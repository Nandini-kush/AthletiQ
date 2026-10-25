"""
Exercise Form Correction Rules
Rule-based evaluation for Squats, Push-ups, and Bicep Curls using real landmark geometry and biomechanics.
"""

from typing import Any, Dict, List, Optional, Tuple
from app.form_analysis.schemas import FormFinding, FormFindingMeasurement

DEFAULT_FORM_THRESHOLDS = {
    # Squat thresholds
    "squat_min_depth_knee": 105.0,        # Degrees: knee angle must reach <= 105 at bottom
    "squat_max_torso_lean_hip": 60.0,      # Degrees: hip angle < 60 indicates excessive forward torso lean
    "squat_max_knee_asymmetry": 15.0,      # Degrees: max acceptable bilateral knee difference
    "squat_min_valgus_ratio": 0.82,        # Ratio: knee span / ankle span threshold for inward caving
    "squat_min_lockout_knee": 155.0,       # Degrees: knees must straighten to >= 155 upon standing

    # Push-up thresholds
    "pushup_min_depth_elbow": 100.0,       # Degrees: elbow angle must reach <= 100 at bottom
    "pushup_min_hip_angle": 140.0,         # Degrees: hip angle < 140 indicates hip sag or piking
    "pushup_max_elbow_asymmetry": 15.0,    # Degrees: max acceptable bilateral elbow difference
    "pushup_min_lockout_elbow": 145.0,     # Degrees: arms should extend to >= 145 at plank top

    # Bicep Curl thresholds
    "curl_max_flexion_elbow": 75.0,        # Degrees: elbow angle should reach <= 75 at peak contraction
    "curl_min_extension_elbow": 140.0,     # Degrees: elbow should extend to >= 140 at bottom
    "curl_max_elbow_asymmetry": 20.0,      # Degrees: bilateral elbow angle discrepancy
    "curl_max_torso_sway": 0.08,           # Normalized coordinate shift of shoulders during curl
}


def _get_lm_coord(lm: Any) -> Tuple[Optional[float], Optional[float], float]:
    """Helper to extract (x, y, visibility) safely from landmark dict or model."""
    if lm is None:
        return None, None, 0.0
    if isinstance(lm, dict):
        return lm.get("x"), lm.get("y"), lm.get("visibility", 1.0)
    return getattr(lm, "x", None), getattr(lm, "y", None), getattr(lm, "visibility", 1.0)


def evaluate_squat_rules(
    joint_angles: Dict[str, Optional[float]],
    segment_distances: Dict[str, Optional[float]],
    landmarks: Dict[str, Any],
    exercise_info: Any,
    thresholds: Dict[str, float],
) -> Tuple[List[FormFinding], List[str]]:
    """Evaluates form rules for Squat exercise."""
    findings: List[FormFinding] = []
    limitations: List[str] = []

    left_knee = joint_angles.get("left_knee")
    right_knee = joint_angles.get("right_knee")
    left_hip = joint_angles.get("left_hip")
    right_hip = joint_angles.get("right_hip")

    # 1. Landmark visibility verification
    _, _, lk_v = _get_lm_coord(landmarks.get("left_knee"))
    _, _, rk_v = _get_lm_coord(landmarks.get("right_knee"))

    if lk_v < 0.5 and rk_v < 0.5:
        limitations.append("Both knees occluded or low confidence — squat form analysis limited.")
        return findings, limitations

    valid_knees = [k for k in (left_knee, right_knee) if k is not None]
    avg_knee = sum(valid_knees) / len(valid_knees) if valid_knees else None
    phase = getattr(exercise_info, "phase", "standing") if exercise_info else "standing"

    # 2. Squat Depth Rule
    if avg_knee is not None:
        if phase == "bottom" and avg_knee > thresholds["squat_min_depth_knee"]:
            findings.append(
                FormFinding(
                    code="SQUAT_DEPTH_LIMITED",
                    severity="warning",
                    message="Observed squat depth is limited (> 105° knee angle).",
                    recommendation="Aim for thighs near parallel with the floor if comfortable.",
                    measurement=FormFindingMeasurement(name="knee_angle", value=round(avg_knee, 1), unit="degrees"),
                )
            )

    # 3. Torso Inclination Rule (Hip Angle)
    valid_hips = [h for h in (left_hip, right_hip) if h is not None]
    if valid_hips:
        avg_hip = sum(valid_hips) / len(valid_hips)
        if phase in ("descending", "bottom") and avg_hip < thresholds["squat_max_torso_lean_hip"]:
            findings.append(
                FormFinding(
                    code="EXCESSIVE_TORSO_LEAN",
                    severity="warning",
                    message="Significant forward torso inclination detected.",
                    recommendation="Keep chest proud and drive hips back while maintaining an upright spine.",
                    measurement=FormFindingMeasurement(name="hip_angle", value=round(avg_hip, 1), unit="degrees"),
                )
            )

    # 4. Bilateral Knee Asymmetry Rule
    if left_knee is not None and right_knee is not None and lk_v >= 0.5 and rk_v >= 0.5:
        knee_diff = abs(left_knee - right_knee)
        if phase in ("descending", "ascending") and knee_diff > thresholds["squat_max_knee_asymmetry"]:
            findings.append(
                FormFinding(
                    code="KNEE_ASYMMETRY",
                    severity="info",
                    message="Bilateral knee angle divergence observed between left and right sides.",
                    recommendation="Distribute weight evenly between both feet throughout the movement.",
                    measurement=FormFindingMeasurement(name="knee_difference", value=round(knee_diff, 1), unit="degrees"),
                )
            )

    # 5. Knee Valgus (Inward Caving) Rule
    lk_x, _, _ = _get_lm_coord(landmarks.get("left_knee"))
    rk_x, _, _ = _get_lm_coord(landmarks.get("right_knee"))
    la_x, _, la_v = _get_lm_coord(landmarks.get("left_ankle"))
    ra_x, _, ra_v = _get_lm_coord(landmarks.get("right_ankle"))

    if all(v is not None for v in (lk_x, rk_x, la_x, ra_x)) and la_v >= 0.4 and ra_v >= 0.4:
        ankle_span = abs(ra_x - la_x)
        knee_span = abs(rk_x - lk_x)
        if ankle_span > 0.05:
            ratio = knee_span / ankle_span
            if ratio < thresholds["squat_min_valgus_ratio"] and phase in ("descending", "bottom", "ascending"):
                findings.append(
                    FormFinding(
                        code="KNEE_VALGUS",
                        severity="warning",
                        message="Knees appear to track inside the ankles (valgus alignment).",
                        recommendation="Actively push knees out in line with your toes.",
                        measurement=FormFindingMeasurement(name="knee_ankle_ratio", value=round(ratio, 2), unit="ratio"),
                    )
                )

    # 6. Incomplete Lockout Rule
    if avg_knee is not None and phase == "standing":
        if avg_knee < thresholds["squat_min_lockout_knee"]:
            findings.append(
                FormFinding(
                    code="INCOMPLETE_LOCKOUT",
                    severity="info",
                    message="Incomplete knee extension at top of squat.",
                    recommendation="Stand fully tall to finish each repetition.",
                    measurement=FormFindingMeasurement(name="knee_angle", value=round(avg_knee, 1), unit="degrees"),
                )
            )

    return findings, limitations


def evaluate_pushup_rules(
    joint_angles: Dict[str, Optional[float]],
    segment_distances: Dict[str, Optional[float]],
    landmarks: Dict[str, Any],
    exercise_info: Any,
    thresholds: Dict[str, float],
) -> Tuple[List[FormFinding], List[str]]:
    """Evaluates form rules for Push-up exercise."""
    findings: List[FormFinding] = []
    limitations: List[str] = []

    left_elbow = joint_angles.get("left_elbow")
    right_elbow = joint_angles.get("right_elbow")
    left_hip = joint_angles.get("left_hip")
    right_hip = joint_angles.get("right_hip")

    _, _, le_v = _get_lm_coord(landmarks.get("left_elbow"))
    _, _, re_v = _get_lm_coord(landmarks.get("right_elbow"))

    if le_v < 0.5 and re_v < 0.5:
        limitations.append("Both elbows occluded or low confidence — push-up form analysis limited.")
        return findings, limitations

    valid_elbows = [e for e in (left_elbow, right_elbow) if e is not None]
    avg_elbow = sum(valid_elbows) / len(valid_elbows) if valid_elbows else None
    phase = getattr(exercise_info, "phase", "top_plank") if exercise_info else "top_plank"

    # 1. Push-up Depth Rule
    if avg_elbow is not None:
        if phase == "bottom" and avg_elbow > thresholds["pushup_min_depth_elbow"]:
            findings.append(
                FormFinding(
                    code="PUSHUP_DEPTH_LIMITED",
                    severity="warning",
                    message="Observed push-up depth may be limited (> 100° elbow bend).",
                    recommendation="Lower chest until elbows reach approximately 90 degrees.",
                    measurement=FormFindingMeasurement(name="elbow_angle", value=round(avg_elbow, 1), unit="degrees"),
                )
            )

    # 2. Torso / Plank Alignment (Hip Sag or Piking)
    valid_hips = [h for h in (left_hip, right_hip) if h is not None]
    if valid_hips:
        avg_hip = sum(valid_hips) / len(valid_hips)
        if avg_hip < thresholds["pushup_min_hip_angle"]:
            findings.append(
                FormFinding(
                    code="HIP_SAG",
                    severity="warning",
                    message="Hip alignment deviates from straight plank line (hips sagging or piking).",
                    recommendation="Engage core and glutes to maintain a straight line from shoulders to ankles.",
                    measurement=FormFindingMeasurement(name="hip_angle", value=round(avg_hip, 1), unit="degrees"),
                )
            )

    # 3. Bilateral Elbow Asymmetry Rule
    if left_elbow is not None and right_elbow is not None and le_v >= 0.5 and re_v >= 0.5:
        elbow_diff = abs(left_elbow - right_elbow)
        if phase in ("lowering", "pushing") and elbow_diff > thresholds["pushup_max_elbow_asymmetry"]:
            findings.append(
                FormFinding(
                    code="ELBOW_ASYMMETRY",
                    severity="info",
                    message="Uneven elbow flexion between left and right arms.",
                    recommendation="Press evenly through both palms to balance pressing load.",
                    measurement=FormFindingMeasurement(name="elbow_difference", value=round(elbow_diff, 1), unit="degrees"),
                )
            )

    # 4. Incomplete Top Extension Rule
    if avg_elbow is not None and phase == "top_plank":
        if avg_elbow < thresholds["pushup_min_lockout_elbow"]:
            findings.append(
                FormFinding(
                    code="PUSHUP_INCOMPLETE_LOCKOUT",
                    severity="info",
                    message="Incomplete arm lockout at top of plank.",
                    recommendation="Press fully away from the floor at the top of the repetition.",
                    measurement=FormFindingMeasurement(name="elbow_angle", value=round(avg_elbow, 1), unit="degrees"),
                )
            )

    return findings, limitations


def evaluate_curl_rules(
    joint_angles: Dict[str, Optional[float]],
    segment_distances: Dict[str, Optional[float]],
    landmarks: Dict[str, Any],
    exercise_info: Any,
    thresholds: Dict[str, float],
) -> Tuple[List[FormFinding], List[str]]:
    """Evaluates form rules for Bicep Curl exercise."""
    findings: List[FormFinding] = []
    limitations: List[str] = []

    left_elbow = joint_angles.get("left_elbow")
    right_elbow = joint_angles.get("right_elbow")

    _, _, le_v = _get_lm_coord(landmarks.get("left_elbow"))
    _, _, re_v = _get_lm_coord(landmarks.get("right_elbow"))

    if le_v < 0.5 and re_v < 0.5:
        limitations.append("Both arms occluded or low confidence — bicep curl form analysis limited.")
        return findings, limitations

    valid_elbows = [e for e in (left_elbow, right_elbow) if e is not None]
    min_elbow = min(valid_elbows) if valid_elbows else None
    phase = getattr(exercise_info, "phase", "extended") if exercise_info else "extended"

    # 1. Incomplete Peak Contraction Rule
    if min_elbow is not None:
        if phase == "contracted" and min_elbow > thresholds["curl_max_flexion_elbow"]:
            findings.append(
                FormFinding(
                    code="CURL_INCOMPLETE_FLEXION",
                    severity="warning",
                    message="Observed curl does not reach peak contraction (> 75° elbow angle).",
                    recommendation="Curl upward through the full comfortable range of motion.",
                    measurement=FormFindingMeasurement(name="elbow_angle", value=round(min_elbow, 1), unit="degrees"),
                )
            )

    # 2. Incomplete Bottom Extension Rule
    if min_elbow is not None and phase == "extended":
        if min_elbow < thresholds["curl_min_extension_elbow"]:
            findings.append(
                FormFinding(
                    code="CURL_INCOMPLETE_EXTENSION",
                    severity="info",
                    message="Elbow remains partially flexed at bottom.",
                    recommendation="Lower weight completely until arm is comfortably extended.",
                    measurement=FormFindingMeasurement(name="elbow_angle", value=round(min_elbow, 1), unit="degrees"),
                )
            )

    # 3. Bilateral Arm Asymmetry Rule (when bilateral curls are performed)
    if left_elbow is not None and right_elbow is not None and le_v >= 0.5 and re_v >= 0.5:
        curl_diff = abs(left_elbow - right_elbow)
        if phase in ("curling", "lowering") and curl_diff > thresholds["curl_max_elbow_asymmetry"]:
            findings.append(
                FormFinding(
                    code="CURL_ASYMMETRY",
                    severity="info",
                    message="Arms are moving at different rates or ranges.",
                    recommendation="Synchronize movement tempo between both sides.",
                    measurement=FormFindingMeasurement(name="elbow_difference", value=round(curl_diff, 1), unit="degrees"),
                )
            )

    # 4. Torso Sway / Momentum Rule (image-space normalized displacement)
    ls_x, _, ls_v = _get_lm_coord(landmarks.get("left_shoulder"))
    rs_x, _, rs_v = _get_lm_coord(landmarks.get("right_shoulder"))
    lh_x, _, lh_v = _get_lm_coord(landmarks.get("left_hip"))
    rh_x, _, rh_v = _get_lm_coord(landmarks.get("right_hip"))

    if all(v is not None for v in (ls_x, rs_x, lh_x, rh_x)) and min(ls_v, rs_v, lh_v, rh_v) >= 0.5:
        mid_shoulder_x = (ls_x + rs_x) / 2.0
        mid_hip_x = (lh_x + rh_x) / 2.0
        sway_offset = abs(mid_shoulder_x - mid_hip_x)

        if sway_offset > thresholds["curl_max_torso_sway"] and phase in ("curling", "contracted"):
            findings.append(
                FormFinding(
                    code="EXCESSIVE_TORSO_SWAY",
                    severity="warning",
                    message="Noticeable torso movement detected during curl.",
                    recommendation="Keep torso steady and isolate movement to the elbows.",
                    measurement=FormFindingMeasurement(name="torso_offset", value=round(sway_offset, 3), unit="normalized"),
                )
            )

    return findings, limitations
