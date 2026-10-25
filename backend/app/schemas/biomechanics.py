"""
Pydantic Schemas for Biomechanical Analysis Telemetry
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class JointAngleDetail(BaseModel):
    angle: Optional[float] = Field(None, description="Angle in degrees [0.0, 180.0]")
    valid: bool
    reason: Optional[str] = None


class RangeOfMotionItem(BaseModel):
    current_angle: Optional[float] = None
    min_angle: Optional[float] = None
    max_angle: Optional[float] = None
    rom: Optional[float] = None


class SymmetryData(BaseModel):
    joint_angle_differences_deg: Dict[str, Optional[float]] = {}
    segment_distance_differences_norm: Dict[str, Optional[float]] = {}
    movement_symmetry_score: Optional[float] = Field(
        None, description="Bilateral movement symmetry score [0.0, 100.0]%"
    )
    valid: bool = False


class KinematicsPointData(BaseModel):
    displacement_norm: float = 0.0
    speed_norm_per_sec: float = 0.0
    acceleration_norm_per_sec2: float = 0.0


class KinematicsData(BaseModel):
    overall_movement_speed_norm_per_sec: float = 0.0
    landmarks_kinematics: Dict[str, KinematicsPointData] = {}


class BiomechanicsResult(BaseModel):
    timestamp: float
    valid: bool
    joint_angles: Dict[str, Optional[float]] = {}
    joint_angles_detailed: Dict[str, JointAngleDetail] = {}
    segment_distances_norm: Dict[str, Optional[float]] = {}
    symmetry: SymmetryData
    range_of_motion: Dict[str, RangeOfMotionItem] = {}
    kinematics: KinematicsData
