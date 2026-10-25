"""
AthletiQ - Stage 3 Comprehensive Verification Test Suite
Tests:
1. MediaPipe, OpenCV, NumPy library environment and versions
2. PoseEstimator service initialization & model asset existence
3. FrameProcessor image decoding (base64 string, data URI, raw bytes)
4. Frame downscaling optimization
5. Pose estimation on empty/blank frame (handles no-pose gracefully)
6. Landmark mapping, names, and quality threshold logic
7. FrameProcessor skeleton drawing utility
8. Real-time WebSocket (/ws/pose) connection, ping/pong, frame streaming, and graceful disconnect
9. Verification that Stage 1 and Stage 2 routes remain fully functional and intact
"""

import base64
import json
import numpy as np
import cv2
from fastapi.testclient import TestClient
from app.main import app
from app.cv.pose_estimator import PoseEstimator
from app.cv.frame_processor import FrameProcessor
from app.cv.landmarks import (
    POSE_LANDMARKS,
    KEY_BIOMECHANICAL_LANDMARKS,
    POSE_CONNECTIONS,
    is_valid_pose,
)
from app.schemas.pose import LandmarkPoint, PoseDetectionResult

client = TestClient(app)


def test_cv_environment():
    print("Testing CV Environment & Libraries...")
    import mediapipe as mp
    import cv2
    import numpy as np

    print(f"  MediaPipe version: {mp.__version__}")
    print(f"  OpenCV version: {cv2.__version__}")
    print(f"  NumPy version: {np.__version__}")
    assert hasattr(mp, "tasks"), "MediaPipe Tasks API is missing"
    assert hasattr(mp.tasks, "vision"), "MediaPipe Tasks Vision is missing"
    print("  [PASS] CV environment verified")


def test_pose_estimator_service():
    print("\nTesting PoseEstimator Service...")
    estimator = PoseEstimator()
    assert estimator.model_path.exists(), f"Model file not found at {estimator.model_path}"
    assert estimator.model_path.stat().st_size > 1_000_000, "Model file size seems too small"
    print(f"  Model verified at: {estimator.model_path} ({estimator.model_path.stat().st_size} bytes)")

    # Test detection on empty black frame
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = estimator.detect(blank_frame)
    assert result is not None, "Detection returned None instead of PoseLandmarkerResult"
    assert len(result.pose_landmarks) == 0, "Blank frame should not detect any person"
    print("  [PASS] PoseEstimator blank frame handling verified (0 poses detected)")


def test_frame_processor_service():
    print("\nTesting FrameProcessor Service...")
    processor = FrameProcessor(max_width=640)

    # 1. Test image decoding
    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", test_img)
    b64_str = base64.b64encode(encoded.tobytes()).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{b64_str}"

    decoded_from_raw = processor.decode_frame(b64_str)
    assert decoded_from_raw is not None
    assert decoded_from_raw.shape == (100, 100, 3)

    decoded_from_uri = processor.decode_frame(data_uri)
    assert decoded_from_uri is not None
    assert decoded_from_uri.shape == (100, 100, 3)

    decoded_from_bytes = processor.decode_frame(encoded.tobytes())
    assert decoded_from_bytes is not None
    print("  [PASS] Frame decoding (base64 string, Data URI, raw bytes) verified")

    # 2. Test frame resizing
    large_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    resized = processor.resize_frame_if_needed(large_frame)
    assert resized.shape[1] == 640, f"Expected width 640, got {resized.shape[1]}"
    assert resized.shape[0] == 360, f"Expected height 360, got {resized.shape[0]}"
    print("  [PASS] Frame resizing for real-time latency optimization verified")

    # 3. Test process_frame on blank frame
    pose_res = processor.process_frame(data_uri)
    assert isinstance(pose_res, PoseDetectionResult)
    assert pose_res.pose_detected is False
    assert len(pose_res.landmarks) == 0
    assert pose_res.inference_time_ms >= 0.0
    print("  [PASS] Blank frame processed returning valid PoseDetectionResult (pose_detected=False)")

    # 4. Test draw_skeleton helper
    dummy_landmarks = [
        LandmarkPoint(index=i, name=POSE_LANDMARKS[i], x=0.5, y=0.5, z=0.0, visibility=0.9)
        for i in range(33)
    ]
    annotated = processor.draw_skeleton(test_img, dummy_landmarks)
    assert annotated.shape == test_img.shape
    print("  [PASS] Skeleton drawing utility verified")


def test_landmarks_mapping():
    print("\nTesting Landmark Mapping & Quality Thresholds...")
    assert len(POSE_LANDMARKS) == 33, f"Expected 33 landmarks, got {len(POSE_LANDMARKS)}"
    assert POSE_LANDMARKS[0] == "nose"
    assert POSE_LANDMARKS[11] == "left_shoulder"
    assert POSE_LANDMARKS[12] == "right_shoulder"
    assert POSE_LANDMARKS[23] == "left_hip"
    assert POSE_LANDMARKS[24] == "right_hip"
    assert POSE_LANDMARKS[27] == "left_ankle"
    assert POSE_LANDMARKS[28] == "right_ankle"

    assert len(KEY_BIOMECHANICAL_LANDMARKS) == 12
    assert len(POSE_CONNECTIONS) > 20

    # Test threshold quality helper
    empty_list = []
    assert is_valid_pose(empty_list) is False

    low_vis_list = [
        {"name": POSE_LANDMARKS[i], "visibility": 0.1} for i in range(33)
    ]
    assert is_valid_pose(low_vis_list) is False

    high_vis_list = [
        {"name": POSE_LANDMARKS[i], "visibility": 0.8} for i in range(33)
    ]
    assert is_valid_pose(high_vis_list) is True
    print("  [PASS] Landmark definitions & is_valid_pose quality threshold verified")


def test_websocket_pose_stream():
    print("\nTesting Real-Time WebSocket Endpoint (/ws/pose)...")

    # Encode a test blank frame
    test_img = np.zeros((240, 320, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", test_img)
    b64_str = base64.b64encode(encoded.tobytes()).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{b64_str}"

    with client.websocket_connect("/ws/pose") as websocket:
        # 1. Ping / Pong
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert json.loads(data) == {"type": "pong"}
        print("  [PASS] WebSocket ping/pong verified")

        # 2. Send frame payload as raw data URI
        websocket.send_text(data_uri)
        response_text = websocket.receive_text()
        resp_json = json.loads(response_text)
        assert "pose_detected" in resp_json
        assert "landmarks" in resp_json
        assert "inference_time_ms" in resp_json
        print("  [PASS] WebSocket frame processing & structured response verified")

        # 3. Send JSON wrapped frame: {"frame": "<data_uri>"}
        websocket.send_text(json.dumps({"frame": data_uri}))
        response_text2 = websocket.receive_text()
        resp_json2 = json.loads(response_text2)
        assert resp_json2["pose_detected"] is False
        print("  [PASS] WebSocket JSON-wrapped frame payload verified")

        # 4. Send malformed/empty payload (should return error payload without crashing socket)
        websocket.send_text("")
        malformed_resp = json.loads(websocket.receive_text())
        assert malformed_resp["pose_detected"] is False
        print("  [PASS] WebSocket resilient error handling verified")


def test_preserve_stage1_and_stage2():
    print("\nTesting Preservation of Stage 1 & Stage 2 Services...")
    # 1. Health check
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("  [PASS] GET /api/health functional")

    # 2. Auth register & login
    unique_email = f"cv_test_{np.random.randint(10000, 99999)}@athletiq.com"
    reg_resp = client.post("/api/auth/register", json={
        "full_name": "CV Athlete",
        "email": unique_email,
        "password": "Password123!"
    })
    assert reg_resp.status_code == 201

    login_resp = client.post("/api/auth/login", json={
        "email": unique_email,
        "password": "Password123!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 3. Authenticated profile check
    me_resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == unique_email
    print("  [PASS] Stage 2 Auth & Protected User routes functional and intact")


if __name__ == "__main__":
    test_cv_environment()
    test_pose_estimator_service()
    test_frame_processor_service()
    test_landmarks_mapping()
    test_websocket_pose_stream()
    test_preserve_stage1_and_stage2()
    print("\n==========================================")
    print("ALL STAGE 3 TESTS PASSED SUCCESSFULLY!")
    print("==========================================\n")
