"""
Kinematics & Range of Motion (ROM) Tracking
Monitors temporal displacement, velocity, acceleration, and dynamic joint ROM.
Units are in normalized coordinate space and seconds.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class RangeOfMotionTracker:
    """
    Maintains min, max, and range of motion (ROM = max - min) across successive frames.
    """

    def __init__(self):
        self._history: Dict[str, Dict[str, float]] = {}

    def update(self, joint_angles: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Optional[float]]]:
        """
        Updates the observed range for each valid joint angle.
        """
        rom_results: Dict[str, Dict[str, Optional[float]]] = {}

        for joint_name, item in joint_angles.items():
            angle = item.get("angle")
            is_valid = item.get("valid", False)

            if not is_valid or angle is None:
                existing = self._history.get(joint_name)
                if existing:
                    rom_results[joint_name] = {
                        "current_angle": None,
                        "min_angle": existing["min"],
                        "max_angle": existing["max"],
                        "rom": round(existing["max"] - existing["min"], 2),
                    }
                else:
                    rom_results[joint_name] = {
                        "current_angle": None,
                        "min_angle": None,
                        "max_angle": None,
                        "rom": None,
                    }
                continue

            angle_val = float(angle)
            if joint_name not in self._history:
                self._history[joint_name] = {"min": angle_val, "max": angle_val}
            else:
                self._history[joint_name]["min"] = min(self._history[joint_name]["min"], angle_val)
                self._history[joint_name]["max"] = max(self._history[joint_name]["max"], angle_val)

            min_val = self._history[joint_name]["min"]
            max_val = self._history[joint_name]["max"]

            rom_results[joint_name] = {
                "current_angle": angle_val,
                "min_angle": round(min_val, 2),
                "max_angle": round(max_val, 2),
                "rom": round(max_val - min_val, 2),
            }

        return rom_results

    def reset(self, joint_name: Optional[str] = None) -> None:
        """
        Resets ROM history for a specific joint or all joints.
        """
        if joint_name:
            self._history.pop(joint_name, None)
        else:
            self._history.clear()


class KinematicMovementTracker:
    """
    Calculates frame-to-frame displacement, velocity, and acceleration.
    Tracks body center (midpoint of hips/shoulders) and critical extremities.
    """

    def __init__(self, max_history_seconds: float = 2.0):
        self.max_history_seconds = max_history_seconds
        # Stores landmark_name -> list of (timestamp, np.array([x, y, z]))
        self._history: Dict[str, List[Tuple[float, np.ndarray]]] = {}
        self._last_velocities: Dict[str, float] = {}

    def update(
        self,
        landmarks_by_name: Dict[str, Any],
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Processes new frame coordinates and computes normalized kinematics.
        """
        now = timestamp if timestamp is not None else time.time()
        kinematics: Dict[str, Any] = {}

        # Key landmarks to track for overall body movement
        target_landmarks = ["nose", "left_wrist", "right_wrist", "left_ankle", "right_ankle"]

        # Synthesize Body Center Proxy (Mid-Hip)
        left_hip = landmarks_by_name.get("left_hip")
        right_hip = landmarks_by_name.get("right_hip")

        points_to_process: Dict[str, np.ndarray] = {}

        for name in target_landmarks:
            lm = landmarks_by_name.get(name)
            if lm:
                if isinstance(lm, dict):
                    coords = [lm.get("x", 0.0), lm.get("y", 0.0), lm.get("z", 0.0)]
                    vis = lm.get("visibility", 1.0)
                else:
                    coords = [getattr(lm, "x", 0.0), getattr(lm, "y", 0.0), getattr(lm, "z", 0.0)]
                    vis = getattr(lm, "visibility", 1.0)

                if vis >= 0.4:
                    points_to_process[name] = np.array(coords[:2], dtype=np.float64)

        if left_hip and right_hip:
            def get_xy(lm):
                if isinstance(lm, dict):
                    return [lm.get("x", 0.0), lm.get("y", 0.0)], lm.get("visibility", 1.0)
                return [getattr(lm, "x", 0.0), getattr(lm, "y", 0.0)], getattr(lm, "visibility", 1.0)

            lh_xy, lh_v = get_xy(left_hip)
            rh_xy, rh_v = get_xy(right_hip)
            if min(lh_v, rh_v) >= 0.4:
                mid_hip = (np.array(lh_xy) + np.array(rh_xy)) / 2.0
                points_to_process["body_center"] = mid_hip

        total_speed = 0.0
        active_points = 0

        for pt_name, current_pos in points_to_process.items():
            if pt_name not in self._history:
                self._history[pt_name] = []

            history = self._history[pt_name]
            displacement = 0.0
            velocity = 0.0
            acceleration = 0.0

            if history:
                prev_time, prev_pos = history[-1]
                dt = now - prev_time

                if dt > 1e-4:
                    displacement = float(np.linalg.norm(current_pos - prev_pos))
                    velocity = displacement / dt

                    prev_velocity = self._last_velocities.get(pt_name, 0.0)
                    acceleration = (velocity - prev_velocity) / dt
                    self._last_velocities[pt_name] = velocity

            history.append((now, current_pos))
            # Trim old history
            while history and now - history[0][0] > self.max_history_seconds:
                history.pop(0)

            kinematics[pt_name] = {
                "displacement_norm": round(displacement, 4),
                "speed_norm_per_sec": round(velocity, 4),
                "acceleration_norm_per_sec2": round(acceleration, 4),
            }

            total_speed += velocity
            active_points += 1

        overall_movement_speed = round(total_speed / active_points, 4) if active_points > 0 else 0.0

        return {
            "overall_movement_speed_norm_per_sec": overall_movement_speed,
            "landmarks_kinematics": kinematics,
        }

    def reset(self) -> None:
        self._history.clear()
        self._last_velocities.clear()
