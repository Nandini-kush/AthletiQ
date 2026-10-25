"""
Official MediaPipe Pose Landmark Definitions & Connections
Provides 33 standard human body landmarks and anatomical connection pairs.
"""

from typing import Dict, List, Tuple

# Official MediaPipe Pose 33 Landmark Indices & Names
POSE_LANDMARKS: Dict[int, str] = {
    0: "nose",
    1: "left_eye_inner",
    2: "left_eye",
    3: "left_eye_outer",
    4: "right_eye_inner",
    5: "right_eye",
    6: "right_eye_outer",
    7: "left_ear",
    8: "right_ear",
    9: "mouth_left",
    10: "mouth_right",
    11: "left_shoulder",
    12: "right_shoulder",
    13: "left_elbow",
    14: "right_elbow",
    15: "left_wrist",
    16: "right_wrist",
    17: "left_pinky",
    18: "right_pinky",
    19: "left_index",
    20: "right_index",
    21: "left_thumb",
    22: "right_thumb",
    23: "left_hip",
    24: "right_hip",
    25: "left_knee",
    26: "right_knee",
    27: "left_ankle",
    28: "right_ankle",
    29: "left_heel",
    30: "right_heel",
    31: "left_foot_index",
    32: "right_foot_index",
}

# Reverse lookup: name -> index
LANDMARK_NAME_TO_INDEX: Dict[str, int] = {v: k for k, v in POSE_LANDMARKS.items()}

# Key Biomechanical Landmarks critical for athletic form, movement, and joint angles
KEY_BIOMECHANICAL_LANDMARKS: List[str] = [
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

# Standard Anatomical Connections for Pose Skeleton Visualization
# Pairs of (start_index, end_index)
POSE_CONNECTIONS: List[Tuple[int, int]] = [
    # Face & Head
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    # Torso
    (11, 12),  # Shoulders
    (11, 23),  # Left Torso (shoulder to hip)
    (12, 24),  # Right Torso (shoulder to hip)
    (23, 24),  # Hips
    # Left Arm
    (11, 13),  # Shoulder to Elbow
    (13, 15),  # Elbow to Wrist
    (15, 17),  # Wrist to Pinky
    (15, 19),  # Wrist to Index
    (15, 21),  # Wrist to Thumb
    (17, 19),  # Pinky to Index
    # Right Arm
    (12, 14),  # Shoulder to Elbow
    (14, 16),  # Elbow to Wrist
    (16, 18),  # Wrist to Pinky
    (16, 20),  # Wrist to Index
    (16, 22),  # Wrist to Thumb
    (18, 20),  # Pinky to Index
    # Left Leg
    (23, 25),  # Hip to Knee
    (25, 27),  # Knee to Ankle
    (27, 29),  # Ankle to Heel
    (27, 31),  # Ankle to Foot Index
    (29, 31),  # Heel to Foot Index
    # Right Leg
    (24, 26),  # Hip to Knee
    (26, 28),  # Knee to Ankle
    (28, 30),  # Ankle to Heel
    (28, 32),  # Ankle to Foot Index
    (30, 32),  # Heel to Foot Index
]

# Quality threshold: minimum visibility confidence for a landmark to be considered detected
DEFAULT_VISIBILITY_THRESHOLD: float = 0.5

# Minimum number of key biomechanical landmarks with visibility >= threshold
# required to declare a valid athlete pose
MIN_KEY_LANDMARKS_FOR_VALID_POSE: int = 4


def is_valid_pose(
    landmarks_data: List[dict],
    visibility_threshold: float = DEFAULT_VISIBILITY_THRESHOLD,
    min_key_landmarks: int = MIN_KEY_LANDMARKS_FOR_VALID_POSE,
) -> bool:
    """
    Evaluates whether a detected pose contains enough visible key body landmarks.
    """
    if not landmarks_data or len(landmarks_data) < 33:
        return False

    visible_key_count = 0
    for lm in landmarks_data:
        name = lm.get("name")
        visibility = lm.get("visibility", 0.0)
        if name in KEY_BIOMECHANICAL_LANDMARKS and visibility >= visibility_threshold:
            visible_key_count += 1

    return visible_key_count >= min_key_landmarks
