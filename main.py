import logging
import uuid
import os
import shutil
import multiprocessing
import uvicorn
import hydra
from fastapi import FastAPI, UploadFile, File
from omegaconf import DictConfig
from models import Job
from transcription import process_transcription
from ocr import process_ocr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mink")

app = FastAPI(title="Mink")
config_store = {}


def run_transcription_worker(job_id: str, video_path: str, config: DictConfig):
    try:
        logger.info(f"Job {job_id}: Starting transcription worker")
        events = process_transcription(video_path, config)
        logger.info(
            f"Job {job_id}: Transcription finished. Found {len(events)} events."
        )
        for e in events:
            logger.info(f"[Transcript] {e.start:.2f}-{e.end:.2f}: {e.content}")
    except Exception as e:
        logger.error(f"Job {job_id}: Transcription failed: {e}")


def run_ocr_worker(job_id: str, video_path: str, config: DictConfig):
    try:
        logger.info(f"Job {job_id}: Starting OCR worker")
        events = process_ocr(video_path, config)
        logger.info(f"Job {job_id}: OCR finished. Found {len(events)} events.")
        for e in events:
            logger.info(f"[OCR] {e.start:.2f}-{e.end:.2f}: {e.content}")
    except Exception as e:
        logger.error(f"Job {job_id}: OCR failed: {e}")


@app.post("/take-notes", response_model=Job)
async def take_notes(file: UploadFile = File(...)):
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
    p_transcribe = multiprocessing.Process(
        target=run_transcription_worker, args=(job_id, file_path, cfg)
    )
    p_ocr = multiprocessing.Process(
        target=run_ocr_worker, args=(job_id, file_path, cfg)
    )

    p_transcribe.start()
    p_ocr.start()

    return Job(job_id=job_id, job_status="started")


@hydra.main(version_base=None, config_path="config", config_name="config")
def main(cfg: DictConfig):
    config_store["config"] = cfg
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
