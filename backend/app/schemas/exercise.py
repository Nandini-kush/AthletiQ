"""
Exercise Schemas
Pydantic validation models for real-time exercise classification, state machines, and repetition tracking.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ExercisePhaseInfo(BaseModel):
    exercise_name: str
    phase: str
    repetitions: int = 0
    is_rep_completed: bool = False
    form_cues: List[str] = []
    primary_metric_name: str = "angle"
    primary_metric_value: Optional[float] = None
    phase_progress_pct: float = Field(0.0, ge=0.0, le=100.0, description="Movement cycle completion percentage")
    candidate_detected: Optional[str] = Field(None, description="Optional heuristic posture classification")
    valid: bool = True
