import logging
import uuid
import os
import shutil
import multiprocessing as mp
import uvicorn
import hydra
import time
import glob
from multiprocessing import Queue
from contextlib import asynccontextmanager
from sqlmodel import select
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, status
from fastapi.responses import JSONResponse
from omegaconf import DictConfig
from .models import Job, Meeting
from .transcription import process_transcription
from .ocr import process_ocr
from .db import init_db, get_session
from .llmcast import cast_to_intelligent_notes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mink")

config_store = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if "config" in config_store:
        init_db(config_store["config"])
    yield


app = FastAPI(title="Mink", lifespan=lifespan)


@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.url.path in ["/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)

    cfg = config_store.get("config")

    if cfg and "auth" in cfg and cfg.auth.get("type") == "static":
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in cfg.auth.get("keys", []):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing API Key"},
            )

    return await call_next(request)


def run_transcription_worker(
    job_id: str, video_path: str, config: DictConfig, queue: Queue
):
    try:
        logger.info(f"Job {job_id}: Starting transcription worker")
        events = process_transcription(video_path, job_id, config)
        logger.info(
            f"Job {job_id}: Transcription finished. Found {len(events)} events."
        )
        queue.put(events)
    except Exception as e:
        logger.error(f"Job {job_id}: Transcription failed: {e}")
        queue.put([])


def run_ocr_worker(job_id: str, video_path: str, config: DictConfig, queue: Queue):
    try:
        logger.info(f"Job {job_id}: Starting OCR worker")
        events = process_ocr(video_path, job_id, config)
        logger.info(f"Job {job_id}: OCR finished. Found {len(events)} events.")
        queue.put(events)
    except Exception as e:
        logger.error(f"Job {job_id}: OCR failed: {e}")
        queue.put([])


def run_worker_task(job: Job):
    job_id = job.job_id
    upload_dir = "/tmp/mink"

    files = glob.glob(os.path.join(upload_dir, f"{job_id}_*"))
    if not files:
        logger.error(f"Job {job_id}: Could not find video file")
        return
    file_path = files[0]

    if "config" not in config_store:
        logger.error(f"Job {job_id}: Config not available")
        return
    cfg = config_store["config"]

    transcription_queue = mp.Queue()
    ocr_queue = mp.Queue()

    p_transcribe = mp.Process(
        target=run_transcription_worker,
        args=(job_id, file_path, cfg, transcription_queue),
    )
    p_ocr = mp.Process(target=run_ocr_worker, args=(job_id, file_path, cfg, ocr_queue))

    p_transcribe.start()
    p_ocr.start()

    # Retrieve results
    # Note: get() is blocking by default, which is what we want here as we wait for workers
    full_transcript = transcription_queue.get()
    full_ocr = ocr_queue.get()

    p_transcribe.join()
    p_ocr.join()

    logger.info(
        f"Job {job_id}: Retrieved {len(full_transcript)} transcript events and {len(full_ocr)} OCR events."
    )

    # Save to DB
    try:
        # We use a new session here since this runs in a separate thread (BackgroundTasks)
        with next(get_session()) as session:
            session.expire_on_commit = False
            db_job = session.get(Job, job_id)
            if db_job:
                db_job.job_status = "completed"

                transcript_duration = full_transcript[-1].end
                for event in full_transcript:
                    session.add(event)
                    db_job.transcript_events.append(event)
                for event in full_ocr:
                    session.add(event)
                    db_job.ocr_events.append(event)

                session.add(db_job)

                meeting = session.get(Meeting, db_job.meeting_id)
                if meeting:
                    meeting.duration = transcript_duration
                    session.add(meeting)

                session.commit()
                logger.info(f"Job {job_id}: Saved results to database.")
            else:
                logger.error(f"Job {job_id}: Job not found in DB during save.")

    except Exception as e:
        logger.error(f"Job {job_id}: Failed to save to DB: {e}")
        return

    if not cfg.cast:
        logger.info(
            f"Job {job_id}: No LLM casting config found, skipping intelligent notes."
        )
        return

    intelligent_notes = cast_to_intelligent_notes(
        full_transcript, full_ocr, job_id, cfg.cast
    )
    try:
        with next(get_session()) as session:
            db_job = session.get(Job, job_id)
            if db_job:
                for note in intelligent_notes:
                    session.add(note)
                    db_job.intelligent_notes.append(note)
                session.add(db_job)
                session.commit()
                logger.info(f"Job {job_id}: Saved intelligent notes to database.")
            else:
                logger.error(f"Job {job_id}: Job not found in DB during save.")
    except Exception as e:
        logger.error(f"Job {job_id}: Failed to save to DB: {e}")


@app.post("/take-notes", response_model=Job)
async def take_notes(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    logger.info(f"Received request, job_id={job_id}")
    upload_dir = "/tmp/mink"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{job_id}_{file.filename}")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    if "config" not in config_store:
        logger.error("Config not initialized!")
        return Job(job_id=job_id, job_status="failed")
    cfg = config_store["config"]

    # Start job
    # Create Meeting and Job
    try:
        with next(get_session()) as session:
            meeting = Meeting(name=f"Meeting {job_id}", time_started=time.time())
            session.add(meeting)
            session.commit()
            session.refresh(meeting)

            job = Job(job_id=job_id, job_status="queued", meeting_id=meeting.id)
            session.add(job)
            session.commit()
            session.refresh(job)
    except Exception as e:
        logger.error(f"Failed to create DB records: {e}")
        return Job(job_id=job_id, job_status="failed")

    background_tasks.add_task(run_worker_task, job)
    return job


@app.get("/job/{job_id}", response_model=Job)
async def get_job(job_id: str):
    with next(get_session()) as session:
        job = session.get(Job, job_id)
        if job:
            return job
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Job not found"},
            )


@hydra.main(version_base=None, config_path="../config", config_name="config")
def main(cfg: DictConfig):
    config_store["config"] = cfg
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
