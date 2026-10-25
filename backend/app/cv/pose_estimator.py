"""
PoseEstimator Service
Initializes and encapsulates MediaPipe Tasks PoseLandmarker.
Automatically downloads and caches the model asset if missing.
"""

import os
import urllib.request
from pathlib import Path
from typing import Optional
import numpy as np
import mediapipe as mp

# Default model download URL
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "pose_landmarker_lite.task"


class PoseEstimator:
    """
    Modular Pose Estimator using MediaPipe Tasks API.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self._ensure_model_exists()
        self._landmarker = None
        self._initialize_landmarker()

    def _ensure_model_exists(self) -> None:
        """Downloads the MediaPipe pose landmarker model if not present."""
        if not self.model_path.exists():
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"[PoseEstimator] Downloading pose landmarker model to {self.model_path}...")
            urllib.request.urlretrieve(MODEL_URL, str(self.model_path))
            print(f"[PoseEstimator] Model downloaded successfully ({self.model_path.stat().st_size} bytes).")

    def _initialize_landmarker(self) -> None:
        """Initializes the MediaPipe PoseLandmarker."""
        base_options = mp.tasks.BaseOptions(model_asset_path=str(self.model_path))
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )
        self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    def detect(self, bgr_frame: np.ndarray):
        """
        Executes pose detection on a BGR numpy image frame.
        Converts BGR to RGB and wraps in mp.Image.
        Returns PoseLandmarkerResult or None.
        """
        if self._landmarker is None:
            raise RuntimeError("PoseEstimator is not initialized or has been closed.")

        if bgr_frame is None or bgr_frame.size == 0:
            return None

        # Convert OpenCV BGR to RGB
        rgb_frame = np.ascontiguousarray(bgr_frame[:, :, ::-1])
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Run inference
        result = self._landmarker.detect(mp_image)
        return result

    def close(self) -> None:
        """Cleans up MediaPipe resources."""
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
