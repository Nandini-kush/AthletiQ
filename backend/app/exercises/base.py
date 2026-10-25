"""
Base Exercise State Machine
Defines the abstract interface, state transition lifecycle, hysteresis, and debounce validation for exercise analysis.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.schemas.exercise import ExercisePhaseInfo


class ExerciseStateMachine(ABC):
    """
    Abstract state machine for tracking exercise repetition cycles and form cues.
    Enforces complete movement cycle validation and prevents duplicate counts via hysteresis.
    """

    def __init__(
        self,
        name: str,
        initial_phase: str,
        min_rep_interval_sec: float = 0.6,
        min_phase_dwell_sec: float = 0.15,
        thresholds: Optional[Dict[str, float]] = None,
    ):
        self.name = name
        self.initial_phase = initial_phase
        self.current_phase = initial_phase
        self.reps = 0
        self.min_rep_interval_sec = min_rep_interval_sec
        self.min_phase_dwell_sec = min_phase_dwell_sec
        self.thresholds = thresholds or {}

        # Timestamps for debounce & hysteresis
        self.last_rep_timestamp: float = 0.0
        self.last_phase_change_timestamp: float = 0.0
        self.form_cues: List[str] = []

    def reset(self) -> None:
        """Resets the state machine and repetition counter to zero."""
        self.current_phase = self.initial_phase
        self.reps = 0
        self.last_rep_timestamp = 0.0
        self.last_phase_change_timestamp = 0.0
        self.form_cues.clear()

    def transition_to(self, new_phase: str, timestamp: float) -> bool:
        """
        Transitions to a new phase if sufficient dwell time has elapsed.
        Returns True if the transition occurred.
        """
        if new_phase == self.current_phase:
            return False

        # Guard against hyper-frequency bouncing / jitter
        if self.last_phase_change_timestamp > 0:
            if (timestamp - self.last_phase_change_timestamp) < self.min_phase_dwell_sec:
                return False

        self.current_phase = new_phase
        self.last_phase_change_timestamp = timestamp
        return True

    def can_count_rep(self, timestamp: float) -> bool:
        """Temporal hysteresis check to prevent duplicate / double counting."""
        if self.last_rep_timestamp > 0:
            if (timestamp - self.last_rep_timestamp) < self.min_rep_interval_sec:
                return False
        return True

    @abstractmethod
    def update(
        self,
        joint_angles: Dict[str, Optional[float]],
        segment_distances: Dict[str, Optional[float]],
        landmarks_by_name: Dict[str, Any],
        timestamp: Optional[float] = None,
    ) -> ExercisePhaseInfo:
        """
        Evaluates current frame measurements and updates exercise state, rep count, and cues.
        """
        pass
