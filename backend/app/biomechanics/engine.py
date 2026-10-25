"""
BiomechanicsEngine Orchestrator
Integrates joint angles, segment distances, bilateral symmetry, ROM, and kinematics.
"""

import time
from typing import Any, Dict, List, Optional
from app.biomechanics.angles import calculate_all_joint_angles
from app.biomechanics.distances import calculate_all_segment_distances
from app.biomechanics.movement import KinematicMovementTracker, RangeOfMotionTracker
from app.biomechanics.smoothing import ExponentialMovingAverageFilter
from app.biomechanics.symmetry import calculate_symmetry_metrics


class BiomechanicsEngine:
    """
    Online Biomechanics Engine for real-time sports and athletic movement analysis.
    """

    def __init__(
        self,
        visibility_threshold: float = 0.5,
        smoothing_alpha: float = 0.70,
        enable_smoothing: bool = True,
    ):
        self.visibility_threshold = visibility_threshold
        self.enable_smoothing = enable_smoothing
        self.smoother = ExponentialMovingAverageFilter(alpha=smoothing_alpha)
        self.rom_tracker = RangeOfMotionTracker()
        self.movement_tracker = KinematicMovementTracker()

    def analyze(
        self,
        landmarks: List[Any],
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executes biomechanical analysis on a list of landmark objects or dicts.
        Returns a structured dictionary of biomechanics telemetry.
        """
        now = timestamp if timestamp is not None else time.time()

        # Build landmark dictionary keyed by name
        landmarks_by_name: Dict[str, Any] = {}
        for lm in landmarks:
            if isinstance(lm, dict):
                name = lm.get("name")
            else:
                name = getattr(lm, "name", None)
            if name:
                landmarks_by_name[name] = lm

        # 1. Joint angles
        raw_angles = calculate_all_joint_angles(
            landmarks_by_name,
            visibility_threshold=self.visibility_threshold,
        )

        # Apply smoothing to angles if enabled
        processed_angles: Dict[str, Dict[str, Any]] = {}
        for joint, item in raw_angles.items():
            angle_val = item.get("angle")
            if self.enable_smoothing and item.get("valid") and angle_val is not None:
                smoothed_angle = self.smoother.filter_scalar(f"angle_{joint}", angle_val)
                processed_angles[joint] = {
                    "angle": smoothed_angle,
                    "valid": True,
                    "reason": None,
                }
            else:
                processed_angles[joint] = item

        # 2. Body segment distances
        distances = calculate_all_segment_distances(
            landmarks_by_name,
            visibility_threshold=self.visibility_threshold,
        )

        # 3. Bilateral symmetry analysis
        symmetry = calculate_symmetry_metrics(processed_angles, distances)

        # 4. Range of motion tracking
        rom_metrics = self.rom_tracker.update(processed_angles)

        # 5. Kinematic movement metrics
        kinematics = self.movement_tracker.update(landmarks_by_name, timestamp=now)

        # Quick dictionary of valid joint angles in degrees for easy client consumption
        simple_angles: Dict[str, Optional[float]] = {
            joint: data["angle"] if data["valid"] else None
            for joint, data in processed_angles.items()
        }

        simple_distances: Dict[str, Optional[float]] = {
            seg: data["distance"] if data["valid"] else None
            for seg, data in distances.items()
        }

        return {
            "timestamp": round(now, 4),
            "valid": any(data["valid"] for data in processed_angles.values()),
            "joint_angles": simple_angles,
            "joint_angles_detailed": processed_angles,
            "segment_distances_norm": simple_distances,
            "symmetry": symmetry,
            "range_of_motion": rom_metrics,
            "kinematics": kinematics,
        }

    def reset_rom(self, joint_name: Optional[str] = None) -> None:
        """Resets the Range of Motion tracking memory."""
        self.rom_tracker.reset(joint_name)

    def reset(self) -> None:
        """Resets all internal history buffers."""
        self.smoother.reset()
        self.rom_tracker.reset()
        self.movement_tracker.reset()
