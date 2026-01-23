import logging
import uuid
import os
import shutil
import multiprocessing as mp
from multiprocessing import Queue
import uvicorn
import hydra
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, status
from fastapi.responses import JSONResponse
from omegaconf import DictConfig
from .models import Job
from .transcription import process_transcription
from .ocr import process_ocr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mink")

app = FastAPI(title="Mink")
config_store = {}


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
        events = process_transcription(video_path, config)
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
        events = process_ocr(video_path, config)
        logger.info(f"Job {job_id}: OCR finished. Found {len(events)} events.")
        queue.put(events)
    except Exception as e:
        logger.error(f"Job {job_id}: OCR failed: {e}")
        queue.put([])


def run_worker_task(job: Job):
    job_id = job.job_id
    # We need to reconstruct the file path. Ideally it should be passed in job or stored better.
    # For now assuming standard path based on job_id
    upload_dir = "/tmp/mink"
    # Find the file in upload_dir that starts with job_id
    import glob

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

    # Print results as requested
    print(f"--- Transcript ({len(full_transcript)} events) ---")
    for e in full_transcript:
        print(f"{e.start:.2f}-{e.end:.2f}: {e.content}")

    print(f"--- OCR ({len(full_ocr)} events) ---")
    for e in full_ocr:
        print(f"{e.start:.2f}-{e.end:.2f}: {e.content}")


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
        return Job(job_id=job_id, job_status="failed_no_config")
    cfg = config_store["config"]

    # Start job
    job = Job(job_id=job_id, job_status="queued")
    background_tasks.add_task(run_worker_task, job)
    return job


@hydra.main(version_base=None, config_path="../config", config_name="config")
def main(cfg: DictConfig):
    config_store["config"] = cfg
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
