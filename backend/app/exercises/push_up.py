"""
Push-up Exercise State Machine
Tracks: top_plank -> lowering -> bottom -> pushing -> top_plank
Evaluates bilateral elbow flexion, bottom chest depth, and torso/hip plank alignment.
"""

import time
from typing import Any, Dict, List, Optional
from app.exercises.base import ExerciseStateMachine
from app.schemas.exercise import ExercisePhaseInfo


class PushUpStateMachine(ExerciseStateMachine):
    """
    Finite state machine for real-time push-up repetition tracking.
    Validates complete descent to 90 degrees elbow angle and straight torso alignment.
    """

    DEFAULT_THRESHOLDS = {
        "top_elbow": 150.0,       # Arms locked out in plank position (degrees)
        "lowering_elbow": 135.0,  # Beginning descent towards floor
        "bottom_elbow": 90.0,     # Chest down, elbows at 90 degrees or below
        "pushing_elbow": 105.0,   # Pushing back up towards lockout
        "min_hip_angle": 140.0,   # Torso/hip plank alignment threshold
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        cfg = dict(self.DEFAULT_THRESHOLDS)
        if thresholds:
            cfg.update(thresholds)
        super().__init__(
            name="push_up",
            initial_phase="top_plank",
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

        # Extract elbow angle (average of valid elbows or whichever is visible)
        left_elbow = joint_angles.get("left_elbow")
        right_elbow = joint_angles.get("right_elbow")

        valid_elbows = [e for e in (left_elbow, right_elbow) if e is not None]
        if not valid_elbows:
            return ExercisePhaseInfo(
                exercise_name=self.name,
                phase=self.current_phase,
                repetitions=self.reps,
                is_rep_completed=False,
                form_cues=["Low landmark visibility for arms"],
                primary_metric_name="elbow_angle",
                primary_metric_value=None,
                phase_progress_pct=0.0,
                valid=False,
            )

        elbow_angle = sum(valid_elbows) / len(valid_elbows)
        hip_angle = joint_angles.get("left_hip") or joint_angles.get("right_hip")

        is_rep_completed = False
        progress_pct = 0.0

        if self.current_phase == "top_plank":
            self.reached_bottom = False
            progress_pct = 0.0
            if elbow_angle < self.thresholds["lowering_elbow"]:
                self.transition_to("lowering", now)
                progress_pct = 15.0

        elif self.current_phase == "lowering":
            # Progress 0 -> 50%
            span = max(1.0, self.thresholds["top_elbow"] - self.thresholds["bottom_elbow"])
            progress_pct = min(50.0, max(0.0, (self.thresholds["top_elbow"] - elbow_angle) / span * 50.0))

            if elbow_angle <= self.thresholds["bottom_elbow"]:
                self.reached_bottom = True
                self.transition_to("bottom", now)
                progress_pct = 50.0
                cues.append("Good push-up depth")
            elif elbow_angle >= self.thresholds["top_elbow"]:
                # Aborted descent -> reset
                self.transition_to("top_plank", now)
                cues.append("Lower chest further")

        elif self.current_phase == "bottom":
            progress_pct = 50.0
            if elbow_angle > self.thresholds["pushing_elbow"]:
                self.transition_to("pushing", now)
                progress_pct = 60.0

        elif self.current_phase == "pushing":
            # Progress 50 -> 100%
            span = max(1.0, self.thresholds["top_elbow"] - self.thresholds["bottom_elbow"])
            ascent_progress = min(50.0, max(0.0, (elbow_angle - self.thresholds["bottom_elbow"]) / span * 50.0))
            progress_pct = 50.0 + ascent_progress

            if elbow_angle >= self.thresholds["top_elbow"]:
                if self.reached_bottom and self.can_count_rep(now):
                    self.reps += 1
                    self.last_rep_timestamp = now
                    is_rep_completed = True
                    cues.append("Rep completed!")

                self.reached_bottom = False
                self.transition_to("top_plank", now)
                progress_pct = 100.0
            elif elbow_angle <= self.thresholds["bottom_elbow"]:
                self.transition_to("bottom", now)

        # Form Cue Analysis: Torso plank alignment (hip sag or excessive piking)
        if hip_angle is not None and hip_angle < self.thresholds["min_hip_angle"]:
            cues.append("Keep core tight — avoid sagging or piking hips")

        self.form_cues = cues

        return ExercisePhaseInfo(
            exercise_name=self.name,
            phase=self.current_phase,
            repetitions=self.reps,
            is_rep_completed=is_rep_completed,
            form_cues=cues,
            primary_metric_name="elbow_angle",
            primary_metric_value=round(elbow_angle, 1),
            phase_progress_pct=round(progress_pct, 1),
            valid=True,
        )
