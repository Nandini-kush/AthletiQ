"""
Joint Angle Calculations
Implements 3-point vector trigonometry for human anatomical joints.
Formula:
    Given points A, B (vertex), C:
    BA = A - B
    BC = C - B
    cos(theta) = dot(BA, BC) / (||BA|| * ||BC||)
    angle = arccos(clamp(cos(theta), -1.0, 1.0)) in degrees [0.0, 180.0]
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

# Mapping of standard athletic joint angles to (Point A, Vertex B, Point C) landmark names
JOINT_DEFINITIONS: Dict[str, Tuple[str, str, str]] = {
    "left_elbow": ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_knee": ("left_hip", "left_knee", "left_ankle"),
    "right_knee": ("right_hip", "right_knee", "right_ankle"),
    "left_shoulder": ("left_elbow", "left_shoulder", "left_hip"),
    "right_shoulder": ("right_elbow", "right_shoulder", "right_hip"),
    "left_hip": ("left_shoulder", "left_hip", "left_knee"),
    "right_hip": ("right_shoulder", "right_hip", "right_knee"),
}


def calculate_3point_angle(
    a: Union[Tuple[float, ...], List[float], np.ndarray],
    b: Union[Tuple[float, ...], List[float], np.ndarray],
    c: Union[Tuple[float, ...], List[float], np.ndarray],
    use_3d: bool = False,
) -> Optional[float]:
    """
    Calculates the interior angle at vertex point B formed by segments BA and BC in degrees [0, 180].
    Returns None if any vector has zero length or inputs are invalid.
    """
    try:
        a_arr = np.array(a, dtype=np.float64)
        b_arr = np.array(b, dtype=np.float64)
        c_arr = np.array(c, dtype=np.float64)

        if not use_3d:
            a_arr = a_arr[:2]
            b_arr = b_arr[:2]
            c_arr = c_arr[:2]

        ba = a_arr - b_arr
        bc = c_arr - b_arr

        norm_ba = np.linalg.norm(ba)
        norm_bc = np.linalg.norm(bc)

        if norm_ba < 1e-7 or norm_bc < 1e-7:
            return None

        cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
        # Numerical stability clamp to [-1.0, 1.0]
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)

        angle_rad = np.arccos(cosine_angle)
        angle_deg = float(np.degrees(angle_rad))
        return round(angle_deg, 2)
    except Exception:
        return None


def calculate_all_joint_angles(
    landmarks_by_name: Dict[str, Any],
    visibility_threshold: float = 0.5,
    use_3d: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """
    Computes all standard athletic joint angles from a dictionary of landmark objects or dicts.
    Returns:
        {
            "left_knee": {"angle": 92.4, "valid": True, "reason": None},
            "right_knee": {"angle": None, "valid": False, "reason": "insufficient_visibility"},
            ...
        }
    """
    results: Dict[str, Dict[str, Any]] = {}

    for joint_name, (name_a, name_b, name_c) in JOINT_DEFINITIONS.items():
        lm_a = landmarks_by_name.get(name_a)
        lm_b = landmarks_by_name.get(name_b)
        lm_c = landmarks_by_name.get(name_c)

        if not lm_a or not lm_b or not lm_c:
            results[joint_name] = {
                "angle": None,
                "valid": False,
                "reason": "missing_landmarks",
            }
            continue

        # Extract coordinates and visibility
        def get_props(lm: Any) -> Tuple[List[float], float]:
            if isinstance(lm, dict):
                coords = [lm.get("x", 0.0), lm.get("y", 0.0), lm.get("z", 0.0)]
                vis = lm.get("visibility", 1.0)
            else:
                coords = [getattr(lm, "x", 0.0), getattr(lm, "y", 0.0), getattr(lm, "z", 0.0)]
                vis = getattr(lm, "visibility", 1.0)
            return coords, vis

        pt_a, vis_a = get_props(lm_a)
        pt_b, vis_b = get_props(lm_b)
        pt_c, vis_c = get_props(lm_c)

        if min(vis_a, vis_b, vis_c) < visibility_threshold:
            results[joint_name] = {
                "angle": None,
                "valid": False,
                "reason": "insufficient_visibility",
            }
            continue

        angle = calculate_3point_angle(pt_a, pt_b, pt_c, use_3d=use_3d)

        if angle is None:
            results[joint_name] = {
                "angle": None,
                "valid": False,
                "reason": "collinear_or_zero_length_vectors",
            }
        else:
            results[joint_name] = {
                "angle": angle,
                "valid": True,
                "reason": None,
            }

    return results
