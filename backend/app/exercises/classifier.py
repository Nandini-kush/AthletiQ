"""
Posture & Exercise Heuristic Classifier
Separate advisory classifier for candidate posture estimation.
Note: Manual exercise selection remains the authoritative driver for repetition state machines.
"""

from typing import Any, Dict, Optional


def classify_candidate_posture(
    landmarks_by_name: Dict[str, Any],
    joint_angles: Dict[str, Optional[float]],
) -> Optional[str]:
    """
    Heuristically analyzes athlete posture orientation to suggest candidate exercise.
    This is strictly separate from the authoritative manual exercise selection.
    """
    left_shoulder = landmarks_by_name.get("left_shoulder")
    right_shoulder = landmarks_by_name.get("right_shoulder")
    left_hip = landmarks_by_name.get("left_hip")
    right_hip = landmarks_by_name.get("right_hip")

    if not (left_shoulder and right_shoulder and left_hip and right_hip):
        return None

    def get_xy(lm):
        if isinstance(lm, dict):
            return lm.get("x", 0.0), lm.get("y", 0.0), lm.get("visibility", 1.0)
        return getattr(lm, "x", 0.0), getattr(lm, "y", 0.0), getattr(lm, "visibility", 1.0)

    ls_x, ls_y, ls_v = get_xy(left_shoulder)
    rs_x, rs_y, rs_v = get_xy(right_shoulder)
    lh_x, lh_y, lh_v = get_xy(left_hip)
    rh_x, rh_y, rh_v = get_xy(right_hip)

    if min(ls_v, rs_v, lh_v, rh_v) < 0.4:
        return None

    mid_shoulder_x = (ls_x + rs_x) / 2.0
    mid_shoulder_y = (ls_y + rs_y) / 2.0
    mid_hip_x = (lh_x + rh_x) / 2.0
    mid_hip_y = (lh_y + rh_y) / 2.0

    delta_x = abs(mid_shoulder_x - mid_hip_x)
    delta_y = abs(mid_shoulder_y - mid_hip_y)

    # If horizontal orientation (delta_x > delta_y), candidate is plank / push-up posture
    if delta_x > delta_y:
        return "push_up"

    # In upright / vertical orientation:
    knee_angles = [joint_angles.get("left_knee"), joint_angles.get("right_knee")]
    valid_knees = [k for k in knee_angles if k is not None]

    elbow_angles = [joint_angles.get("left_elbow"), joint_angles.get("right_elbow")]
    valid_elbows = [e for e in elbow_angles if e is not None]

    # If knees are actively bending (< 140 deg), candidate is squat
    if valid_knees and min(valid_knees) < 140.0:
        return "squat"

    # If elbows are curled (< 110 deg) while standing upright, candidate is bicep curl
    if valid_elbows and min(valid_elbows) < 110.0:
        return "bicep_curl"

    return "standing_neutral"
