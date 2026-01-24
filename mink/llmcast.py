from anthropic import Anthropic
from omegaconf import DictConfig
from typing import List
from .models import TranscriptEvent, OnScreenEvent, IntelligentNote
import logging

logger = logging.getLogger(__name__)


def compose_meeting_text(
    transcript_events: List[TranscriptEvent], ocr_events: List[OnScreenEvent]
) -> str:
    """
    Composes a full meeting text from transcript and ocr events from the meeting.

    Args:
        transcript_events: List of transcript events
        ocr_events: List of ocr events

    Returns:
        str: Full meeting text
    """
    merged_events = sorted(transcript_events + ocr_events, key=lambda x: x.start)

    text = ""
    for event in merged_events:
        event_type = "Transcript" if isinstance(event, TranscriptEvent) else "On-Screen"
        text += (
            f"[{event_type} | {event.start:.0f} - {event.end:.0f}]: {event.content}\n"
        )
    return text


def cast_to_intelligent_notes(
    transcript_events: List[TranscriptEvent],
    ocr_events: List[OnScreenEvent],
    job_id: str,
    config: DictConfig,
) -> List[IntelligentNote]:
    """
    Casts the meeting text to intelligent notes using the given config.

    Args:
        config: LLM config
        transcript_events: List of transcript events
        ocr_events: List of ocr events

    Returns:
        Dict[str, str]: Intelligent notes for each type
    """
    client = Anthropic(api_key=config.api_key)
    meeting_text = compose_meeting_text(transcript_events, ocr_events)
    intelligent_notes = []
    logger.info(f"Casting to intelligent notes for {len(config.types)} types.")
    for note_type in config.types:
        prompt = note_type.prompt
        max_tokens = note_type.max_tokens
        full_prompt = f"{prompt}\n\n{meeting_text}"
        anthropic_response = client.messages.create(
            model=config.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": full_prompt},
            ],
        )
        intelligent_notes.append(
            IntelligentNote(
                title=note_type.title,
                content=anthropic_response.content[0].text,
                job_id=job_id,
            )
        )
        logger.info(f"Casted to intelligent notes for {note_type.title}")
    return intelligent_notes
