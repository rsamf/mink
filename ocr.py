import logging
import cv2
import easyocr
from typing import List
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from omegaconf import DictConfig
from models import OnScreenEvent

logger = logging.getLogger(__name__)


def process_ocr(video_path: str, config: DictConfig) -> List[OnScreenEvent]:
    """
    Detects scenes in a video and performs OCR on the middle frame of each scene.
    """
    logger.info(f"Starting OCR processing for {video_path}")

    lang_list = config.ocr.lang
    logger.info(f"Loading EasyOCR with langs={lang_list}")
    reader = easyocr.Reader(
        lang_list,
        gpu=True,
    )

    # Scene Detection
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())

    video_manager.set_downscale_factor()
    video_manager.start()

    scene_manager.detect_scenes(frame_source=video_manager)
    scene_list = scene_manager.get_scene_list()

    logger.info(f"Detected {len(scene_list)} scenes.")

    events = []

    cap = cv2.VideoCapture(video_path)

    scenes_to_process = []
    if not scene_list:
        logger.info("No scenes detected, processing entire video as one scene.")
        base_duration = video_manager.get_duration()[0]
        scenes_to_process.append((0.0, base_duration.get_seconds()))
    else:
        for scene in scene_list:
            scenes_to_process.append((scene[0].get_seconds(), scene[1].get_seconds()))

    for start_time, end_time in scenes_to_process:
        # Get middle frame of scene
        middle_time = (start_time + end_time) / 2
        cap.set(cv2.CAP_PROP_POS_MSEC, middle_time * 1000)
        ret, frame = cap.read()

        if not ret:
            logger.warning(f"Could not read frame at {middle_time}s")
            continue

        # Run OCR
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = reader.readtext(frame_rgb)

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
                        start=start_time,
                        end=end_time,
                        bbox=bbox,
                        confidence=res[2],
                    )
                )

    cap.release()
    video_manager.release()

    logger.info(f"OCR complete. Found {len(events)} events.")
    return events
