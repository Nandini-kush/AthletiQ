"""
Bicep Curl Exercise State Machine
Tracks: extended -> curling -> contracted -> lowering -> extended
Evaluates elbow flexion, peak contraction, and bottom extension.
"""

import time
from typing import Any, Dict, List, Optional
from app.exercises.base import ExerciseStateMachine
from app.schemas.exercise import ExercisePhaseInfo


class BicepCurlStateMachine(ExerciseStateMachine):
    """
    Finite state machine for real-time bicep curl repetition tracking.
    Validates complete range of motion from full arm extension through peak contraction.
    """

    DEFAULT_THRESHOLDS = {
        "extended_elbow": 150.0,   # Arm straight at bottom (degrees)
        "curling_elbow": 135.0,    # Arm flexing upward
        "contracted_elbow": 65.0,  # Peak curl contraction at top
        "lowering_elbow": 80.0,    # Arm extending downward
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        cfg = dict(self.DEFAULT_THRESHOLDS)
        if thresholds:
            cfg.update(thresholds)
        super().__init__(
            name="bicep_curl",
            initial_phase="extended",
            min_rep_interval_sec=0.6,
            min_phase_dwell_sec=0.15,
            thresholds=cfg,
        )
        self.reached_contracted = False

    def reset(self) -> None:
        super().reset()
        self.reached_contracted = False

    def update(
        self,
        joint_angles: Dict[str, Optional[float]],
        segment_distances: Dict[str, Optional[float]],
        landmarks_by_name: Dict[str, Any],
        timestamp: Optional[float] = None,
    ) -> ExercisePhaseInfo:
        now = timestamp if timestamp is not None else time.time()
        cues: List[str] = []

        # Find primary active elbow (use minimum angle among visible arms = active arm)
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

        # The active arm curling has the smaller elbow angle
        elbow_angle = min(valid_elbows)

        is_rep_completed = False
        progress_pct = 0.0

        if self.current_phase == "extended":
            self.reached_contracted = False
            progress_pct = 0.0
            if elbow_angle < self.thresholds["curling_elbow"]:
                self.transition_to("curling", now)
                progress_pct = 15.0

        elif self.current_phase == "curling":
            # Progress 0 -> 50%
            span = max(1.0, self.thresholds["extended_elbow"] - self.thresholds["contracted_elbow"])
            progress_pct = min(50.0, max(0.0, (self.thresholds["extended_elbow"] - elbow_angle) / span * 50.0))

            if elbow_angle <= self.thresholds["contracted_elbow"]:
                self.reached_contracted = True
                self.transition_to("contracted", now)
                progress_pct = 50.0
                cues.append("Peak contraction reached")
            elif elbow_angle >= self.thresholds["extended_elbow"]:
                # Aborted curl before contraction -> reset
                self.transition_to("extended", now)
                cues.append("Curl all the way up for full contraction")

        elif self.current_phase == "contracted":
            progress_pct = 50.0
            if elbow_angle > self.thresholds["lowering_elbow"]:
                self.transition_to("lowering", now)
                progress_pct = 60.0

        elif self.current_phase == "lowering":
            # Progress 50 -> 100%
            span = max(1.0, self.thresholds["extended_elbow"] - self.thresholds["contracted_elbow"])
            descent_progress = min(50.0, max(0.0, (elbow_angle - self.thresholds["contracted_elbow"]) / span * 50.0))
            progress_pct = 50.0 + descent_progress

            if elbow_angle >= self.thresholds["extended_elbow"]:
                if self.reached_contracted and self.can_count_rep(now):
                    self.reps += 1
                    self.last_rep_timestamp = now
                    is_rep_completed = True
                    cues.append("Rep completed!")

                self.reached_contracted = False
                self.transition_to("extended", now)
                progress_pct = 100.0
            elif elbow_angle <= self.thresholds["contracted_elbow"]:
                self.transition_to("contracted", now)

        # Form Cue Analysis
        if self.current_phase == "extended" and elbow_angle < 140.0:
            cues.append("Full arm extension at bottom")

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
