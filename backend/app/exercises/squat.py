"""
Squat Exercise State Machine
Tracks: standing -> descending -> bottom -> ascending -> standing
Evaluates bilateral knee flexion, squat depth, and knee valgus (inward caving).
"""

import time
from typing import Any, Dict, List, Optional
from app.exercises.base import ExerciseStateMachine
from app.schemas.exercise import ExercisePhaseInfo


class SquatStateMachine(ExerciseStateMachine):
    """
    Finite state machine for real-time squat analysis.
    Validates complete descent to depth before awarding a repetition.
    """

    DEFAULT_THRESHOLDS = {
        "standing_knee": 160.0,   # Knees extended in standing position (degrees)
        "descending_knee": 145.0, # Knees bending downwards
        "bottom_knee": 100.0,     # Knee flexion at bottom of squat
        "ascending_knee": 115.0,  # Knees straightening back up
        "valgus_ratio": 0.85,     # Knee distance / ankle distance threshold for caving
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        cfg = dict(self.DEFAULT_THRESHOLDS)
        if thresholds:
            cfg.update(thresholds)
        super().__init__(
            name="squat",
            initial_phase="standing",
            min_rep_interval_sec=0.7,
            min_phase_dwell_sec=0.15,
            thresholds=cfg,
        )
        self.reached_bottom = False

    def reset(self) -> None:
        super().reset()
        self.reached_bottom = False

    def update(
        self,
        joint_angles: Dict[str, Optional[float]],
        segment_distances: Dict[str, Optional[float]],
        landmarks_by_name: Dict[str, Any],
        timestamp: Optional[float] = None,
    ) -> ExercisePhaseInfo:
        now = timestamp if timestamp is not None else time.time()
        cues: List[str] = []

        # Extract primary knee angle (use average of valid knees or whichever is visible)
        left_knee = joint_angles.get("left_knee")
        right_knee = joint_angles.get("right_knee")

        valid_knees = [k for k in (left_knee, right_knee) if k is not None]
        if not valid_knees:
            return ExercisePhaseInfo(
                exercise_name=self.name,
                phase=self.current_phase,
                repetitions=self.reps,
                is_rep_completed=False,
                form_cues=["Low landmark visibility for knees"],
                primary_metric_name="knee_angle",
                primary_metric_value=None,
                phase_progress_pct=0.0,
                valid=False,
            )

        knee_angle = sum(valid_knees) / len(valid_knees)
        hip_angle = joint_angles.get("left_hip") or joint_angles.get("right_hip")

        is_rep_completed = False
        progress_pct = 0.0

        # State transitions
        if self.current_phase == "standing":
            self.reached_bottom = False
            progress_pct = 0.0
            if knee_angle < self.thresholds["descending_knee"]:
                self.transition_to("descending", now)
                progress_pct = 15.0

        elif self.current_phase == "descending":
            # Progress 0 -> 50%
            span = max(1.0, self.thresholds["standing_knee"] - self.thresholds["bottom_knee"])
            progress_pct = min(50.0, max(0.0, (self.thresholds["standing_knee"] - knee_angle) / span * 50.0))

            if knee_angle <= self.thresholds["bottom_knee"]:
                self.reached_bottom = True
                self.transition_to("bottom", now)
                progress_pct = 50.0
                cues.append("Good squat depth")
            elif knee_angle >= self.thresholds["standing_knee"]:
                # Aborted/partial descent without hitting bottom -> reset to standing
                self.transition_to("standing", now)
                cues.append("Squat deeper for full depth")

        elif self.current_phase == "bottom":
            progress_pct = 50.0
            if knee_angle > self.thresholds["ascending_knee"]:
                self.transition_to("ascending", now)
                progress_pct = 60.0

        elif self.current_phase == "ascending":
            # Progress 50 -> 100%
            span = max(1.0, self.thresholds["standing_knee"] - self.thresholds["bottom_knee"])
            ascent_progress = min(50.0, max(0.0, (knee_angle - self.thresholds["bottom_knee"]) / span * 50.0))
            progress_pct = 50.0 + ascent_progress

            if knee_angle >= self.thresholds["standing_knee"]:
                if self.reached_bottom and self.can_count_rep(now):
                    self.reps += 1
                    self.last_rep_timestamp = now
                    is_rep_completed = True
                    cues.append("Rep completed!")

                self.reached_bottom = False
                self.transition_to("standing", now)
                progress_pct = 100.0
            elif knee_angle <= self.thresholds["bottom_knee"]:
                # Dropped back down
                self.transition_to("bottom", now)

        # Form Cue Analysis: Knee Valgus (inward caving)
        left_knee_lm = landmarks_by_name.get("left_knee")
        right_knee_lm = landmarks_by_name.get("right_knee")
        left_ankle_lm = landmarks_by_name.get("left_ankle")
        right_ankle_lm = landmarks_by_name.get("right_ankle")

        if left_knee_lm and right_knee_lm and left_ankle_lm and right_ankle_lm:
            def get_x(lm):
                return lm.get("x") if isinstance(lm, dict) else getattr(lm, "x", None)

            lk_x, rk_x = get_x(left_knee_lm), get_x(right_knee_lm)
            la_x, ra_x = get_x(left_ankle_lm), get_x(right_ankle_lm)

            if all(v is not None for v in (lk_x, rk_x, la_x, ra_x)):
                knee_dist = abs(rk_x - lk_x)
                ankle_dist = abs(ra_x - la_x)
                if ankle_dist > 0.05:
                    ratio = knee_dist / ankle_dist
                    if ratio < self.thresholds["valgus_ratio"] and self.current_phase in ("descending", "bottom", "ascending"):
                        cues.append("Knees caving inwards — push knees out")

        # Form Cue: Forward lean
        if hip_angle is not None and hip_angle < 65.0 and self.current_phase in ("descending", "bottom"):
            cues.append("Chest up — avoid excessive forward lean")

        self.form_cues = cues

        return ExercisePhaseInfo(
            exercise_name=self.name,
            phase=self.current_phase,
            repetitions=self.reps,
            is_rep_completed=is_rep_completed,
            form_cues=cues,
            primary_metric_name="knee_angle",
            primary_metric_value=round(knee_angle, 1),
            phase_progress_pct=round(progress_pct, 1),
            valid=True,
        )
