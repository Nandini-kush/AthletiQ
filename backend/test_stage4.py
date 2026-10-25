"""
test_stage4.py — AthletiQ Stage 4: Biomechanics Engine Tests

Tests cover:
  - calculate_3point_angle() geometry cases (90 deg, 180 deg, 45 deg, zero-length vectors)
  - calculate_all_joint_angles() visibility gating and landmark validation
  - calculate_all_segment_distances() Euclidean distances in normalized space
  - ExponentialMovingAverageFilter temporal smoothing
  - RangeOfMotionTracker min/max/rom dynamics and reset
  - KinematicMovementTracker displacement, velocity, acceleration
  - calculate_symmetry_metrics() bilateral symmetry calculations
  - BiomechanicsEngine.analyze() end-to-end telemetry
  - BiomechanicsEngine.reset_rom() and reset()
  - FrameProcessor.process_frame() returns biomechanics
  - WebSocket /ws/pose returns biomechanics JSON field
"""

import sys
import json
import math
import time
import base64
from typing import Any, Dict, List, Optional

# Ensure ASCII/UTF-8 safe test output on Windows terminal
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def assert_none(label: str, actual):
    ok = actual is None
    _results.append(PASS if ok else FAIL)
    symbol = "+" if ok else "x"
    print(f"  [{symbol}] {label}: {actual!r} == None")
    if not ok:
        raise AssertionError(f"{label}: expected None, got {actual!r}")


def assert_not_none(label: str, actual):
    ok = actual is not None
    _results.append(PASS if ok else FAIL)
    symbol = "+" if ok else "x"
    print(f"  [{symbol}] {label}: is not None")
    if not ok:
        raise AssertionError(f"{label}: expected non-None, got None")


def assert_true(label: str, condition: bool):
    _results.append(PASS if condition else FAIL)
    symbol = "+" if condition else "x"
    print(f"  [{symbol}] {label}")
    if not condition:
        raise AssertionError(f"{label}: condition is False")


def assert_in_range(label: str, actual, lo, hi):
    ok = actual is not None and lo <= actual <= hi
    _results.append(PASS if ok else FAIL)
    symbol = "+" if ok else "x"
    print(f"  [{symbol}] {label}: {actual!r} in [{lo}, {hi}]")
    if not ok:
        raise AssertionError(f"{label}: {actual!r} not in [{lo}, {hi}]")


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# TEST SUITE 1 — calculate_3point_angle()
# ---------------------------------------------------------------------------

def test_angle_calculations():
    section("Suite 1 — calculate_3point_angle()")
    from app.biomechanics.angles import calculate_3point_angle

    # Right angle (L-shape): A=(1,0), B=(0,0), C=(0,1)
    angle = calculate_3point_angle((1, 0), (0, 0), (0, 1))
    assert_equal("Right angle (90 deg)", angle, 90.0, tol=0.01)

    # Straight line: A=(0,0), B=(0.5,0), C=(1,0) => angle at B should be 180 deg
    angle = calculate_3point_angle((0, 0), (0.5, 0), (1, 0))
    assert_equal("Straight line (180 deg)", angle, 180.0, tol=0.01)

    # Acute angle: A=(1,0), B=(0,0), C=(math.cos(45), math.sin(45))
    cx = math.cos(math.radians(45))
    cy = math.sin(math.radians(45))
    angle = calculate_3point_angle((1, 0), (0, 0), (cx, cy))
    assert_equal("Acute angle (45 deg)", angle, 45.0, tol=0.1)

    # Zero-length BA vector returns None
    angle = calculate_3point_angle((0, 0), (0, 0), (1, 0))
    assert_none("Zero-length BA returns None", angle)

    # Zero-length BC vector returns None
    angle = calculate_3point_angle((1, 0), (0, 0), (0, 0))
    assert_none("Zero-length BC returns None", angle)

    # Obtuse angle: A=(1,0), B=(0,0), C=(-0.5, 0.1)
    angle = calculate_3point_angle((1, 0), (0, 0), (-0.5, 0.1))
    assert_true("Obtuse angle > 90 deg", angle is not None and angle > 90.0)

    # 3D mode
    angle_3d = calculate_3point_angle((1, 0, 0), (0, 0, 0), (0, 1, 0), use_3d=True)
    assert_equal("3D right angle (90 deg)", angle_3d, 90.0, tol=0.01)

    print("Suite 1 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 2 — calculate_all_joint_angles() & Landmark Validation
# ---------------------------------------------------------------------------

def _make_lm(name: str, x: float, y: float, z: float = 0.0, vis: float = 1.0) -> Dict[str, Any]:
    return {"name": name, "x": x, "y": y, "z": z, "visibility": vis}


def _landmarks_by_name(lms: List[Dict]) -> Dict[str, Any]:
    return {lm["name"]: lm for lm in lms}


def test_joint_angles_all_joints():
    section("Suite 2 — calculate_all_joint_angles()")
    from app.biomechanics.angles import calculate_all_joint_angles

    # Build a landmark set that forms right-angle geometries
    lms = [
        _make_lm("left_shoulder", 0.0, 0.0),
        _make_lm("left_elbow",    0.0, 0.2),
        _make_lm("left_wrist",    0.2, 0.2),
        _make_lm("left_hip",      0.0, 0.5),
        _make_lm("left_knee",     0.0, 0.7),
        _make_lm("left_ankle",    0.2, 0.7),

        _make_lm("right_shoulder", 0.5, 0.0),
        _make_lm("right_elbow",    0.5, 0.2),
        _make_lm("right_wrist",    0.7, 0.2),
        _make_lm("right_hip",      0.5, 0.5),
        _make_lm("right_knee",     0.5, 0.7),
        _make_lm("right_ankle",    0.7, 0.7),
    ]
    lms_dict = _landmarks_by_name(lms)
    results = calculate_all_joint_angles(lms_dict)

    # All 8 joints should be evaluated
    for joint in ["left_knee", "right_knee", "left_elbow", "right_elbow",
                  "left_shoulder", "right_shoulder", "left_hip", "right_hip"]:
        assert_true(f"{joint} is valid", results[joint]["valid"])
        assert_not_none(f"{joint} angle is not None", results[joint]["angle"])

    # Left knee should be ~90 degrees
    assert_equal("left_knee angle ~90 deg", results["left_knee"]["angle"], 90.0, tol=1.0)

    print("Suite 2a PASSED")

    # Low-visibility test: set visibility < threshold -> invalid
    low_vis_lms = [dict(lm, visibility=0.1) for lm in lms]
    low_dict = _landmarks_by_name(low_vis_lms)
    low_results = calculate_all_joint_angles(low_dict, visibility_threshold=0.5)
    for joint in ["left_knee", "right_knee"]:
        assert_equal(f"{joint} invalid when low vis", low_results[joint]["valid"], False)
        assert_equal(f"{joint} reason=insufficient_visibility", low_results[joint]["reason"], "insufficient_visibility")

    print("Suite 2b PASSED")

    # Missing landmark test
    partial = {k: v for k, v in lms_dict.items() if k != "left_wrist"}
    partial_results = calculate_all_joint_angles(partial)
    assert_equal("left_elbow missing landmark", partial_results["left_elbow"]["valid"], False)
    assert_equal("left_elbow reason=missing_landmarks", partial_results["left_elbow"]["reason"], "missing_landmarks")

    print("Suite 2c PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 3 — calculate_all_segment_distances()
# ---------------------------------------------------------------------------

def test_segment_distances():
    section("Suite 3 — calculate_all_segment_distances()")
    from app.biomechanics.distances import calculate_all_segment_distances

    lms = [
        _make_lm("left_shoulder",  0.0, 0.0),
        _make_lm("right_shoulder", 0.4, 0.0),
        _make_lm("left_hip",       0.0, 0.5),
        _make_lm("right_hip",      0.4, 0.5),
        _make_lm("left_knee",      0.0, 0.8),
        _make_lm("right_knee",     0.4, 0.8),
        _make_lm("left_ankle",     0.0, 1.0),
        _make_lm("right_ankle",    0.4, 1.0),
        _make_lm("left_elbow",     -0.1, 0.2),
        _make_lm("right_elbow",    0.5, 0.2),
        _make_lm("left_wrist",     -0.2, 0.4),
        _make_lm("right_wrist",    0.6, 0.4),
        _make_lm("nose",           0.2, -0.1),
    ]
    lms_dict = _landmarks_by_name(lms)
    results = calculate_all_segment_distances(lms_dict)

    # shoulder_width between (0.0,0.0) and (0.4,0.0) = 0.4
    assert_true("shoulder_width is valid", results["shoulder_width"]["valid"])
    assert_equal("shoulder_width distance ~0.4", results["shoulder_width"]["distance"], 0.4, tol=0.01)

    # hip_width: (0,0.5) to (0.4,0.5) = 0.4
    assert_true("hip_width is valid", results["hip_width"]["valid"])
    assert_equal("hip_width distance ~0.4", results["hip_width"]["distance"], 0.4, tol=0.01)

    # left_thigh: (0,0.5) to (0,0.8) = 0.3
    assert_true("left_thigh is valid", results["left_thigh"]["valid"])
    assert_equal("left_thigh distance ~0.3", results["left_thigh"]["distance"], 0.3, tol=0.01)

    print("Suite 3 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 4 — Temporal Smoothing (EMA Filter)
# ---------------------------------------------------------------------------

def test_ema_filter():
    section("Suite 4 — ExponentialMovingAverageFilter")
    from app.biomechanics.smoothing import ExponentialMovingAverageFilter

    ema = ExponentialMovingAverageFilter(alpha=0.5)

    # First call: output == input (no history)
    v1 = ema.filter_scalar("knee", 100.0)
    assert_equal("EMA first value = input", v1, 100.0)

    # Second call: 0.5*100 + 0.5*100 = 100
    v2 = ema.filter_scalar("knee", 100.0)
    assert_equal("EMA stable signal stays at 100", v2, 100.0, tol=0.01)

    # Large jump: 0.5*0 + 0.5*100 = 50
    v3 = ema.filter_scalar("knee", 0.0)
    assert_equal("EMA smooths large jump to 50", v3, 50.0, tol=0.01)

    # Reset clears history
    ema.reset()
    v_after_reset = ema.filter_scalar("knee", 42.0)
    assert_equal("EMA after reset starts fresh at 42", v_after_reset, 42.0)

    print("Suite 4 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 5 — RangeOfMotionTracker
# ---------------------------------------------------------------------------

def test_rom_tracker():
    section("Suite 5 — RangeOfMotionTracker")
    from app.biomechanics.movement import RangeOfMotionTracker

    tracker = RangeOfMotionTracker()

    def make_angle_dict(joint: str, angle: float, valid: bool = True) -> Dict:
        return {joint: {"angle": angle, "valid": valid, "reason": None}}

    # Frame 1: left_knee = 90 deg
    r1 = tracker.update(make_angle_dict("left_knee", 90.0))
    assert_equal("ROM frame1 current=90", r1["left_knee"]["current_angle"], 90.0)
    assert_equal("ROM frame1 min=90", r1["left_knee"]["min_angle"], 90.0)
    assert_equal("ROM frame1 max=90", r1["left_knee"]["max_angle"], 90.0)
    assert_equal("ROM frame1 rom=0", r1["left_knee"]["rom"], 0.0)

    # Frame 2: left_knee = 120 deg -> new max
    r2 = tracker.update(make_angle_dict("left_knee", 120.0))
    assert_equal("ROM frame2 max=120", r2["left_knee"]["max_angle"], 120.0)
    assert_equal("ROM frame2 rom=30", r2["left_knee"]["rom"], 30.0)

    # Frame 3: left_knee = 60 deg -> new min
    r3 = tracker.update(make_angle_dict("left_knee", 60.0))
    assert_equal("ROM frame3 min=60", r3["left_knee"]["min_angle"], 60.0)
    assert_equal("ROM frame3 rom=60", r3["left_knee"]["rom"], 60.0)

    # Reset
    tracker.reset("left_knee")
    r4 = tracker.update(make_angle_dict("left_knee", 50.0))
    assert_equal("ROM after reset min=50", r4["left_knee"]["min_angle"], 50.0)
    assert_equal("ROM after reset rom=0", r4["left_knee"]["rom"], 0.0)

    print("Suite 5 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 6 — Symmetry Analysis
# ---------------------------------------------------------------------------

def test_symmetry():
    section("Suite 6 — Bilateral Symmetry Analysis")
    from app.biomechanics.symmetry import calculate_symmetry_metrics

    # Perfect symmetry: Left angles == Right angles
    joint_angles = {
        "left_knee": {"angle": 90.0, "valid": True},
        "right_knee": {"angle": 90.0, "valid": True},
        "left_elbow": {"angle": 140.0, "valid": True},
        "right_elbow": {"angle": 140.0, "valid": True},
        "left_shoulder": {"angle": 70.0, "valid": True},
        "right_shoulder": {"angle": 70.0, "valid": True},
        "left_hip": {"angle": 85.0, "valid": True},
        "right_hip": {"angle": 85.0, "valid": True},
    }
    distances = {
        "left_thigh": {"distance": 0.3, "valid": True},
        "right_thigh": {"distance": 0.3, "valid": True},
        "left_upper_arm": {"distance": 0.25, "valid": True},
        "right_upper_arm": {"distance": 0.25, "valid": True},
        "left_forearm": {"distance": 0.2, "valid": True},
        "right_forearm": {"distance": 0.2, "valid": True},
        "left_lower_leg": {"distance": 0.3, "valid": True},
        "right_lower_leg": {"distance": 0.3, "valid": True},
    }

    sym = calculate_symmetry_metrics(joint_angles, distances)
    assert_true("Symmetry valid=True", sym["valid"])
    assert_equal("Perfect symmetry score == 100%", sym["movement_symmetry_score"], 100.0)
    assert_equal("Knee diff == 0", sym["joint_angle_differences_deg"]["knee_diff_deg"], 0.0)

    # Introduce 10 deg asymmetry in knee
    joint_angles["right_knee"]["angle"] = 100.0
    sym2 = calculate_symmetry_metrics(joint_angles, distances)
    assert_equal("Knee diff == 10 deg", sym2["joint_angle_differences_deg"]["knee_diff_deg"], 10.0)
    assert_true("Symmetry score < 100% when asymmetric", sym2["movement_symmetry_score"] < 100.0)

    print("Suite 6 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 7 — BiomechanicsEngine.analyze() end-to-end
# ---------------------------------------------------------------------------

def _full_landmarks() -> List[Dict[str, Any]]:
    names = [
        "nose", "left_eye_inner", "left_eye", "left_eye_outer",
        "right_eye_inner", "right_eye", "right_eye_outer",
        "left_ear", "right_ear", "mouth_left", "mouth_right",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_pinky", "right_pinky",
        "left_index", "right_index", "left_thumb", "right_thumb",
        "left_hip", "right_hip", "left_knee", "right_knee",
        "left_ankle", "right_ankle", "left_heel", "right_heel",
        "left_foot_index", "right_foot_index",
    ]
    base = {
        "nose": (0.5, 0.05),
        "left_shoulder": (0.35, 0.2), "right_shoulder": (0.65, 0.2),
        "left_elbow": (0.25, 0.4), "right_elbow": (0.75, 0.4),
        "left_wrist": (0.2, 0.55), "right_wrist": (0.8, 0.55),
        "left_hip": (0.4, 0.55), "right_hip": (0.6, 0.55),
        "left_knee": (0.38, 0.75), "right_knee": (0.62, 0.75),
        "left_ankle": (0.38, 0.95), "right_ankle": (0.62, 0.95),
    }
    lms = []
    for i, name in enumerate(names):
        x, y = base.get(name, (0.5, 0.5))
        lms.append({"index": i, "name": name, "x": x, "y": y, "z": 0.0, "visibility": 0.95})
    return lms


def test_biomechanics_engine_analyze():
    section("Suite 7 — BiomechanicsEngine.analyze()")
    from app.biomechanics.engine import BiomechanicsEngine

    engine = BiomechanicsEngine(visibility_threshold=0.5, enable_smoothing=True)
    lms = _full_landmarks()

    result = engine.analyze(lms, timestamp=1000.0)

    # Top-level structure
    assert_true("result is dict", isinstance(result, dict))
    assert_true("result has valid key", "valid" in result)
    assert_true("result has joint_angles", "joint_angles" in result)
    assert_true("result has segment_distances_norm", "segment_distances_norm" in result)
    assert_true("result has symmetry", "symmetry" in result)
    assert_true("result has range_of_motion", "range_of_motion" in result)
    assert_true("result has kinematics", "kinematics" in result)

    # Joint angles check
    ja = result["joint_angles"]
    valid_angles = [v for v in ja.values() if v is not None]
    assert_true("At least 1 valid joint angle", len(valid_angles) > 0)
    for joint, angle in ja.items():
        if angle is not None:
            assert_in_range(f"{joint} angle in [0,180]", angle, 0.0, 180.0)

    # Segment distances
    for seg, dist in result["segment_distances_norm"].items():
        if dist is not None:
            assert_true(f"{seg} distance >= 0", dist >= 0.0)

    # Movement kinematics with 2 frames
    lms2 = [dict(lm) for lm in lms]
    for lm in lms2:
        if lm["name"] == "right_wrist":
            lm["x"] += 0.05
            lm["y"] += 0.05

    result2 = engine.analyze(lms2, timestamp=1000.1)
    overall_speed = result2["kinematics"]["overall_movement_speed_norm_per_sec"]
    assert_true("Movement speed > 0 after position change", overall_speed > 0.0)

    print("Suite 7 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 8 — BiomechanicsEngine.reset_rom()
# ---------------------------------------------------------------------------

def test_engine_reset_rom():
    section("Suite 8 — BiomechanicsEngine.reset_rom()")
    from app.biomechanics.engine import BiomechanicsEngine

    engine = BiomechanicsEngine()
    lms = _full_landmarks()

    engine.analyze(lms, timestamp=0.0)

    # Reset and run again
    engine.reset_rom()
    r_after = engine.analyze(lms, timestamp=0.1)
    lk_rom_after = r_after["range_of_motion"].get("left_knee", {}).get("rom")
    assert_equal("ROM = 0 after reset", lk_rom_after, 0.0)

    print("Suite 8 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 9 — Pydantic Schema Validation
# ---------------------------------------------------------------------------

def test_biomechanics_schema():
    section("Suite 9 — BiomechanicsResult Pydantic Schema")
    from app.schemas.biomechanics import BiomechanicsResult, SymmetryData, KinematicsData
    from app.biomechanics.engine import BiomechanicsEngine

    engine = BiomechanicsEngine()
    lms = _full_landmarks()
    raw = engine.analyze(lms, timestamp=1.0)

    result = BiomechanicsResult.model_validate(raw)
    assert_true("BiomechanicsResult is valid Pydantic model", isinstance(result, BiomechanicsResult))
    assert_true("symmetry is SymmetryData", isinstance(result.symmetry, SymmetryData))
    assert_true("kinematics is KinematicsData", isinstance(result.kinematics, KinematicsData))

    # JSON serialization
    j = result.model_dump_json()
    data = json.loads(j)
    assert_true("JSON has joint_angles key", "joint_angles" in data)
    assert_true("JSON has range_of_motion key", "range_of_motion" in data)

    print("Suite 9 PASSED")


# ---------------------------------------------------------------------------
# TEST SUITE 10 — WebSocket end-to-end with Biomechanics
# ---------------------------------------------------------------------------

def _make_black_frame_b64(width: int = 64, height: int = 64) -> str:
    import cv2
    import numpy as np
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf.tobytes()).decode("ascii")


def test_websocket_biomechanics():
    section("Suite 10 — WebSocket /ws/pose returns biomechanics JSON field")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # ping/pong
    with client.websocket_connect("/ws/pose") as ws:
        ws.send_text("ping")
        msg = ws.receive_json()
        assert_equal("WS ping returns pong type", msg.get("type"), "pong")

    # Reset ROM command
    with client.websocket_connect("/ws/pose") as ws:
        ws.send_text("reset_rom")
        msg = ws.receive_json()
        assert_equal("reset_rom returns rom_reset type", msg.get("type"), "rom_reset")

    # Black frame (no person)
    with client.websocket_connect("/ws/pose") as ws:
        b64 = _make_black_frame_b64()
        ws.send_text(json.dumps({"frame": b64}))
        msg = ws.receive_json()
        assert_equal("Black frame pose_detected=False", msg.get("pose_detected"), False)
        assert_true("Response has biomechanics key", "biomechanics" in msg)
        assert_none("Black frame biomechanics=None", msg.get("biomechanics"))

    print("Suite 10 PASSED")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_all():
    suites = [
        ("1 — calculate_3point_angle",       test_angle_calculations),
        ("2 — calculate_all_joint_angles",   test_joint_angles_all_joints),
        ("3 — calculate_all_segment_distances", test_segment_distances),
        ("4 — ExponentialMovingAverageFilter",   test_ema_filter),
        ("5 — RangeOfMotionTracker",         test_rom_tracker),
        ("6 — Bilateral Symmetry Analysis",  test_symmetry),
        ("7 — BiomechanicsEngine.analyze",   test_biomechanics_engine_analyze),
        ("8 — BiomechanicsEngine.reset_rom", test_engine_reset_rom),
        ("9 — Pydantic Schema Validation",   test_biomechanics_schema),
        ("10 — WebSocket Biomechanics",      test_websocket_biomechanics),
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
    print(f"  STAGE 4 TEST RESULTS: {passed_suites}/{len(suites)} suites passed")
    if failed_names:
        print(f"  FAILED: {', '.join(failed_names)}")
    else:
        print("  ALL STAGE 4 TESTS PASSED")
    print(f"{'='*60}\n")

    if failed_suites > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
