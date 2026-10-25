"""
Bilateral Body Symmetry Analysis
Computes left/right differences and symmetry indicators for corresponding joints and segments.
Note: These are kinematic movement symmetry indicators, not medical diagnoses.
"""

from typing import Any, Dict, Optional


def calculate_symmetry_metrics(
    angles: Dict[str, Dict[str, Any]],
    distances: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Computes bilateral difference indicators:
        - Absolute angle differences (degrees)
        - Absolute segment length differences (normalized units)
        - Overall movement symmetry balance score [0.0, 100.0]%
    """
    angle_pairs = [
        ("elbow", "left_elbow", "right_elbow"),
        ("knee", "left_knee", "right_knee"),
        ("shoulder", "left_shoulder", "right_shoulder"),
        ("hip", "left_hip", "right_hip"),
    ]

    distance_pairs = [
        ("upper_arm", "left_upper_arm", "right_upper_arm"),
        ("forearm", "left_forearm", "right_forearm"),
        ("thigh", "left_thigh", "right_thigh"),
        ("lower_leg", "left_lower_leg", "right_lower_leg"),
    ]

    angle_diffs: Dict[str, Optional[float]] = {}
    valid_angle_diffs = []

    for name, left_key, right_key in angle_pairs:
        left_res = angles.get(left_key, {})
        right_res = angles.get(right_key, {})

        if left_res.get("valid") and right_res.get("valid"):
            diff = abs(float(left_res["angle"]) - float(right_res["angle"]))
            angle_diffs[f"{name}_diff_deg"] = round(diff, 2)
            valid_angle_diffs.append(diff)
        else:
            angle_diffs[f"{name}_diff_deg"] = None

    distance_diffs: Dict[str, Optional[float]] = {}
    for name, left_key, right_key in distance_pairs:
        left_res = distances.get(left_key, {})
        right_res = distances.get(right_key, {})

        if left_res.get("valid") and right_res.get("valid"):
            diff = abs(float(left_res["distance"]) - float(right_res["distance"]))
            distance_diffs[f"{name}_diff_norm"] = round(diff, 4)
        else:
            distance_diffs[f"{name}_diff_norm"] = None

    # Calculate overall movement symmetry score (100% = identical bilateral angles, decreases with divergence)
    # A 30 degree average discrepancy equates to ~70% balance
    if valid_angle_diffs:
        mean_diff = sum(valid_angle_diffs) / len(valid_angle_diffs)
        # Score penalty: max 100%, 0% at 100 degree difference
        symmetry_score = max(0.0, min(100.0, 100.0 - mean_diff))
        symmetry_score = round(symmetry_score, 1)
    else:
        symmetry_score = None

    return {
        "joint_angle_differences_deg": angle_diffs,
        "segment_distance_differences_norm": distance_diffs,
        "movement_symmetry_score": symmetry_score,
        "valid": len(valid_angle_diffs) > 0,
    }
