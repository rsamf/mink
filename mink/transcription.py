import logging
from typing import List
from faster_whisper import WhisperModel, BatchedInferencePipeline
from omegaconf import DictConfig
from .models import TranscriptEvent

logger = logging.getLogger(__name__)


def process_transcription(
    video_path: str, job_id: str, config: DictConfig
) -> List[TranscriptEvent]:
    """
    Transcribes a video file using faster-whisper with batched inference.
    """
    logger.info(f"Starting transcription for {video_path}")

    model_size = config.transcript.model_size
    compute_type = config.transcript.precision
    device = "cuda"

    logger.info(f"Loading Whisper model: {model_size} on {device} with {compute_type}")

    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        batched_model = BatchedInferencePipeline(model=model)

        batch_size = config.transcript.batch_size
        logger.info(f"Transcribing with batch_size={batch_size}")

        segments, info = batched_model.transcribe(
            video_path,
            vad_filter=True,
            batch_size=batch_size,
        )

        events = []
        for segment in segments:
            events.append(
                TranscriptEvent(
                    speaker_name=None,
                    content=segment.text,
                    start=segment.start,
                    end=segment.end,
                    job_id=job_id,
                )
            )

        logger.info(f"Transcription complete. Found {len(events)} events.")
        return events

    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        raise
