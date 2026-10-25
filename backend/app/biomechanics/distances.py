"""
Body Segment Distances
Calculates normalized Euclidean distances between anatomical landmark pairs.
Units are in normalized coordinate space [0.0, 1.0].
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

# Anatomical body segments defined by (Endpoint A, Endpoint B)
SEGMENT_DEFINITIONS: Dict[str, Tuple[str, str]] = {
    "shoulder_width": ("left_shoulder", "right_shoulder"),
    "hip_width": ("left_hip", "right_hip"),
    "left_upper_arm": ("left_shoulder", "left_elbow"),
    "right_upper_arm": ("right_shoulder", "right_elbow"),
    "left_forearm": ("left_elbow", "left_wrist"),
    "right_forearm": ("right_elbow", "right_wrist"),
    "left_thigh": ("left_hip", "left_knee"),
    "right_thigh": ("right_hip", "right_knee"),
    "left_lower_leg": ("left_knee", "left_ankle"),
    "right_lower_leg": ("right_knee", "right_ankle"),
}


def calculate_euclidean_distance(
    a: Union[Tuple[float, ...], List[float], np.ndarray],
    b: Union[Tuple[float, ...], List[float], np.ndarray],
    use_3d: bool = False,
) -> Optional[float]:
    """
    Computes Euclidean distance between points A and B.
    """
    try:
        a_arr = np.array(a, dtype=np.float64)
        b_arr = np.array(b, dtype=np.float64)

        if not use_3d:
            a_arr = a_arr[:2]
            b_arr = b_arr[:2]

        dist = float(np.linalg.norm(a_arr - b_arr))
        return round(dist, 4)
    except Exception:
        return None


def calculate_all_segment_distances(
    landmarks_by_name: Dict[str, Any],
    visibility_threshold: float = 0.5,
    use_3d: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """
    Calculates all standard body segment distances in normalized units.
    """
    results: Dict[str, Dict[str, Any]] = {}

    for segment_name, (name_a, name_b) in SEGMENT_DEFINITIONS.items():
        lm_a = landmarks_by_name.get(name_a)
        lm_b = landmarks_by_name.get(name_b)

        if not lm_a or not lm_b:
            results[segment_name] = {
                "distance": None,
                "valid": False,
                "reason": "missing_landmarks",
            }
            continue

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

        if min(vis_a, vis_b) < visibility_threshold:
            results[segment_name] = {
                "distance": None,
                "valid": False,
                "reason": "insufficient_visibility",
            }
            continue

        dist = calculate_euclidean_distance(pt_a, pt_b, use_3d=use_3d)
        if dist is None:
            results[segment_name] = {
                "distance": None,
                "valid": False,
                "reason": "computation_error",
            }
        else:
            results[segment_name] = {
                "distance": dist,
                "valid": True,
                "reason": None,
            }

    return results
