from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ExerciseSessionBase(BaseModel):
    exercise_name: str
    started_at: datetime
    ended_at: datetime
    duration: int = Field(..., ge=0)
    total_repetitions: int = Field(0, ge=0)
    avg_pace_rpm: Optional[float] = None
    summary_metrics: Optional[Dict[str, Any]] = None

class ExerciseSessionCreate(ExerciseSessionBase):
    pass

class ExerciseSessionResponse(ExerciseSessionBase):
    id: int
    athlete_id: int
    performance_score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}
