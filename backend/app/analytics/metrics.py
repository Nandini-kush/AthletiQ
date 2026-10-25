"""
AthletiQ Stage 7 — Performance Metrics Functions.
Pure mathematical and analytical calculations for exercise analytics.
"""
import math
from typing import Optional, List, Dict, Any

SCIENTIFIC_DISCLAIMER = (
    "Measurements are geometric approximations derived from 2D/3D webcam-based pose landmarks. "
    "Range of motion (ROM) represents observed angular excursion, not clinically validated goniometry. "
    "Repetitions per minute indicates movement cadence, not mechanical power. "
    "Bilateral asymmetry reflects kinematic posture balance, not injury diagnosis."
)

def calculate_pace_rpm(repetitions: int, duration_sec: int) -> Optional[float]:
    """
    Calculate exercise pace in repetitions per minute.
    Safe against zero or invalid durations.
    """
    if repetitions is None or duration_sec is None:
        return None
    if duration_sec <= 0 or repetitions < 0:
        return None
    return round((float(repetitions) / float(duration_sec)) * 60.0, 2)


def calculate_joint_angle_stats(samples: List[float]) -> Optional[Dict[str, float]]:
    """
    Calculate min, max, mean, and observed range of motion from a list of angle samples.
    Excludes invalid, None, NaN, inf, or out-of-range (<0 or >180) values.
    """
    if not samples:
        return None

    valid = []
    for s in samples:
        if s is None:
            continue
        try:
            val = float(s)
            if math.isnan(val) or math.isinf(val):
                continue
            if 0.0 <= val <= 180.0:
                valid.append(val)
        except (ValueError, TypeError):
            continue

    if not valid:
        return None

    min_val = min(valid)
    max_val = max(valid)
    mean_val = sum(valid) / len(valid)
    rom_val = max_val - min_val

    return {
        "min": round(min_val, 1),
        "max": round(max_val, 1),
        "mean": round(mean_val, 1),
        "rom": round(rom_val, 1),
        "sample_count": len(valid)
    }


def compare_rom(
    current_rom: Optional[float],
    baseline_rom: Optional[float],
    noise_margin: float = 2.0
) -> Dict[str, Any]:
    """
    Compare observed range of motion between compatible sessions.
    Changes within noise_margin (default 2.0 deg) are classified as 'consistent'
    rather than claiming improvement or regression.
    """
    if current_rom is None or baseline_rom is None:
        return {
            "diff_deg": None,
            "status": "insufficient_data",
            "note": "Insufficient compatible ROM samples for comparison."
        }

    diff = round(float(current_rom) - float(baseline_rom), 1)

    if abs(diff) <= noise_margin:
        status = "consistent"
        note = f"Observed ROM within expected optical measurement margin ({diff:+.1f}°)."
    elif diff > noise_margin:
        status = "wider"
        note = f"Observed ROM is {diff:+.1f}° wider than baseline session."
    else:
        status = "narrower"
        note = f"Observed ROM is {diff:+.1f}° narrower than baseline session."

    return {
        "diff_deg": diff,
        "status": status,
        "note": note
    }


def compare_sessions(current_session, baseline_session) -> Optional[Dict[str, Any]]:
    """
    Compare current session against a baseline session of the same exercise.
    Calculates repetition count delta, duration delta, pace delta, and primary ROM delta.
    """
    if baseline_session is None:
        return None

    rep_diff = current_session.total_repetitions - baseline_session.total_repetitions
    duration_diff = current_session.duration - baseline_session.duration

    current_pace = current_session.avg_pace_rpm or calculate_pace_rpm(
        current_session.total_repetitions, current_session.duration
    )
    baseline_pace = baseline_session.avg_pace_rpm or calculate_pace_rpm(
        baseline_session.total_repetitions, baseline_session.duration
    )

    pace_diff = (
        round(current_pace - baseline_pace, 2)
        if (current_pace is not None and baseline_pace is not None)
        else None
    )

    # Extract primary joint ROM for comparison if available
    current_metrics = getattr(current_session, "summary_metrics", {}) or {}
    baseline_metrics = getattr(baseline_session, "summary_metrics", {}) or {}

    current_roms = current_metrics.get("rom_stats", {})
    baseline_roms = baseline_metrics.get("rom_stats", {})

    # Detect primary joint key based on exercise
    exercise = (current_session.exercise_name or "").lower()
    primary_joint = "knee" if "squat" in exercise else ("elbow" if ("push" in exercise or "curl" in exercise) else None)

    rom_diff_deg = None
    rom_status = "unavailable"
    if primary_joint:
        curr_val = current_roms.get(primary_joint) or current_roms.get(f"{primary_joint}_rom")
        base_val = baseline_roms.get(primary_joint) or baseline_roms.get(f"{primary_joint}_rom")
        if curr_val is not None and base_val is not None:
            comparison = compare_rom(curr_val, base_val)
            rom_diff_deg = comparison["diff_deg"]
            rom_status = comparison["status"]

    notes = []
    if rep_diff > 0:
        notes.append(f"+{rep_diff} reps vs baseline")
    elif rep_diff < 0:
        notes.append(f"{rep_diff} reps vs baseline")
    else:
        notes.append("Identical reps to baseline")

    if pace_diff is not None:
        notes.append(f"{pace_diff:+.1f} rpm cadence change")

    return {
        "baseline_session_id": baseline_session.id,
        "baseline_date": baseline_session.started_at,
        "rep_diff": rep_diff,
        "duration_diff_sec": duration_diff,
        "pace_diff_rpm": pace_diff,
        "rom_diff_deg": rom_diff_deg,
        "summary_note": "; ".join(notes)
    }
