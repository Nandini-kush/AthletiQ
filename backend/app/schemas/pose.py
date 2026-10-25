"""
Pydantic Schemas for Real-Time Pose Estimation
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class LandmarkPoint(BaseModel):
    index: int
    name: str
    x: float = Field(..., description="Normalized X coordinate in image space [0.0, 1.0]")
    y: float = Field(..., description="Normalized Y coordinate in image space [0.0, 1.0]")
    z: float = Field(..., description="Relative landmark depth / Z coordinate")
    visibility: float = Field(0.0, description="Confidence/visibility score [0.0, 1.0]")


class KeyLandmark(BaseModel):
    x: float
    y: float
    z: float
    visibility: float


from app.schemas.biomechanics import BiomechanicsResult
from app.schemas.exercise import ExercisePhaseInfo
from app.form_analysis.schemas import FormAnalysisResult


class PoseDetectionResult(BaseModel):
    pose_detected: bool
    confidence: float = 0.0
    landmarks: List[LandmarkPoint] = []
    key_landmarks: Dict[str, KeyLandmark] = {}
    biomechanics: Optional[BiomechanicsResult] = None
    exercise: Optional[ExercisePhaseInfo] = None
    form_feedback: Optional[FormAnalysisResult] = None
    inference_time_ms: float = 0.0
    message: Optional[str] = None
