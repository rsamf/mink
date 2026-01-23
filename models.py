from typing import Optional, List
from pydantic import BaseModel


class TranscriptEvent(BaseModel):
    speaker_name: Optional[str] = None
    content: str
    start: float
    end: float


class OnScreenEvent(BaseModel):
    speaker_name: Optional[str] = None
    content: str
    start: float
    end: float
    bbox: List[float]
    confidence: float


class Job(BaseModel):
    job_id: str
    job_status: str
