from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class JointAngleStat(BaseModel):
    min: float
    max: float
    mean: float
    rom: float
    sample_count: int = 0

class SymmetryStat(BaseModel):
    avg_symmetry_score: Optional[float] = None
    knee_diff_deg: Optional[float] = None
    elbow_diff_deg: Optional[float] = None
    observation: Optional[str] = None

class FormFeedbackSummary(BaseModel):
    total_findings: int = 0
    total_warnings: int = 0
    total_infos: int = 0
    finding_counts: Dict[str, int] = Field(default_factory=dict)
    primary_cues: List[str] = Field(default_factory=list)

class DataQualitySummary(BaseModel):
    valid_frames: int = 0
    total_frames: int = 0
    tracking_ratio: float = 0.0
    limitations: List[str] = Field(default_factory=list)

class BaselineComparison(BaseModel):
    baseline_session_id: Optional[int] = None
    baseline_date: Optional[datetime] = None
    rep_diff: Optional[int] = None
    pace_diff_rpm: Optional[float] = None
    rom_diff_deg: Optional[float] = None
    duration_diff_sec: Optional[int] = None
    summary_note: str

class SessionAnalyticsResponse(BaseModel):
    session_id: int
    exercise_name: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: int
    total_repetitions: int
    pace_rpm: Optional[float] = None
    pace_label: str = "cadence"
    joint_angle_stats: Dict[str, JointAngleStat] = Field(default_factory=dict)
    rom_stats: Dict[str, float] = Field(default_factory=dict)
    symmetry: Optional[SymmetryStat] = None
    form_summary: Optional[FormFeedbackSummary] = None
    data_quality: Optional[DataQualitySummary] = None
    baseline_comparison: Optional[BaselineComparison] = None
    scientific_disclaimer: str

    model_config = {"from_attributes": True}

class ExerciseProgressPoint(BaseModel):
    session_id: int
    date: datetime
    repetitions: int
    duration_seconds: int
    pace_rpm: Optional[float] = None
    primary_rom_deg: Optional[float] = None

class ExerciseProgressResponse(BaseModel):
    exercise_name: str
    total_sessions: int
    total_repetitions: int
    avg_pace_rpm: Optional[float] = None
    best_pace_rpm: Optional[float] = None
    avg_primary_rom_deg: Optional[float] = None
    time_filter_applied: str
    history: List[ExerciseProgressPoint] = Field(default_factory=list)
    baseline_summary: Optional[str] = None

class PerExerciseSummary(BaseModel):
    exercise_name: str
    total_sessions: int
    total_repetitions: int
    total_duration_seconds: int
    avg_pace_rpm: Optional[float] = None
    last_performed_at: Optional[datetime] = None

class AthleteOverviewResponse(BaseModel):
    total_sessions: int
    total_repetitions: int
    total_duration_seconds: int
    most_frequent_exercise: Optional[str] = None
    exercises_practiced: List[str] = Field(default_factory=list)
    per_exercise_summary: Dict[str, PerExerciseSummary] = Field(default_factory=dict)
    recent_sessions: List[Dict[str, Any]] = Field(default_factory=list)
