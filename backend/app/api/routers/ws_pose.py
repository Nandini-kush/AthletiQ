"""
WebSocket Route for Real-Time Pose Estimation
Provides high-frequency bidirectional streaming for webcam frame analysis.
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.cv.frame_processor import FrameProcessor

router = APIRouter()

# Shared FrameProcessor instance
processor = FrameProcessor()


@router.websocket("/pose")
async def websocket_pose(websocket: WebSocket):
    """
    WebSocket endpoint for real-time video frame pose analysis.
    Accepts:
      - JSON string: {"frame": "<base64_data_uri_or_string>"}
      - Raw base64 string
      - Raw binary image bytes
    Returns:
      - JSON PoseDetectionResult
    """
    await websocket.accept()

    active_exercise = None

    try:
        while True:
            # Receive either text or bytes
            message = await websocket.receive()
            
            # Check for disconnect frame
            if message.get("type") == "websocket.disconnect":
                break

            image_data = None
            if "text" in message and message["text"]:
                text_content = message["text"].strip()
                if text_content == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue

                if text_content == "reset_rom":
                    processor.biomechanics_engine.reset_rom()
                    await websocket.send_text(json.dumps({"type": "rom_reset", "message": "Range-of-motion tracking reset."}))
                    continue

                if text_content == "reset_exercise":
                    processor.exercise_manager.reset_exercise(active_exercise)
                    processor.form_analyzer.reset()
                    await websocket.send_text(json.dumps({"type": "exercise_reset", "message": "Exercise repetitions and state reset."}))
                    continue

                if text_content.startswith("{"):
                    try:
                        parsed = json.loads(text_content)
                        msg_type = parsed.get("type")

                        if msg_type == "select_exercise":
                            active_exercise = parsed.get("exercise")
                            processor.exercise_manager.select_exercise(active_exercise)
                            processor.form_analyzer.reset()
                            await websocket.send_text(json.dumps({
                                "type": "exercise_selected",
                                "exercise": active_exercise,
                                "message": f"Selected exercise: {active_exercise or 'None'}"
                            }))
                            continue

                        if msg_type == "reset_exercise":
                            processor.exercise_manager.reset_exercise(active_exercise)
                            processor.form_analyzer.reset()
                            await websocket.send_text(json.dumps({"type": "exercise_reset", "message": "Exercise repetitions and state reset."}))
                            continue

                        image_data = parsed.get("frame") or parsed.get("image")
                        if "exercise" in parsed:
                            active_exercise = parsed["exercise"]
                    except json.JSONDecodeError:
                        image_data = text_content
                else:
                    image_data = text_content

            elif "bytes" in message and message["bytes"]:
                image_data = message["bytes"]

            if not image_data:
                await websocket.send_text(
                    json.dumps({
                        "pose_detected": False,
                        "landmarks": [],
                        "message": "Empty or unrecognized frame payload.",
                    })
                )
                continue

            # Process the frame
            result = processor.process_frame(image_data, exercise_name=active_exercise)

            # Send back JSON result
            await websocket.send_text(result.model_dump_json())

    except WebSocketDisconnect:
        # Normal client disconnection (user left page / closed browser)
        pass
    except Exception as e:
        # Catch any unexpected socket error and attempt graceful close
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
