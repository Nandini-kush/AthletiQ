from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class ExerciseSession(Base):
    __tablename__ = "exercise_sessions"

    id = Column(Integer, primary_key=True, index=True)
    athlete_id = Column(Integer, ForeignKey("athlete_profiles.id"), nullable=False)
    exercise_name = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=False)
    duration = Column(Integer, nullable=False) # in seconds
    total_repetitions = Column(Integer, default=0)
    avg_pace_rpm = Column(Float, nullable=True) # Repetitions per minute
    performance_score = Column(Float, nullable=True) # Computed later
    summary_metrics = Column(JSON, nullable=True) # Stage 7: Joint angle stats, ROM, symmetry, form summary, quality
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("AthleteProfile", back_populates="sessions")

    __table_args__ = (
        Index("ix_exercise_sessions_athlete_started", "athlete_id", "started_at"),
        Index("ix_exercise_sessions_athlete_exercise", "athlete_id", "exercise_name"),
    )
