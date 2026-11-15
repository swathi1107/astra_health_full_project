from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(30), default="astronaut")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Astronaut(Base):
    __tablename__ = "astronauts"
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(180), default="")
    status: Mapped[str] = mapped_column(String(30), default="Active")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Planned")
    phase: Mapped[str] = mapped_column(String(30), default="Pre-launch")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

class MissionAssignment(Base):
    __tablename__ = "mission_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronauts.id"))
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Reading(Base):
    __tablename__ = "readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronauts.id"), index=True)
    mission_id: Mapped[int | None] = mapped_column(ForeignKey("missions.id"), nullable=True)
    heart_rate: Mapped[float] = mapped_column(Float)
    spo2: Mapped[float] = mapped_column(Float)
    systolic_bp: Mapped[float] = mapped_column(Float)
    diastolic_bp: Mapped[float] = mapped_column(Float)
    activity: Mapped[str] = mapped_column(String(40), default="RESTING")
    mission_phase: Mapped[str] = mapped_column(String(40), default="Pre-launch")
    sensor_source: Mapped[str] = mapped_column(String(40), default="SIMULATED")
    quality_status: Mapped[str] = mapped_column(String(30), default="VALID")
    environment: Mapped[str] = mapped_column(String(20), default="EARTH")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    sync_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)

Index("ix_reading_astronaut_recorded", Reading.astronaut_id, Reading.recorded_at)

class Baseline(Base):
    __tablename__ = "baselines"
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronauts.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="Pending")
    reading_count: Mapped[int] = mapped_column(Integer)
    avg_heart_rate: Mapped[float] = mapped_column(Float)
    min_heart_rate: Mapped[float] = mapped_column(Float)
    max_heart_rate: Mapped[float] = mapped_column(Float)
    std_heart_rate: Mapped[float] = mapped_column(Float)
    avg_spo2: Mapped[float] = mapped_column(Float)
    min_spo2: Mapped[float] = mapped_column(Float)
    max_spo2: Mapped[float] = mapped_column(Float)
    avg_systolic: Mapped[float] = mapped_column(Float)
    avg_diastolic: Mapped[float] = mapped_column(Float)
    comments: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronauts.id"))
    reading_id: Mapped[int | None] = mapped_column(ForeignKey("readings.id"), nullable=True)
    parameter: Mapped[str] = mapped_column(String(40))
    observed: Mapped[float] = mapped_column(Float)
    baseline_value: Mapped[float] = mapped_column(Float)
    deviation: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="Open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    acknowledged_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

class MedicalReview(Base):
    __tablename__ = "medical_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(30))
    subject_id: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(30))
    comments: Mapped[str] = mapped_column(Text, default="")
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
