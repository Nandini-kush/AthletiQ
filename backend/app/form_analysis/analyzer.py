"""
Form Analyzer Service
Coordinates exercise form rule evaluation, feedback stabilization, and overall form status generation.
"""

import time
from typing import Any, Dict, List, Optional
from app.form_analysis.feedback import FeedbackStabilizer
from app.form_analysis.rules import (
    DEFAULT_FORM_THRESHOLDS,
    evaluate_curl_rules,
    evaluate_pushup_rules,
    evaluate_squat_rules,
)
from app.form_analysis.schemas import FormAnalysisResult, FormFinding


class FormAnalyzer:
    """
    Central analyzer for athletic exercise form evaluation.
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        confirmation_frames: int = 2,
        cooldown_seconds: float = 1.8,
    ):
        self.thresholds = dict(DEFAULT_FORM_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

        self.stabilizer = FeedbackStabilizer(
            confirmation_frames=confirmation_frames,
            cooldown_seconds=cooldown_seconds,
        )
        self.current_exercise: Optional[str] = None

    def reset(self) -> None:
        """Clears all historical findings and stabilizer buffers."""
        self.stabilizer.reset()

    def analyze(
        self,
        exercise_name: Optional[str],
        biomechanics: Any,
        exercise_info: Any,
        landmarks: List[Any],
        timestamp: Optional[float] = None,
    ) -> Optional[FormAnalysisResult]:
        """
        Executes rule-based form evaluation for the currently active exercise.
        Returns None if no exercise is active.
        """
        now = timestamp if timestamp is not None else time.time()

        if not exercise_name:
            if self.current_exercise is not None:
                self.reset()
                self.current_exercise = None
            return None

        clean_exercise = exercise_name.strip().lower()

        # Handle exercise switching
        if clean_exercise != self.current_exercise:
            self.reset()
            self.current_exercise = clean_exercise

        # Landmark dictionary
        landmarks_by_name: Dict[str, Any] = {}
        for lm in landmarks:
            if isinstance(lm, dict):
                name = lm.get("name")
            else:
                name = getattr(lm, "name", None)
            if name:
                landmarks_by_name[name] = lm

        # Biomechanics angles & distances
        if biomechanics is None:
            return FormAnalysisResult(
                exercise=clean_exercise,
                analysis_available=False,
                form_status="unavailable",
                findings=[],
                limitations=["Biomechanics data unavailable for this frame."],
            )

        if isinstance(biomechanics, dict):
            joint_angles = biomechanics.get("joint_angles", {})
            segment_distances = biomechanics.get("segment_distances_norm", {})
        else:
            joint_angles = getattr(biomechanics, "joint_angles", {})
            segment_distances = getattr(biomechanics, "segment_distances_norm", {})

        raw_findings: List[FormFinding] = []
        limitations: List[str] = []

        if clean_exercise == "squat":
            raw_findings, limitations = evaluate_squat_rules(
                joint_angles=joint_angles,
                segment_distances=segment_distances,
                landmarks=landmarks_by_name,
                exercise_info=exercise_info,
                thresholds=self.thresholds,
            )
        elif clean_exercise == "push_up":
            raw_findings, limitations = evaluate_pushup_rules(
                joint_angles=joint_angles,
                segment_distances=segment_distances,
                landmarks=landmarks_by_name,
                exercise_info=exercise_info,
                thresholds=self.thresholds,
            )
        elif clean_exercise == "bicep_curl":
            raw_findings, limitations = evaluate_curl_rules(
                joint_angles=joint_angles,
                segment_distances=segment_distances,
                landmarks=landmarks_by_name,
                exercise_info=exercise_info,
                thresholds=self.thresholds,
            )
        else:
            return None

        # Filter through temporal confirmation & cooldown stabilizer
        stable_findings = self.stabilizer.filter_findings(raw_findings, timestamp=now)

        # Determine overall form status
        if limitations and not stable_findings:
            form_status = "unavailable"
            available = False
        elif any(f.severity == "warning" for f in stable_findings):
            form_status = "needs_attention"
            available = True
        elif any(f.severity == "info" for f in stable_findings):
            form_status = "needs_attention"
            available = True
        else:
            form_status = "good"
            available = True

        return FormAnalysisResult(
            exercise=clean_exercise,
            analysis_available=available,
            form_status=form_status,
            findings=stable_findings,
            limitations=limitations,
        )
