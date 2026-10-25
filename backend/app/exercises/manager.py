"""
Exercise Analysis Manager
Orchestrates exercise state machines, manual exercise selection, and real-time repetition tracking.
"""

import time
from typing import Any, Dict, List, Optional
from app.exercises.bicep_curl import BicepCurlStateMachine
from app.exercises.classifier import classify_candidate_posture
from app.exercises.push_up import PushUpStateMachine
from app.exercises.squat import SquatStateMachine
from app.schemas.exercise import ExercisePhaseInfo


class ExerciseAnalysisManager:
    """
    Central manager for athletic exercise repetition counting and form tracking.
    """

    def __init__(self):
        self.state_machines = {
            "squat": SquatStateMachine(),
            "bicep_curl": BicepCurlStateMachine(),
            "push_up": PushUpStateMachine(),
        }
        self.selected_exercise: Optional[str] = None

    def select_exercise(self, name: Optional[str]) -> None:
        """
        Sets the active exercise for analysis. If None or empty, analysis is paused.
        """
        if name:
            clean_name = name.strip().lower()
            if clean_name in self.state_machines:
                if self.selected_exercise != clean_name:
                    self.selected_exercise = clean_name
                    self.state_machines[clean_name].reset()
            else:
                self.selected_exercise = None
        else:
            self.selected_exercise = None

    def reset_exercise(self, name: Optional[str] = None) -> None:
        """
        Resets repetition counts and state machine phases.
        """
        target = name or self.selected_exercise
        if target and target in self.state_machines:
            self.state_machines[target].reset()
        else:
            for sm in self.state_machines.values():
                sm.reset()

    def process_frame(
        self,
        biomechanics: Any,
        landmarks: List[Any],
        timestamp: Optional[float] = None,
        exercise_name: Optional[str] = None,
    ) -> Optional[ExercisePhaseInfo]:
        """
        Processes real-time frame biomechanics through the selected exercise state machine.
        """
        now = timestamp if timestamp is not None else time.time()

        if exercise_name is not None and exercise_name != self.selected_exercise:
            self.select_exercise(exercise_name)

        # Build landmark dictionary keyed by name
        landmarks_by_name: Dict[str, Any] = {}
        for lm in landmarks:
            if isinstance(lm, dict):
                name = lm.get("name")
            else:
                name = getattr(lm, "name", None)
            if name:
                landmarks_by_name[name] = lm

        # Extract joint angles & distances from biomechanics
        if biomechanics is None:
            return None

        if isinstance(biomechanics, dict):
            joint_angles = biomechanics.get("joint_angles", {})
            segment_distances = biomechanics.get("segment_distances_norm", {})
        else:
            joint_angles = getattr(biomechanics, "joint_angles", {})
            segment_distances = getattr(biomechanics, "segment_distances_norm", {})

        # Optional heuristic advisory classification
        candidate = classify_candidate_posture(landmarks_by_name, joint_angles)

        if not self.selected_exercise or self.selected_exercise not in self.state_machines:
            return None

        machine = self.state_machines[self.selected_exercise]
        result = machine.update(
            joint_angles=joint_angles,
            segment_distances=segment_distances,
            landmarks_by_name=landmarks_by_name,
            timestamp=now,
        )

        result.candidate_detected = candidate
        return result
