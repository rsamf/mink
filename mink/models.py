from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Relationship, JSON
from pydantic import BaseModel


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
    time_started: Optional[float] = Field(default=None)

    meeting: Optional[Meeting] = Relationship(back_populates="jobs")
    transcript_events: List[TranscriptEvent] = Relationship(back_populates="job")
    ocr_events: List[OnScreenEvent] = Relationship(back_populates="job")
    intelligent_notes: List["IntelligentNote"] = Relationship(back_populates="job")


class IntelligentNote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    job_id: str = Field(foreign_key="job.job_id")

    job: Optional["Job"] = Relationship(back_populates="intelligent_notes")


# Response schemas for API
class TranscriptEventResponse(BaseModel):
    id: Optional[int]
    speaker_name: Optional[str]
    content: str
    start: float
    end: float

    model_config = {"from_attributes": True}


class OnScreenEventResponse(BaseModel):
    id: Optional[int]
    speaker_name: Optional[str]
    content: str
    start: float
    end: float
    bbox: List[int]
    confidence: float

    model_config = {"from_attributes": True}


class IntelligentNoteResponse(BaseModel):
    id: Optional[int]
    title: str
    content: str

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    job_id: str
    job_status: str
    meeting_id: Optional[int] = None
    time_started: Optional[float] = None
    transcript_events: List[TranscriptEventResponse] = []
    ocr_events: List[OnScreenEventResponse] = []
    intelligent_notes: List[IntelligentNoteResponse] = []

    model_config = {"from_attributes": True}
    
class MeetingResponse(BaseModel):
    id: Optional[int]
    name: str
    time_started: float
    duration: float = 0.0
    jobs: List[JobResponse] = []

    model_config = {"from_attributes": True}
