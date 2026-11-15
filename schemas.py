from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict

class LoginIn(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str = Field(min_length=10)
    role: str = "astronaut"

class AstronautIn(BaseModel):
    astronaut_code: str
    full_name: str
    email: str = ""
    status: str = "Active"
    notes: str = ""

class MissionIn(BaseModel):
    name: str
    description: str = ""
    status: str = "Planned"
    phase: str = "Pre-launch"
    start_date: date | None = None
    end_date: date | None = None

class ReadingIn(BaseModel):
    astronaut_id: int
    mission_id: int | None = None
    heart_rate: float = Field(gt=0, le=250)
    spo2: float = Field(gt=0, le=100)
    systolic_bp: float = Field(gt=0, le=300)
    diastolic_bp: float = Field(gt=0, le=200)
    activity: str = "RESTING"
    mission_phase: str = "Pre-launch"
    sensor_source: str = "SIMULATED"
    quality_status: str = "VALID"
    environment: str = "EARTH"
    recorded_at: datetime | None = None
    sync_key: str | None = None

class ReviewIn(BaseModel):
    decision: str
    comments: str = ""

class AlertAction(BaseModel):
    comments: str = ""
    status: str = "Acknowledged"
