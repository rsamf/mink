from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Relationship, JSON


class TranscriptEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    speaker_name: Optional[str] = None
    content: str
    start: float
    end: float
    job_id: str = Field(foreign_key="job.job_id")

    job: Optional["Job"] = Relationship(back_populates="transcript_events")


class OnScreenEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    speaker_name: Optional[str] = None
    content: str
    start: float
    end: float
    bbox: List[int] = Field(sa_type=JSON)
    confidence: float
    job_id: str = Field(foreign_key="job.job_id")

    job: Optional["Job"] = Relationship(back_populates="ocr_events")


class Meeting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    time_started: float
    duration: float = 0.0

    jobs: List["Job"] = Relationship(back_populates="meeting")


class Job(SQLModel, table=True):
    job_id: str = Field(primary_key=True)
    job_status: str
    meeting_id: Optional[int] = Field(default=None, foreign_key="meeting.id")

    meeting: Optional[Meeting] = Relationship(back_populates="jobs")
    transcript_events: List[TranscriptEvent] = Relationship(back_populates="job")
    ocr_events: List[OnScreenEvent] = Relationship(back_populates="job")
