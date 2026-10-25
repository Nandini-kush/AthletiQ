"""
Exercise Analysis Package
Exposes state machines, manager, and posture classification for AthletiQ.
"""

from app.exercises.base import ExerciseStateMachine
from app.exercises.bicep_curl import BicepCurlStateMachine
from app.exercises.classifier import classify_candidate_posture
from app.exercises.manager import ExerciseAnalysisManager
from app.exercises.push_up import PushUpStateMachine
from app.exercises.squat import SquatStateMachine

__all__ = [
    "ExerciseStateMachine",
    "SquatStateMachine",
    "PushUpStateMachine",
    "BicepCurlStateMachine",
    "ExerciseAnalysisManager",
    "classify_candidate_posture",
]
