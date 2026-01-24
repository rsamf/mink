import torch
import logging
import cv2
import easyocr
from typing import Generator, List
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from omegaconf import DictConfig
from .models import OnScreenEvent

logger = logging.getLogger(__name__)


def process_ocr(
    video_path: str, job_id: str, config: DictConfig
) -> List[OnScreenEvent]:
    if config.ocr.model == "easyocr":
        return process_ocr_easyocr(video_path, job_id, config)
    elif config.ocr.model == "lightonocr":
        return process_ocr_lightonocr(video_path, job_id, config)
    else:
        logger.error(f"Unknown OCR model: {config.ocr.model}. Will not process OCR.")
        return []
    
def process_ocr_lightonocr(
    video_path: str, job_id: str, config: DictConfig
) -> List[OnScreenEvent]:
    """
    Uses LightOnOCR (https://huggingface.co/lightonai/LightOnOCR-2-1B).
    Currently processes the entire video as a single chunk.
    """
    logger.info(f"Starting OCR processing for {video_path} using LightOnOCR")
    try:
        from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor
    except ImportError:
        logger.error("transformers library not found. Please install it using 'uv sync --all-extras'.")
        return []
    
    device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float32 if device == "mps" else torch.bfloat16

    model = LightOnOcrForConditionalGeneration.from_pretrained("lightonai/LightOnOCR-2-1B", torch_dtype=dtype).to(device)
    processor = LightOnOcrProcessor.from_pretrained("lightonai/LightOnOCR-2-1B")
    
    events = []
    for frame, start_time, end_time in get_scene_frames(video_path):
        conversation = [{"role": "user", "content": [{"type": "image", "data": frame}]}]

        inputs = processor.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(device=device, dtype=dtype) if v.is_floating_point() else v.to(device) for k, v in inputs.items()}

        output_ids = model.generate(**inputs, max_new_tokens=1024)
        generated_ids = output_ids[0, inputs["input_ids"].shape[1]:]
        output_text = processor.decode(generated_ids, skip_special_tokens=True)
        
        if output_text:
            # bbox and confidence not supported
            events.append(
                OnScreenEvent(
                    speaker_name=None,
                    content=output_text,
                    start=float(start_time),
                    end=float(end_time),
                    bbox=[],
                    confidence=1.0,
                    job_id=job_id,
                )
            )    
    
    logger.info(f"OCR complete. Found {len(events)} events.")

    return events

def process_ocr_easyocr(
    video_path: str, job_id: str, config: DictConfig
) -> List[OnScreenEvent]:
    """
    Detects scenes in a video and performs OCR on the middle frame of each scene.
    """
    logger.info(f"Starting OCR processing for {video_path}")

    lang_list = config.ocr.lang
    logger.info(f"Loading EasyOCR with langs={lang_list}")
    reader = easyocr.Reader(
        lang_list,
        gpu=torch.cuda.is_available(),
    )
    events = []
    for frame, start_time, end_time in get_scene_frames(video_path):
        results = reader.readtext(frame)

        # results format: [[bbox, text, conf], ...]
        if results:
            for res in results:
                # For some reason EasyOCR returns XY,XY,XY,XY
                raw_bbox = res[0]
                bbox = [
                    int(raw_bbox[0][0]),
                    int(raw_bbox[0][1]),
                    int(raw_bbox[2][0]),
                    int(raw_bbox[2][1]),
                ]
                events.append(
                    OnScreenEvent(
                        speaker_name=None,
                        content=res[1],
                        start=float(start_time),
                        end=float(end_time),
                        bbox=bbox,
                        confidence=float(res[2]),
                        job_id=job_id,
                    )
                )


    logger.info(f"OCR complete. Found {len(events)} events.")
    return events


def get_scene_frames(video_path: str) -> Generator[List[tuple], None, None]:
    """
    Utility function to get scenes from a video.
    Returns list of (start_time, end_time) tuples in seconds.
    """
    cap = cv2.VideoCapture(video_path)
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())

    video_manager.set_downscale_factor()
    video_manager.start()

    scene_manager.detect_scenes(frame_source=video_manager)
    scene_list = scene_manager.get_scene_list()

    for scene in scene_list:
        start_time = scene[0].get_seconds()
        end_time = scene[1].get_seconds()
        # Get middle frame of scene
        middle_time = (start_time + end_time) / 2
        cap.set(cv2.CAP_PROP_POS_MSEC, middle_time * 1000)
        ret, frame = cap.read()

        if not ret:
            logger.warning(f"Could not read frame at {middle_time}s")
            continue

        # Run OCR
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        yield frame_rgb, start_time, end_time

    cap.release()
    video_manager.release()
