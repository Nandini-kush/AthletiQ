"""
FrameProcessor Service
Handles image decoding, frame resizing, landmark extraction, and skeleton visualization.
"""

import base64
import time
from typing import Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

from app.cv.landmarks import (
    KEY_BIOMECHANICAL_LANDMARKS,
    POSE_CONNECTIONS,
    POSE_LANDMARKS,
    is_valid_pose,
)
from app.cv.pose_estimator import PoseEstimator
from app.biomechanics.engine import BiomechanicsEngine
from app.exercises.manager import ExerciseAnalysisManager
from app.form_analysis.analyzer import FormAnalyzer
from app.schemas.biomechanics import BiomechanicsResult
from app.schemas.exercise import ExercisePhaseInfo
from app.form_analysis.schemas import FormAnalysisResult
from app.schemas.pose import KeyLandmark, LandmarkPoint, PoseDetectionResult


class FrameProcessor:
    """
    High-performance frame processing pipeline for real-time webcam analysis.
    """

    def __init__(
        self,
        max_width: int = 640,
        estimator: Optional[PoseEstimator] = None,
        biomechanics_engine: Optional[BiomechanicsEngine] = None,
        exercise_manager: Optional[ExerciseAnalysisManager] = None,
        form_analyzer: Optional[FormAnalyzer] = None,
    ):
        self.max_width = max_width
        self.estimator = estimator or PoseEstimator()
        self.biomechanics_engine = biomechanics_engine or BiomechanicsEngine()
        self.exercise_manager = exercise_manager or ExerciseAnalysisManager()
        self.form_analyzer = form_analyzer or FormAnalyzer()

    @staticmethod
    def decode_frame(image_data: Union[str, bytes]) -> Optional[np.ndarray]:
        """
        Decodes image data from base64 string (including data URI prefix) or raw bytes into OpenCV BGR frame.
        """
        try:
            if isinstance(image_data, str):
                # Strip potential Data URI header (e.g. "data:image/jpeg;base64,")
                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]
                raw_bytes = base64.b64decode(image_data)
            else:
                raw_bytes = image_data

            nparr = np.frombuffer(raw_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            print(f"[FrameProcessor] Error decoding image frame: {e}")
            return None

    def resize_frame_if_needed(self, frame: np.ndarray) -> np.ndarray:
        """
        Scales frame down to max_width preserving aspect ratio if larger, optimizing inference latency.
        """
        h, w = frame.shape[:2]
        if w > self.max_width:
            scale = self.max_width / float(w)
            new_w = self.max_width
            new_h = int(h * scale)
            return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return frame

    def process_frame(
        self,
        image_data: Union[str, bytes, np.ndarray],
        exercise_name: Optional[str] = None,
    ) -> PoseDetectionResult:
        """
        Full processing pipeline:
        1. Decode frame
        2. Downscale if needed
        3. Run pose estimation
        4. Extract landmarks & evaluate validity
        5. Run biomechanics engine
        6. Run exercise state machine
        7. Return structured PoseDetectionResult
        """
        start_time = time.perf_counter()

        if isinstance(image_data, np.ndarray):
            frame = image_data
        else:
            frame = self.decode_frame(image_data)

        if frame is None:
            return PoseDetectionResult(
                pose_detected=False,
                confidence=0.0,
                landmarks=[],
                key_landmarks={},
                inference_time_ms=0.0,
                message="Failed to decode image frame.",
            )

        processed_frame = self.resize_frame_if_needed(frame)

        # Run MediaPipe pose detection
        detection_result = self.estimator.detect(processed_frame)

        inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Check if pose was detected
        if (
            detection_result is None
            or not detection_result.pose_landmarks
            or len(detection_result.pose_landmarks) == 0
        ):
            return PoseDetectionResult(
                pose_detected=False,
                confidence=0.0,
                landmarks=[],
                key_landmarks={},
                inference_time_ms=inference_time_ms,
                message="No person or pose detected in frame.",
            )

        # MediaPipe returns a list of detected poses; we analyze the primary detected athlete (index 0)
        raw_landmarks = detection_result.pose_landmarks[0]

        extracted_landmarks: List[LandmarkPoint] = []
        key_landmarks_dict: Dict[str, KeyLandmark] = {}
        total_visibility = 0.0

        for idx, lm in enumerate(raw_landmarks):
            name = POSE_LANDMARKS.get(idx, f"landmark_{idx}")
            visibility = getattr(lm, "visibility", 0.0) or 0.0
            total_visibility += visibility

            pt = LandmarkPoint(
                index=idx,
                name=name,
                x=round(float(lm.x), 4),
                y=round(float(lm.y), 4),
                z=round(float(lm.z), 4),
                visibility=round(float(visibility), 4),
            )
            extracted_landmarks.append(pt)

            if name in KEY_BIOMECHANICAL_LANDMARKS:
                key_landmarks_dict[name] = KeyLandmark(
                    x=pt.x,
                    y=pt.y,
                    z=pt.z,
                    visibility=pt.visibility,
                )

        avg_confidence = round(total_visibility / len(raw_landmarks), 4) if raw_landmarks else 0.0

        # Evaluate quality / validity threshold
        valid = is_valid_pose([lm.model_dump() for lm in extracted_landmarks])

        # Run biomechanics engine on all 33 landmarks (always, even partial poses — engine handles low-visibility joints internally)
        biomechanics_result = None
        try:
            bio_raw = self.biomechanics_engine.analyze(
                [lm.model_dump() for lm in extracted_landmarks]
            )
            biomechanics_result = BiomechanicsResult.model_validate(bio_raw)
        except Exception as bio_err:
            print(f"[FrameProcessor] Biomechanics analysis error: {bio_err}")

        # Run exercise analysis state machine if an exercise is active or requested
        exercise_result = None
        try:
            exercise_result = self.exercise_manager.process_frame(
                biomechanics=biomechanics_result,
                landmarks=[lm.model_dump() for lm in extracted_landmarks],
                exercise_name=exercise_name,
            )
        except Exception as ex_err:
            print(f"[FrameProcessor] Exercise processing error: {ex_err}")

        # Run real-time form correction rules
        form_feedback = None
        try:
            active_ex = exercise_name or (exercise_result.exercise_name if exercise_result else None)
            if active_ex:
                form_feedback = self.form_analyzer.analyze(
                    exercise_name=active_ex,
                    biomechanics=biomechanics_result,
                    exercise_info=exercise_result,
                    landmarks=[lm.model_dump() for lm in extracted_landmarks],
                )
        except Exception as form_err:
            print(f"[FrameProcessor] Form analysis error: {form_err}")

        return PoseDetectionResult(
            pose_detected=valid,
            confidence=avg_confidence,
            landmarks=extracted_landmarks,
            key_landmarks=key_landmarks_dict,
            inference_time_ms=inference_time_ms,
            message="Pose detected successfully." if valid else "Partial pose detected; insufficient key joints visible.",
            biomechanics=biomechanics_result,
            exercise=exercise_result,
            form_feedback=form_feedback,
        )

    @staticmethod
    def draw_skeleton(
        frame: np.ndarray,
        landmarks: List[LandmarkPoint],
        visibility_threshold: float = 0.4,
    ) -> np.ndarray:
        """
        Utility to render pose skeleton directly onto an OpenCV frame (for test/debug visualization).
        """
        output = frame.copy()
        h, w = output.shape[:2]

        pts: Dict[int, Tuple[int, int]] = {}
        for lm in landmarks:
            if lm.visibility >= visibility_threshold:
                px = int(lm.x * w)
                py = int(lm.y * h)
                pts[lm.index] = (px, py)
                cv2.circle(output, (px, py), 4, (0, 255, 0), -1)

        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx in pts and end_idx in pts:
                cv2.line(output, pts[start_idx], pts[end_idx], (255, 128, 0), 2)

        return output
