"""
test_stage5.py — AthletiQ Stage 5: Exercise Classification & Repetition Counting Tests

Tests cover:
  - SquatStateMachine: full cycle, partial movement rejection, knee valgus cue, reset
  - BicepCurlStateMachine: full cycle, partial curl rejection, peak contraction, reset
  - PushUpStateMachine: full cycle, partial push-up rejection, hip sag cue, reset
  - Duplicate-count prevention / temporal hysteresis
  - Missing and low-visibility landmark handling
  - Posture / Candidate classifier heuristics
  - ExerciseAnalysisManager switching and reset
  - FrameProcessor process_frame() with active exercise
  - WebSocket /ws/pose with exercise selection and repetition counting
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
# TEST SUITE 1 — SquatStateMachine Full Cycle & Partial Movement
# ---------------------------------------------------------------------------

def test_squat_state_machine():
    section("Suite 1 — SquatStateMachine Full Cycle & Partial Movement")
    from app.exercises.squat import SquatStateMachine

    sm = SquatStateMachine()
    assert_equal("Initial phase is standing", sm.current_phase, "standing")
    assert_equal("Initial reps == 0", sm.reps, 0)

    # Mock empty distances and landmarks
    dist = {}
    lms = {}

    t = 1000.0

    # 1. Standing upright (170 deg)
    res = sm.update({"left_knee": 170.0, "right_knee": 170.0}, dist, lms, timestamp=t)
    assert_equal("Upright knee -> standing", res.phase, "standing")
    assert_equal("Reps == 0", res.repetitions, 0)
    assert_false("Not rep completed", res.is_rep_completed)

    # 2. Descending (130 deg)
    t += 0.2
    res = sm.update({"left_knee": 130.0, "right_knee": 130.0}, dist, lms, timestamp=t)
    assert_equal("130 deg -> descending", res.phase, "descending")
    assert_true("Progress > 0%", res.phase_progress_pct > 0.0)

    # 3. Partial rep abort: ascend back to standing (165 deg) without hitting bottom
    t += 0.2
    res = sm.update({"left_knee": 165.0, "right_knee": 165.0}, dist, lms, timestamp=t)
    assert_equal("Aborted descent -> returns to standing", res.phase, "standing")
    assert_equal("Partial rep rejected -> reps still 0", res.repetitions, 0)
    assert_false("No rep count", res.is_rep_completed)

    # 4. Now perform a complete valid repetition:
    # 4a. Descending (135 deg)
    t += 0.2
    res = sm.update({"left_knee": 135.0, "right_knee": 135.0}, dist, lms, timestamp=t)
    assert_equal("Phase -> descending", res.phase, "descending")

    # 4b. Bottom depth reached (90 deg <= 100 deg)
    t += 0.2
    res = sm.update({"left_knee": 90.0, "right_knee": 90.0}, dist, lms, timestamp=t)
    assert_equal("Phase -> bottom", res.phase, "bottom")
    assert_true("Bottom reached flag set", sm.reached_bottom)

    # 4c. Ascending (125 deg > 115 deg)
    t += 0.2
    res = sm.update({"left_knee": 125.0, "right_knee": 125.0}, dist, lms, timestamp=t)
    assert_equal("Phase -> ascending", res.phase, "ascending")
    assert_true("Progress > 50%", res.phase_progress_pct > 50.0)

    # 4d. Standing lockout (165 deg >= 160 deg) -> Rep completes!
    t += 0.2
    res = sm.update({"left_knee": 165.0, "right_knee": 165.0}, dist, lms, timestamp=t)
    assert_equal("Phase -> standing", res.phase, "standing")
    assert_equal("Rep counted! reps == 1", res.repetitions, 1)
    assert_true("is_rep_completed == True", res.is_rep_completed)

    # 5. Reset test
    sm.reset()
    assert_equal("After reset: reps == 0", sm.reps, 0)
    assert_equal("After reset: phase == standing", sm.current_phase, "standing")
    assert_false("After reset: reached_bottom == False", sm.reached_bottom)

    print("Suite 1 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 2 — Squat Knee Valgus & Form Cues
# ---------------------------------------------------------------------------

def test_squat_form_cues():
    section("Suite 2 — Squat Form Cues & Valgus Detection")
    from app.exercises.squat import SquatStateMachine

    sm = SquatStateMachine()
    t = 2000.0

    # Start descent
    sm.update({"left_knee": 130.0, "right_knee": 130.0}, {}, {}, timestamp=t)

    # Simulate knee valgus: knees narrow (x diff = 0.05) relative to ankles (x diff = 0.3)
    lms = {
        "left_knee": {"x": 0.48},
        "right_knee": {"x": 0.52},
        "left_ankle": {"x": 0.35},
        "right_ankle": {"x": 0.65},
    }
    t += 0.2
    res = sm.update({"left_knee": 120.0, "right_knee": 120.0}, {}, lms, timestamp=t)
    valgus_cues = [c for c in res.form_cues if "caving" in c.lower()]
    assert_true("Valgus cue triggered when knees cave inwards", len(valgus_cues) > 0)

    print("Suite 2 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 3 — BicepCurlStateMachine Full Cycle & Partial Movement
# ---------------------------------------------------------------------------

def test_bicep_curl_state_machine():
    section("Suite 3 — BicepCurlStateMachine Full Cycle & Partial Movement")
    from app.exercises.bicep_curl import BicepCurlStateMachine

    sm = BicepCurlStateMachine()
    assert_equal("Initial phase is extended", sm.current_phase, "extended")
    assert_equal("Initial reps == 0", sm.reps, 0)

    t = 3000.0

    # 1. Arm extended (160 deg)
    res = sm.update({"left_elbow": 160.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> extended", res.phase, "extended")
    assert_equal("Reps == 0", res.repetitions, 0)

    # 2. Start curling (125 deg)
    t += 0.2
    res = sm.update({"left_elbow": 125.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> curling", res.phase, "curling")

    # 3. Partial curl: lower back down to 155 deg without reaching peak contraction (< 65 deg)
    t += 0.2
    res = sm.update({"left_elbow": 155.0}, {}, {}, timestamp=t)
    assert_equal("Partial curl aborted -> returns to extended", res.phase, "extended")
    assert_equal("Reps still 0", res.repetitions, 0)

    # 4. Valid full repetition:
    # 4a. Curling (120 deg)
    t += 0.2
    res = sm.update({"left_elbow": 120.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> curling", res.phase, "curling")

    # 4b. Contracted at top (55 deg <= 65 deg)
    t += 0.2
    res = sm.update({"left_elbow": 55.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> contracted", res.phase, "contracted")
    assert_true("Peak contraction reached", sm.reached_contracted)

    # 4c. Lowering (95 deg > 80 deg)
    t += 0.2
    res = sm.update({"left_elbow": 95.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> lowering", res.phase, "lowering")

    # 4d. Extended at bottom (155 deg >= 150 deg) -> Rep completes!
    t += 0.2
    res = sm.update({"left_elbow": 155.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> extended", res.phase, "extended")
    assert_equal("Reps == 1", res.repetitions, 1)
    assert_true("is_rep_completed == True", res.is_rep_completed)

    # Reset
    sm.reset()
    assert_equal("Reps reset to 0", sm.reps, 0)

    print("Suite 3 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 4 — PushUpStateMachine Full Cycle & Hip Sag Cue
# ---------------------------------------------------------------------------

def test_push_up_state_machine():
    section("Suite 4 — PushUpStateMachine Full Cycle & Plank Form Cue")
    from app.exercises.push_up import PushUpStateMachine

    sm = PushUpStateMachine()
    assert_equal("Initial phase is top_plank", sm.current_phase, "top_plank")
    assert_equal("Initial reps == 0", sm.reps, 0)

    t = 4000.0

    # 1. Top plank position (160 deg elbow, 170 deg hip)
    res = sm.update({"left_elbow": 160.0, "left_hip": 170.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> top_plank", res.phase, "top_plank")

    # 2. Lowering (120 deg elbow)
    t += 0.2
    res = sm.update({"left_elbow": 120.0, "left_hip": 170.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> lowering", res.phase, "lowering")

    # 3. Partial rep: return to top (155 deg) without hitting bottom
    t += 0.2
    res = sm.update({"left_elbow": 155.0, "left_hip": 170.0}, {}, {}, timestamp=t)
    assert_equal("Partial rep aborted -> top_plank", res.phase, "top_plank")
    assert_equal("Reps still 0", res.repetitions, 0)

    # 4. Valid full push-up:
    # 4a. Lowering (115 deg)
    t += 0.2
    sm.update({"left_elbow": 115.0, "left_hip": 165.0}, {}, {}, timestamp=t)

    # 4b. Bottom chest depth (80 deg <= 90 deg)
    t += 0.2
    res = sm.update({"left_elbow": 80.0, "left_hip": 165.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> bottom", res.phase, "bottom")

    # 4c. Pushing back up (115 deg > 105 deg)
    t += 0.2
    res = sm.update({"left_elbow": 115.0, "left_hip": 165.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> pushing", res.phase, "pushing")

    # 4d. Lockout in plank (155 deg >= 150 deg) -> Rep completes!
    t += 0.2
    res = sm.update({"left_elbow": 155.0, "left_hip": 165.0}, {}, {}, timestamp=t)
    assert_equal("Phase -> top_plank", res.phase, "top_plank")
    assert_equal("Reps == 1", res.repetitions, 1)
    assert_true("is_rep_completed == True", res.is_rep_completed)

    # 5. Form Cue: Hip sag / piking (hip angle < 140 deg)
    t += 0.2
    res = sm.update({"left_elbow": 130.0, "left_hip": 125.0}, {}, {}, timestamp=t)
    sag_cues = [c for c in res.form_cues if "sagging" in c.lower() or "piking" in c.lower()]
    assert_true("Hip sag cue triggered when hip < 140 deg", len(sag_cues) > 0)

    print("Suite 4 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 5 — Duplicate-Count Prevention / Hysteresis
# ---------------------------------------------------------------------------

def test_duplicate_count_prevention():
    section("Suite 5 — Temporal Hysteresis & Duplicate Count Prevention")
    from app.exercises.squat import SquatStateMachine

    sm = SquatStateMachine()
    t = 5000.0

    # Move through full cycle to standing
    sm.update({"left_knee": 130.0}, {}, {}, timestamp=t)
    t += 0.2
    sm.update({"left_knee": 85.0}, {}, {}, timestamp=t)
    t += 0.2
    sm.update({"left_knee": 125.0}, {}, {}, timestamp=t)
    t += 0.2
    res1 = sm.update({"left_knee": 165.0}, {}, {}, timestamp=t)
    assert_equal("Rep 1 counted", res1.repetitions, 1)
    assert_true("is_rep_completed == True", res1.is_rep_completed)

    # Immediate jitter around standing threshold 50ms later (t + 0.05s < min_rep_interval_sec)
    t += 0.05
    sm.current_phase = "ascending"
    sm.reached_bottom = True
    res2 = sm.update({"left_knee": 165.0}, {}, {}, timestamp=t)
    # Temporal hysteresis must reject this duplicate
    assert_equal("Duplicate rep rejected by hysteresis", res2.repetitions, 1)

    print("Suite 5 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 6 — Missing & Low-Visibility Landmarks
# ---------------------------------------------------------------------------

def test_missing_landmarks():
    section("Suite 6 — Missing & Low-Visibility Landmarks")
    from app.exercises.squat import SquatStateMachine

    sm = SquatStateMachine()
    # Missing all knee angles (e.g. occluded / out of frame)
    res = sm.update({"left_knee": None, "right_knee": None}, {}, {}, timestamp=1.0)
    assert_false("valid is False when joints missing", res.valid)
    assert_equal("Reps remain 0 without crash", res.repetitions, 0)
    assert_equal("Phase retained safely", res.phase, "standing")

    print("Suite 6 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 7 — Posture / Candidate Classifier Heuristics
# ---------------------------------------------------------------------------

def test_posture_classifier():
    section("Suite 7 — Posture / Candidate Classifier Heuristics")
    from app.exercises.classifier import classify_candidate_posture

    # 1. Horizontal orientation (shoulders and hips on similar horizontal plane)
    horizontal_lms = {
        "left_shoulder": {"x": 0.2, "y": 0.5, "visibility": 0.9},
        "right_shoulder": {"x": 0.2, "y": 0.6, "visibility": 0.9},
        "left_hip": {"x": 0.7, "y": 0.52, "visibility": 0.9},
        "right_hip": {"x": 0.7, "y": 0.62, "visibility": 0.9},
    }
    candidate_push = classify_candidate_posture(horizontal_lms, {})
    assert_equal("Horizontal orientation -> push_up candidate", candidate_push, "push_up")

    # 2. Vertical standing orientation
    vertical_lms = {
        "left_shoulder": {"x": 0.45, "y": 0.2, "visibility": 0.9},
        "right_shoulder": {"x": 0.55, "y": 0.2, "visibility": 0.9},
        "left_hip": {"x": 0.45, "y": 0.55, "visibility": 0.9},
        "right_hip": {"x": 0.55, "y": 0.55, "visibility": 0.9},
    }
    # With bent knees (< 140 deg) -> candidate squat
    candidate_squat = classify_candidate_posture(vertical_lms, {"left_knee": 110.0, "right_knee": 110.0})
    assert_equal("Vertical with bent knees -> squat candidate", candidate_squat, "squat")

    # With curled elbows (< 110 deg) -> candidate bicep_curl
    candidate_curl = classify_candidate_posture(vertical_lms, {"left_elbow": 85.0})
    assert_equal("Vertical with curled arm -> bicep_curl candidate", candidate_curl, "bicep_curl")

    print("Suite 7 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 8 — ExerciseAnalysisManager Switching & Reset
# ---------------------------------------------------------------------------

def test_exercise_manager():
    section("Suite 8 — ExerciseAnalysisManager Switching & Reset")
    from app.exercises.manager import ExerciseAnalysisManager

    mgr = ExerciseAnalysisManager()

    # Default is unselected
    assert_equal("Default selected is None", mgr.selected_exercise, None)
    res_none = mgr.process_frame({"joint_angles": {"left_knee": 170.0}}, [], timestamp=1.0)
    assert_equal("No exercise selected -> returns None", res_none, None)

    # Select squat
    mgr.select_exercise("squat")
    assert_equal("Selected is squat", mgr.selected_exercise, "squat")

    res_squat = mgr.process_frame({"joint_angles": {"left_knee": 170.0}}, [], timestamp=1.0)
    assert_equal("Squat analysis returned", res_squat.exercise_name, "squat")
    assert_equal("Phase is standing", res_squat.phase, "standing")

    # Switch to bicep_curl
    mgr.select_exercise("bicep_curl")
    assert_equal("Switched to bicep_curl", mgr.selected_exercise, "bicep_curl")
    res_curl = mgr.process_frame({"joint_angles": {"left_elbow": 160.0}}, [], timestamp=1.0)
    assert_equal("Bicep curl analysis returned", res_curl.exercise_name, "bicep_curl")

    # Reset
    mgr.reset_exercise()
    assert_equal("Reset resets bicep_curl reps to 0", mgr.state_machines["bicep_curl"].reps, 0)

    print("Suite 8 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 9 — FrameProcessor with Exercise Integration
# ---------------------------------------------------------------------------

def _make_black_frame_b64() -> str:
    import cv2
    import numpy as np
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf.tobytes()).decode("ascii")


def test_frame_processor_exercise():
    section("Suite 9 — FrameProcessor with Exercise Integration")
    from app.cv.frame_processor import FrameProcessor

    fp = FrameProcessor()
    b64 = _make_black_frame_b64()

    # Black frame has no pose, so exercise should be None
    res = fp.process_frame(b64, exercise_name="squat")
    assert_equal("No pose detected -> exercise is None", res.exercise, None)

    print("Suite 9 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 10 — WebSocket /ws/pose with Exercise Selection & Rep Counting
# ---------------------------------------------------------------------------

def test_websocket_exercise():
    section("Suite 10 — WebSocket /ws/pose with Exercise Selection")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    with client.websocket_connect("/ws/pose") as ws:
        # 1. Select exercise command
        ws.send_text(json.dumps({"type": "select_exercise", "exercise": "squat"}))
        msg1 = ws.receive_json()
        assert_equal("Select exercise type", msg1.get("type"), "exercise_selected")
        assert_equal("Selected exercise name", msg1.get("exercise"), "squat")

        # 2. Reset exercise command
        ws.send_text(json.dumps({"type": "reset_exercise"}))
        msg2 = ws.receive_json()
        assert_equal("Reset exercise type", msg2.get("type"), "exercise_reset")

        # 3. Send frame payload containing exercise attribute
        b64 = _make_black_frame_b64()
        ws.send_text(json.dumps({"frame": b64, "exercise": "squat"}))
        msg3 = ws.receive_json()
        assert_true("Response contains exercise key", "exercise" in msg3)

    print("Suite 10 PASSED")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_all():
    suites = [
        ("1 — SquatStateMachine Full Cycle",     test_squat_state_machine),
        ("2 — Squat Form Cues & Valgus",         test_squat_form_cues),
        ("3 — BicepCurlStateMachine Full Cycle", test_bicep_curl_state_machine),
        ("4 — PushUpStateMachine Full Cycle",    test_push_up_state_machine),
        ("5 — Duplicate-Count Hysteresis",       test_duplicate_count_prevention),
        ("6 — Missing Landmarks Handling",       test_missing_landmarks),
        ("7 — Posture Classifier Heuristics",    test_posture_classifier),
        ("8 — ExerciseManager Switching & Reset",test_exercise_manager),
        ("9 — FrameProcessor Exercise",          test_frame_processor_exercise),
        ("10 — WebSocket Exercise",              test_websocket_exercise),
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
    print(f"  STAGE 5 TEST RESULTS: {passed_suites}/{len(suites)} suites passed")
    if failed_names:
        print(f"  FAILED: {', '.join(failed_names)}")
    else:
        print("  ALL STAGE 5 TESTS PASSED")
    print(f"{'='*60}\n")

    if failed_suites > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
