"""
test_stage6.py — AthletiQ Stage 6: Exercise Form Correction & Real-Time Feedback Tests

Tests cover:
  - Squat rules: limited depth, excessive torso lean, knee asymmetry, knee valgus, incomplete lockout
  - Push-up rules: limited depth, hip sag/plank alignment, elbow asymmetry, incomplete lockout
  - Bicep curl rules: incomplete peak flexion, incomplete extension, arm asymmetry, torso sway
  - Missing and low-visibility landmark safety (limitations reporting)
  - Threshold boundaries and deterministic evaluations
  - Temporal confirmation window (2-frame dwell requirement)
  - Feedback repeat cooldown management
  - Exercise switching and reset behavior
  - FormAnalysisResult Pydantic schema validation
  - FrameProcessor & WebSocket integration with form_feedback field
"""

import sys
import json
import time
import base64
from typing import Any, Dict, List, Optional

# Ensure UTF-8 / ASCII safe output on Windows terminal
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASS = "[PASS]"
FAIL = "[FAIL]"

_results: List[str] = []


def assert_equal(label: str, actual, expected, tol: Optional[float] = None):
    if tol is not None:
        ok = actual is not None and abs(actual - expected) <= tol
    else:
        ok = actual == expected
    status = PASS if ok else FAIL
    _results.append(status)
    symbol = "+" if ok else "x"
    print(f"  [{symbol}] {label}: {actual!r} {'~=' if tol else '=='} {expected!r}")
    if not ok:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(label: str, condition: bool):
    _results.append(PASS if condition else FAIL)
    symbol = "+" if condition else "x"
    print(f"  [{symbol}] {label}")
    if not condition:
        raise AssertionError(f"{label}: condition is False")


def assert_false(label: str, condition: bool):
    assert_true(label, not condition)


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Helpers for Synthetic Landmarks
# ---------------------------------------------------------------------------

def _make_lms(**kwargs) -> Dict[str, Any]:
    """Creates a dictionary of landmark points with defaults."""
    res = {}
    for name, data in kwargs.items():
        if isinstance(data, dict):
            res[name] = data
        elif isinstance(data, (tuple, list)):
            x = data[0]
            y = data[1] if len(data) > 1 else 0.0
            vis = data[2] if len(data) > 2 else 0.95
            res[name] = {"name": name, "x": x, "y": y, "z": 0.0, "visibility": vis}
    return res


# ---------------------------------------------------------------------------
# TEST SUITE 1 — Squat Form Rules
# ---------------------------------------------------------------------------

def test_squat_form_rules():
    section("Suite 1 — Squat Form Rules")
    from app.form_analysis.rules import evaluate_squat_rules, DEFAULT_FORM_THRESHOLDS

    class MockExerciseInfo:
        def __init__(self, phase):
            self.phase = phase

    lms = _make_lms(
        left_knee=(0.4, 0.7, 0.95),
        right_knee=(0.6, 0.7, 0.95),
        left_ankle=(0.4, 0.95, 0.95),
        right_ankle=(0.6, 0.95, 0.95),
        left_hip=(0.4, 0.5, 0.95),
        right_hip=(0.6, 0.5, 0.95),
    )

    # 1. Depth Limited Rule: In bottom phase, knee angle 115 deg > 105 deg
    angles_limited = {"left_knee": 115.0, "right_knee": 115.0, "left_hip": 80.0, "right_hip": 80.0}
    findings, _ = evaluate_squat_rules(angles_limited, {}, lms, MockExerciseInfo("bottom"), DEFAULT_FORM_THRESHOLDS)
    codes = [f.code for f in findings]
    assert_true("SQUAT_DEPTH_LIMITED finding triggered", "SQUAT_DEPTH_LIMITED" in codes)

    # 1b. Good Depth: In bottom phase, knee angle 95 deg <= 105 deg
    angles_good = {"left_knee": 95.0, "right_knee": 95.0, "left_hip": 80.0, "right_hip": 80.0}
    findings_good, _ = evaluate_squat_rules(angles_good, {}, lms, MockExerciseInfo("bottom"), DEFAULT_FORM_THRESHOLDS)
    assert_false("Good depth does not trigger SQUAT_DEPTH_LIMITED", "SQUAT_DEPTH_LIMITED" in [f.code for f in findings_good])

    # 2. Excessive Torso Lean Rule: Hip angle 50 deg < 60 deg
    angles_lean = {"left_knee": 95.0, "right_knee": 95.0, "left_hip": 50.0, "right_hip": 50.0}
    findings_lean, _ = evaluate_squat_rules(angles_lean, {}, lms, MockExerciseInfo("descending"), DEFAULT_FORM_THRESHOLDS)
    assert_true("EXCESSIVE_TORSO_LEAN triggered when hip < 60 deg", "EXCESSIVE_TORSO_LEAN" in [f.code for f in findings_lean])

    # 3. Bilateral Knee Asymmetry Rule: left 120, right 95 -> diff 25 > 15 deg
    angles_asym = {"left_knee": 120.0, "right_knee": 95.0, "left_hip": 80.0, "right_hip": 80.0}
    findings_asym, _ = evaluate_squat_rules(angles_asym, {}, lms, MockExerciseInfo("descending"), DEFAULT_FORM_THRESHOLDS)
    assert_true("KNEE_ASYMMETRY triggered when bilateral diff > 15 deg", "KNEE_ASYMMETRY" in [f.code for f in findings_asym])

    # 4. Knee Valgus (Inward Caving) Rule: knees span 0.1 vs ankles span 0.3 (ratio 0.33 < 0.82)
    lms_valgus = _make_lms(
        left_knee=(0.45, 0.7, 0.95),
        right_knee=(0.55, 0.7, 0.95),
        left_ankle=(0.35, 0.95, 0.95),
        right_ankle=(0.65, 0.95, 0.95),
    )
    findings_valgus, _ = evaluate_squat_rules(angles_good, {}, lms_valgus, MockExerciseInfo("descending"), DEFAULT_FORM_THRESHOLDS)
    assert_true("KNEE_VALGUS triggered when knee span / ankle span < 0.82", "KNEE_VALGUS" in [f.code for f in findings_valgus])

    # 5. Incomplete Lockout: In standing phase, knee angle 145 deg < 155 deg
    angles_incomplete = {"left_knee": 145.0, "right_knee": 145.0}
    findings_lockout, _ = evaluate_squat_rules(angles_incomplete, {}, lms, MockExerciseInfo("standing"), DEFAULT_FORM_THRESHOLDS)
    assert_true("INCOMPLETE_LOCKOUT triggered when standing knee < 155 deg", "INCOMPLETE_LOCKOUT" in [f.code for f in findings_lockout])

    print("Suite 1 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 2 — Push-up Form Rules
# ---------------------------------------------------------------------------

def test_pushup_form_rules():
    section("Suite 2 — Push-up Form Rules")
    from app.form_analysis.rules import evaluate_pushup_rules, DEFAULT_FORM_THRESHOLDS

    class MockExerciseInfo:
        def __init__(self, phase):
            self.phase = phase

    lms = _make_lms(
        left_elbow=(0.3, 0.5, 0.95),
        right_elbow=(0.3, 0.6, 0.95),
        left_hip=(0.6, 0.5, 0.95),
        right_hip=(0.6, 0.6, 0.95),
    )

    # 1. Depth Limited: At bottom, elbow angle 115 deg > 100 deg
    angles_limited = {"left_elbow": 115.0, "right_elbow": 115.0, "left_hip": 165.0, "right_hip": 165.0}
    findings, _ = evaluate_pushup_rules(angles_limited, {}, lms, MockExerciseInfo("bottom"), DEFAULT_FORM_THRESHOLDS)
    assert_true("PUSHUP_DEPTH_LIMITED triggered when bottom elbow > 100 deg", "PUSHUP_DEPTH_LIMITED" in [f.code for f in findings])

    # 1b. Good Depth: elbow 85 deg <= 100 deg
    angles_good = {"left_elbow": 85.0, "right_elbow": 85.0, "left_hip": 165.0, "right_hip": 165.0}
    findings_good, _ = evaluate_pushup_rules(angles_good, {}, lms, MockExerciseInfo("bottom"), DEFAULT_FORM_THRESHOLDS)
    assert_false("Good pushup depth does not trigger PUSHUP_DEPTH_LIMITED", "PUSHUP_DEPTH_LIMITED" in [f.code for f in findings_good])

    # 2. Hip Sag / Piking Rule: Hip angle 125 deg < 140 deg
    angles_sag = {"left_elbow": 85.0, "right_elbow": 85.0, "left_hip": 125.0, "right_hip": 125.0}
    findings_sag, _ = evaluate_pushup_rules(angles_sag, {}, lms, MockExerciseInfo("lowering"), DEFAULT_FORM_THRESHOLDS)
    assert_true("HIP_SAG triggered when hip angle < 140 deg", "HIP_SAG" in [f.code for f in findings_sag])

    # 3. Bilateral Elbow Asymmetry: left 85, right 110 -> diff 25 > 15 deg
    angles_asym = {"left_elbow": 85.0, "right_elbow": 110.0, "left_hip": 165.0, "right_hip": 165.0}
    findings_asym, _ = evaluate_pushup_rules(angles_asym, {}, lms, MockExerciseInfo("pushing"), DEFAULT_FORM_THRESHOLDS)
    assert_true("ELBOW_ASYMMETRY triggered when elbow diff > 15 deg", "ELBOW_ASYMMETRY" in [f.code for f in findings_asym])

    # 4. Incomplete Lockout: in top_plank, elbow 135 deg < 145 deg
    angles_lockout = {"left_elbow": 135.0, "right_elbow": 135.0, "left_hip": 165.0, "right_hip": 165.0}
    findings_lockout, _ = evaluate_pushup_rules(angles_lockout, {}, lms, MockExerciseInfo("top_plank"), DEFAULT_FORM_THRESHOLDS)
    assert_true("PUSHUP_INCOMPLETE_LOCKOUT triggered in top_plank when elbow < 145 deg", "PUSHUP_INCOMPLETE_LOCKOUT" in [f.code for f in findings_lockout])

    print("Suite 2 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 3 — Bicep Curl Form Rules
# ---------------------------------------------------------------------------

def test_curl_form_rules():
    section("Suite 3 — Bicep Curl Form Rules")
    from app.form_analysis.rules import evaluate_curl_rules, DEFAULT_FORM_THRESHOLDS

    class MockExerciseInfo:
        def __init__(self, phase):
            self.phase = phase

    lms = _make_lms(
        left_elbow=(0.35, 0.4, 0.95),
        right_elbow=(0.65, 0.4, 0.95),
        left_shoulder=(0.35, 0.2, 0.95),
        right_shoulder=(0.65, 0.2, 0.95),
        left_hip=(0.35, 0.55, 0.95),
        right_hip=(0.65, 0.55, 0.95),
    )

    # 1. Incomplete Peak Contraction: at contracted, elbow 85 deg > 75 deg
    angles_flex = {"left_elbow": 85.0}
    findings, _ = evaluate_curl_rules(angles_flex, {}, lms, MockExerciseInfo("contracted"), DEFAULT_FORM_THRESHOLDS)
    assert_true("CURL_INCOMPLETE_FLEXION triggered when contracted elbow > 75 deg", "CURL_INCOMPLETE_FLEXION" in [f.code for f in findings])

    # 2. Incomplete Extension at bottom: in extended, elbow 125 deg < 140 deg
    angles_ext = {"left_elbow": 125.0}
    findings_ext, _ = evaluate_curl_rules(angles_ext, {}, lms, MockExerciseInfo("extended"), DEFAULT_FORM_THRESHOLDS)
    assert_true("CURL_INCOMPLETE_EXTENSION triggered when extended elbow < 140 deg", "CURL_INCOMPLETE_EXTENSION" in [f.code for f in findings_ext])

    # 3. Bilateral Arm Asymmetry: left 60, right 95 -> diff 35 > 20 deg
    angles_asym = {"left_elbow": 60.0, "right_elbow": 95.0}
    findings_asym, _ = evaluate_curl_rules(angles_asym, {}, lms, MockExerciseInfo("curling"), DEFAULT_FORM_THRESHOLDS)
    assert_true("CURL_ASYMMETRY triggered when bilateral curl diff > 20 deg", "CURL_ASYMMETRY" in [f.code for f in findings_asym])

    # 4. Excessive Torso Sway: shoulders shifted horizontally from hips by 0.12 > 0.08
    lms_sway = _make_lms(
        left_elbow=(0.4, 0.4, 0.95),
        right_elbow=(0.7, 0.4, 0.95),
        left_shoulder=(0.48, 0.2, 0.95),
        right_shoulder=(0.78, 0.2, 0.95), # mid-shoulder x = 0.63
        left_hip=(0.35, 0.55, 0.95),
        right_hip=(0.65, 0.55, 0.95),     # mid-hip x = 0.50 -> offset = 0.13 > 0.08
    )
    findings_sway, _ = evaluate_curl_rules({"left_elbow": 60.0}, {}, lms_sway, MockExerciseInfo("curling"), DEFAULT_FORM_THRESHOLDS)
    assert_true("EXCESSIVE_TORSO_SWAY triggered when shoulder offset > 0.08", "EXCESSIVE_TORSO_SWAY" in [f.code for f in findings_sway])

    print("Suite 3 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 4 — Missing & Low-Visibility Landmarks Safety
# ---------------------------------------------------------------------------

def test_missing_and_low_vis_landmarks():
    section("Suite 4 — Missing and Low-Visibility Landmarks Safety")
    from app.form_analysis.rules import evaluate_squat_rules, DEFAULT_FORM_THRESHOLDS

    # Low visibility on both knees (< 0.5)
    low_vis_lms = _make_lms(
        left_knee=(0.4, 0.7, 0.2),
        right_knee=(0.6, 0.7, 0.3),
    )
    findings, limitations = evaluate_squat_rules(
        {"left_knee": 120.0, "right_knee": 120.0},
        {},
        low_vis_lms,
        None,
        DEFAULT_FORM_THRESHOLDS,
    )
    assert_equal("No false findings emitted when landmarks occluded", len(findings), 0)
    assert_true("Limitation reported when landmarks have low visibility", len(limitations) > 0)

    print("Suite 4 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 5 — Temporal Confirmation & Hysteresis
# ---------------------------------------------------------------------------

def test_temporal_confirmation():
    section("Suite 5 — Temporal Confirmation Window (Dwell Requirement)")
    from app.form_analysis.feedback import FeedbackStabilizer
    from app.form_analysis.schemas import FormFinding

    stabilizer = FeedbackStabilizer(confirmation_frames=2, cooldown_seconds=2.0)
    finding = FormFinding(code="TEST_CODE", severity="warning", message="Test", recommendation="Test")

    # Frame 1: First observation (count=1 < 2) -> should NOT emit yet
    out1 = stabilizer.filter_findings([finding], timestamp=100.0)
    assert_equal("Single-frame jitter rejected (not confirmed)", len(out1), 0)

    # Frame 2: Second consecutive observation (count=2 >= 2) -> CONFIRMED and emitted
    out2 = stabilizer.filter_findings([finding], timestamp=100.1)
    assert_equal("Second consecutive frame confirms finding", len(out2), 1)
    assert_equal("Emitted code matches", out2[0].code, "TEST_CODE")

    print("Suite 5 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 6 — Feedback Repeat Cooldown Management
# ---------------------------------------------------------------------------

def test_feedback_cooldown():
    section("Suite 6 — Feedback Repeat Cooldown Management")
    from app.form_analysis.feedback import FeedbackStabilizer
    from app.form_analysis.schemas import FormFinding

    stabilizer = FeedbackStabilizer(confirmation_frames=1, cooldown_seconds=1.5)
    f = FormFinding(code="COOLDOWN_TEST", severity="warning", message="Test", recommendation="Test")

    # Time 0.0: First emit
    out1 = stabilizer.filter_findings([f], timestamp=0.0)
    assert_equal("Initial emit successful", len(out1), 1)

    # Time 0.5s: Finding still observed within cooldown (< 1.5s) -> keeps existing active finding without duplicate blast
    out2 = stabilizer.filter_findings([f], timestamp=0.5)
    assert_equal("Active finding maintained within cooldown", len(out2), 1)

    print("Suite 6 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 7 — Exercise Switching & Reset Behavior
# ---------------------------------------------------------------------------

def test_exercise_switching_and_reset():
    section("Suite 7 — Exercise Switching and Reset Behavior")
    from app.form_analysis.analyzer import FormAnalyzer

    analyzer = FormAnalyzer(confirmation_frames=1)

    lms = _make_lms(
        left_knee=(0.4, 0.7, 0.95),
        right_knee=(0.6, 0.7, 0.95),
        left_ankle=(0.4, 0.95, 0.95),
        right_ankle=(0.6, 0.95, 0.95),
    )

    class MockExerciseInfo:
        phase = "bottom"

    # Analyze squat with limited depth
    res1 = analyzer.analyze(
        exercise_name="squat",
        biomechanics={"joint_angles": {"left_knee": 115.0, "right_knee": 115.0}},
        exercise_info=MockExerciseInfo(),
        landmarks=list(lms.values()),
        timestamp=1.0,
    )
    assert_equal("Squat analysis active", res1.exercise, "squat")
    assert_equal("Form status needs_attention", res1.form_status, "needs_attention")
    assert_true("Squat finding present", len(res1.findings) > 0)

    # Switch to push_up -> must cleanly reset squat findings
    res2 = analyzer.analyze(
        exercise_name="push_up",
        biomechanics={"joint_angles": {"left_elbow": 160.0, "right_elbow": 160.0, "left_hip": 165.0, "right_hip": 165.0}},
        exercise_info=MockExerciseInfo(),
        landmarks=list(lms.values()),
        timestamp=2.0,
    )
    assert_equal("Switched exercise to push_up", res2.exercise, "push_up")
    squat_codes = [f.code for f in res2.findings if "SQUAT" in f.code]
    assert_equal("Old squat findings cleared on exercise switch", len(squat_codes), 0)

    # Reset
    analyzer.reset()
    assert_equal("Stabilizer cleared on reset", len(analyzer.stabilizer._active_findings), 0)

    print("Suite 7 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 8 — FormAnalysisResult Pydantic Schema Validation
# ---------------------------------------------------------------------------

def test_form_analysis_schema():
    section("Suite 8 — FormAnalysisResult Pydantic Schema Validation")
    from app.form_analysis.schemas import FormAnalysisResult, FormFinding, FormFindingMeasurement

    finding = FormFinding(
        code="TEST_FINDING",
        severity="warning",
        message="Test message",
        recommendation="Test recommendation",
        measurement=FormFindingMeasurement(name="knee_angle", value=112.4, unit="degrees"),
    )
    res = FormAnalysisResult(
        exercise="squat",
        analysis_available=True,
        form_status="needs_attention",
        findings=[finding],
        limitations=["Camera angle slightly oblique."],
    )

    # JSON roundtrip
    dumped = res.model_dump_json()
    parsed = json.loads(dumped)
    assert_equal("Serialized exercise matches", parsed["exercise"], "squat")
    assert_equal("Serialized form_status matches", parsed["form_status"], "needs_attention")
    assert_equal("Serialized measurement value", parsed["findings"][0]["measurement"]["value"], 112.4)

    # Re-validate
    validated = FormAnalysisResult.model_validate(parsed)
    assert_true("Pydantic validation succeeds", isinstance(validated, FormAnalysisResult))

    print("Suite 8 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 9 — FrameProcessor Integration with Form Feedback
# ---------------------------------------------------------------------------

def _make_black_frame_b64() -> str:
    import cv2
    import numpy as np
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf.tobytes()).decode("ascii")


def test_frame_processor_form_feedback():
    section("Suite 9 — FrameProcessor Integration with Form Feedback")
    from app.cv.frame_processor import FrameProcessor

    fp = FrameProcessor()
    b64 = _make_black_frame_b64()

    # When no pose is detected, form_feedback should be None
    res = fp.process_frame(b64, exercise_name="squat")
    assert_equal("No pose detected -> form_feedback is None", res.form_feedback, None)

    print("Suite 9 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 10 — WebSocket /ws/pose Integration with Form Feedback
# ---------------------------------------------------------------------------

def test_websocket_form_feedback():
    section("Suite 10 — WebSocket /ws/pose Integration with Form Feedback")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    with client.websocket_connect("/ws/pose") as ws:
        # Select exercise
        ws.send_text(json.dumps({"type": "select_exercise", "exercise": "squat"}))
        msg1 = ws.receive_json()
        assert_equal("WebSocket confirms exercise selection", msg1.get("type"), "exercise_selected")

        # Send frame payload with exercise
        b64 = _make_black_frame_b64()
        ws.send_text(json.dumps({"frame": b64, "exercise": "squat"}))
        msg2 = ws.receive_json()
        assert_true("Response contains form_feedback field", "form_feedback" in msg2)

    print("Suite 10 PASSED")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_all():
    suites = [
        ("1 — Squat Form Rules",                test_squat_form_rules),
        ("2 — Push-up Form Rules",              test_pushup_form_rules),
        ("3 — Bicep Curl Form Rules",           test_curl_form_rules),
        ("4 — Missing & Low-Vis Landmarks",     test_missing_and_low_vis_landmarks),
        ("5 — Temporal Confirmation",           test_temporal_confirmation),
        ("6 — Feedback Repeat Cooldown",        test_feedback_cooldown),
        ("7 — Exercise Switching & Reset",      test_exercise_switching_and_reset),
        ("8 — Form Analysis Schema Validation", test_form_analysis_schema),
        ("9 — FrameProcessor Form Feedback",    test_frame_processor_form_feedback),
        ("10 — WebSocket Form Feedback",        test_websocket_form_feedback),
    ]

    passed_suites = 0
    failed_suites = 0
    failed_names: List[str] = []

    for name, fn in suites:
        try:
            fn()
            passed_suites += 1
        except AssertionError as e:
            print(f"\n  *** SUITE FAILED: {e}")
            failed_suites += 1
            failed_names.append(name)
        except Exception as e:
            print(f"\n  *** UNEXPECTED ERROR in {name}: {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()
            failed_suites += 1
            failed_names.append(name)

    print(f"\n{'='*60}")
    print(f"  STAGE 6 TEST RESULTS: {passed_suites}/{len(suites)} suites passed")
    if failed_names:
        print(f"  FAILED: {', '.join(failed_names)}")
    else:
        print("  ALL STAGE 6 TESTS PASSED")
    print(f"{'='*60}\n")

    if failed_suites > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
