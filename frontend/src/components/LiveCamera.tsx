import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Camera, CameraOff, RefreshCw, AlertCircle, Wifi, WifiOff } from 'lucide-react';
import { Button } from './Button';

// MediaPipe 33 Landmark Connections for Canvas Skeleton Drawing
const SKELETON_CONNECTIONS: [number, number][] = [
  // Face / Head
  [0, 1], [1, 2], [2, 3], [3, 7],
  [0, 4], [4, 5], [5, 6], [6, 8],
  [9, 10],
  // Torso
  [11, 12], // Shoulders
  [11, 23], // Left shoulder to hip
  [12, 24], // Right shoulder to hip
  [23, 24], // Hips
  // Left Arm
  [11, 13], // Shoulder to Elbow
  [13, 15], // Elbow to Wrist
  [15, 17], [15, 19], [15, 21], [17, 19],
  // Right Arm
  [12, 14], // Shoulder to Elbow
  [14, 16], // Elbow to Wrist
  [16, 18], [16, 20], [16, 22], [18, 20],
  // Left Leg
  [23, 25], // Hip to Knee
  [25, 27], // Knee to Ankle
  [27, 29], [27, 31], [29, 31],
  // Right Leg
  [24, 26], // Hip to Knee
  [26, 28], // Knee to Ankle
  [28, 30], [28, 32], [30, 32]
];

// Major joints to highlight with distinct colors
const KEY_JOINT_INDICES = new Set([
  11, 12, // Shoulders
  13, 14, // Elbows
  15, 16, // Wrists
  23, 24, // Hips
  25, 26, // Knees
  27, 28  // Ankles
]);

export interface LandmarkPoint {
  index: number;
  name: string;
  x: number;
  y: number;
  z: number;
  visibility: number;
}

export interface JointAngleDetail {
  angle: number | null;
  valid: boolean;
  reason?: string | null;
}

export interface RangeOfMotionItem {
  current_angle: number | null;
  min_angle: number | null;
  max_angle: number | null;
  rom: number | null;
}

export interface SymmetryData {
  joint_angle_differences_deg: Record<string, number | null>;
  segment_distance_differences_norm: Record<string, number | null>;
  movement_symmetry_score: number | null;
  valid: boolean;
}

export interface KinematicsPointData {
  displacement_norm: number;
  speed_norm_per_sec: number;
  acceleration_norm_per_sec2: number;
}

export interface KinematicsData {
  overall_movement_speed_norm_per_sec: number;
  landmarks_kinematics: Record<string, KinematicsPointData>;
}

export interface BiomechanicsResult {
  timestamp: number;
  valid: boolean;
  joint_angles: Record<string, number | null>;
  joint_angles_detailed: Record<string, JointAngleDetail>;
  segment_distances_norm: Record<string, number | null>;
  symmetry: SymmetryData;
  range_of_motion: Record<string, RangeOfMotionItem>;
  kinematics: KinematicsData;
}

export interface ExercisePhaseInfo {
  exercise_name: string;
  phase: string;
  repetitions: number;
  is_rep_completed: boolean;
  form_cues: string[];
  primary_metric_name: string;
  primary_metric_value: number | null;
  phase_progress_pct: number;
  candidate_detected?: string | null;
  valid: boolean;
}

export interface FormFindingMeasurement {
  name: string;
  value: number | null;
  unit: string;
}

export interface FormFinding {
  code: string;
  severity: 'info' | 'warning' | 'unavailable' | string;
  message: string;
  recommendation: string;
  measurement?: FormFindingMeasurement | null;
}

export interface FormAnalysisResult {
  exercise: string | null;
  analysis_available: boolean;
  form_status: 'good' | 'needs_attention' | 'unavailable' | string;
  findings: FormFinding[];
  limitations: string[];
}

export interface PoseDetectionResult {
  type?: string;
  pose_detected: boolean;
  confidence: number;
  landmarks: LandmarkPoint[];
  key_landmarks: Record<string, { x: number; y: number; z: number; visibility: number }>;
  biomechanics?: BiomechanicsResult | null;
  exercise?: ExercisePhaseInfo | null;
  form_feedback?: FormAnalysisResult | null;
  inference_time_ms: number;
  message?: string;
}

interface LiveCameraProps {
  onPoseResult?: (result: PoseDetectionResult) => void;
  targetFps?: number;
  resetRomTrigger?: number;
  selectedExercise?: string | null;
  resetExerciseTrigger?: number;
}

export const LiveCamera: React.FC<LiveCameraProps> = ({
  onPoseResult,
  targetFps = 15,
  resetRomTrigger,
  selectedExercise,
  resetExerciseTrigger,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [showSkeleton, setShowSkeleton] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const isProcessingRef = useRef(false);
  const animationFrameIdRef = useRef<number | null>(null);
  const lastCaptureTimeRef = useRef<number>(0);
  const captureIntervalMs = 1000 / targetFps;

  // Trigger ROM reset on WebSocket if requested
  useEffect(() => {
    if (resetRomTrigger && resetRomTrigger > 0 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send('reset_rom');
    }
  }, [resetRomTrigger]);

  // Synchronize active exercise selection over WebSocket
  useEffect(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'select_exercise',
        exercise: selectedExercise || null,
      }));
    }
  }, [selectedExercise]);

  // Trigger Exercise Repetition reset on WebSocket if requested
  useEffect(() => {
    if (resetExerciseTrigger && resetExerciseTrigger > 0 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'reset_exercise',
      }));
    }
  }, [resetExerciseTrigger]);

  // Determine WebSocket URL
  const getWebSocketUrl = () => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const wsProto = apiUrl.startsWith('https') ? 'wss:' : 'ws:';
    const host = apiUrl.replace(/^https?:\/\//, '');
    return `${wsProto}//${host}/ws/pose`;
  };

  // Draw skeleton and landmarks on overlay canvas
  const drawPoseSkeleton = useCallback((landmarks: LandmarkPoint[]) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = video.videoWidth || canvas.clientWidth;
    const height = video.videoHeight || canvas.clientHeight;

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    ctx.clearRect(0, 0, width, height);

    if (!showSkeleton || !landmarks || landmarks.length === 0) return;

    // Draw connection lines
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';

    SKELETON_CONNECTIONS.forEach(([startIdx, endIdx]) => {
      const p1 = landmarks[startIdx];
      const p2 = landmarks[endIdx];

      if (p1 && p2 && p1.visibility > 0.4 && p2.visibility > 0.4) {
        ctx.beginPath();
        ctx.moveTo(p1.x * width, p1.y * height);
        ctx.lineTo(p2.x * width, p2.y * height);

        // Gradient for athletic tech look
        const gradient = ctx.createLinearGradient(
          p1.x * width, p1.y * height,
          p2.x * width, p2.y * height
        );
        gradient.addColorStop(0, '#06b6d4'); // Cyan
        gradient.addColorStop(1, '#3b82f6'); // Blue
        ctx.strokeStyle = gradient;
        ctx.stroke();
      }
    });

    // Draw landmark joints
    landmarks.forEach((lm) => {
      if (lm.visibility > 0.35) {
        const cx = lm.x * width;
        const cy = lm.y * height;
        const isKey = KEY_JOINT_INDICES.has(lm.index);

        ctx.beginPath();
        ctx.arc(cx, cy, isKey ? 6 : 4, 0, 2 * Math.PI);
        ctx.fillStyle = isKey ? '#10b981' : '#38bdf8'; // Emerald for key joints, cyan for others
        ctx.fill();

        ctx.lineWidth = 2;
        ctx.strokeStyle = '#ffffff';
        ctx.stroke();
      }
    });
  }, [showSkeleton]);

  // Connect WebSocket
  const connectWebSocket = useCallback(() => {
    try {
      const url = getWebSocketUrl();
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setWsConnected(true);
        console.log('[LiveCamera] WebSocket connected to', url);
      };

      ws.onmessage = (event) => {
        isProcessingRef.current = false;
        try {
          const parsed = JSON.parse(event.data);
          if (
            parsed.type === 'pong' ||
            parsed.type === 'rom_reset' ||
            parsed.type === 'exercise_selected' ||
            parsed.type === 'exercise_reset'
          ) {
            return;
          }
          const result: PoseDetectionResult = parsed;
          drawPoseSkeleton(result.landmarks || []);
          if (onPoseResult) {
            onPoseResult(result);
          }
        } catch (err) {
          console.error('[LiveCamera] Failed to parse pose response:', err);
        }
      };

      ws.onerror = (err) => {
        console.warn('[LiveCamera] WebSocket error:', err);
        setWsConnected(false);
        isProcessingRef.current = false;
      };

      ws.onclose = () => {
        setWsConnected(false);
        isProcessingRef.current = false;
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[LiveCamera] Could not connect to WebSocket:', err);
      setWsConnected(false);
    }
  }, [drawPoseSkeleton, onPoseResult]);

  // Start webcam
  const startCamera = async () => {
    setCameraError(null);
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Webcam media devices API is not supported in this browser.');
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current?.play();
          setIsStreaming(true);
        };
      }

      connectWebSocket();
    } catch (err: any) {
      console.error('[LiveCamera] Webcam access error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraError('Camera permission denied. Please allow camera access in your browser settings.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraError('No webcam device detected on your system.');
      } else {
        setCameraError(err.message || 'Unable to access webcam.');
      }
      setIsStreaming(false);
    }
  };

  // Stop webcam
  const stopCamera = useCallback(() => {
    if (animationFrameIdRef.current) {
      cancelAnimationFrame(animationFrameIdRef.current);
      animationFrameIdRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Clear canvas
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx?.clearRect(0, 0, canvas.width, canvas.height);
    }

    setIsStreaming(false);
    setWsConnected(false);
    isProcessingRef.current = false;
  }, []);

  // Frame capture loop
  useEffect(() => {
    if (!isStreaming) return;

    let mounted = true;

    const captureLoop = (timestamp: number) => {
      if (!mounted) return;

      const video = videoRef.current;
      const ws = wsRef.current;

      if (
        video &&
        video.readyState >= 2 &&
        ws &&
        ws.readyState === WebSocket.OPEN &&
        !isProcessingRef.current &&
        timestamp - lastCaptureTimeRef.current >= captureIntervalMs
      ) {
        lastCaptureTimeRef.current = timestamp;

        if (!captureCanvasRef.current) {
          captureCanvasRef.current = document.createElement('canvas');
        }

        const captureCanvas = captureCanvasRef.current;
        const targetWidth = Math.min(video.videoWidth || 640, 640);
        const scale = targetWidth / (video.videoWidth || 640);
        const targetHeight = Math.round((video.videoHeight || 480) * scale);

        if (captureCanvas.width !== targetWidth || captureCanvas.height !== targetHeight) {
          captureCanvas.width = targetWidth;
          captureCanvas.height = targetHeight;
        }

        const ctx = captureCanvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(video, 0, 0, targetWidth, targetHeight);
          const dataUrl = captureCanvas.toDataURL('image/jpeg', 0.7);

          try {
            isProcessingRef.current = true;
            const payload = selectedExercise
              ? JSON.stringify({ frame: dataUrl, exercise: selectedExercise })
              : dataUrl;
            ws.send(payload);
          } catch (e) {
            isProcessingRef.current = false;
          }
        }
      }

      animationFrameIdRef.current = requestAnimationFrame(captureLoop);
    };

    animationFrameIdRef.current = requestAnimationFrame(captureLoop);

    return () => {
      mounted = false;
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
      }
    };
  }, [isStreaming, captureIntervalMs, selectedExercise]);

  // Clean up on component unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return (
    <div className="flex flex-col items-center w-full">
      {/* Video + Canvas Viewport */}
      <div className="relative w-full max-w-3xl aspect-[4/3] bg-gray-900 rounded-2xl overflow-hidden shadow-2xl border border-gray-800 flex items-center justify-center">
        {/* Native Video Feed */}
        <video
          ref={videoRef}
          playsInline
          muted
          autoPlay
          className={`w-full h-full object-cover transform -scale-x-100 ${isStreaming ? 'block' : 'hidden'}`}
        />

        {/* Skeleton Canvas Overlay */}
        <canvas
          ref={canvasRef}
          className={`absolute inset-0 w-full h-full object-cover pointer-events-none transform -scale-x-100 ${isStreaming ? 'block' : 'hidden'}`}
        />

        {/* Stream Inactive Placeholder */}
        {!isStreaming && (
          <div className="flex flex-col items-center justify-center p-8 text-center text-gray-400">
            <Camera className="w-16 h-16 text-gray-600 mb-4 animate-pulse" />
            <h3 className="text-lg font-semibold text-gray-200 mb-2">Live Camera Offline</h3>
            <p className="text-sm max-w-md text-gray-400 mb-6">
              Click below to grant camera access and activate real-time pose estimation.
            </p>
            <Button onClick={startCamera} className="shadow-lg shadow-blue-500/20">
              <Camera className="w-4 h-4 mr-2" /> Start Webcam
            </Button>
          </div>
        )}

        {/* Camera Permission / Device Error Notice */}
        {cameraError && (
          <div className="absolute top-4 left-4 right-4 bg-red-900/90 border border-red-500 text-red-200 px-4 py-3 rounded-xl flex items-center shadow-lg text-sm backdrop-blur-sm">
            <AlertCircle className="w-5 h-5 mr-3 shrink-0 text-red-400" />
            <span>{cameraError}</span>
          </div>
        )}

        {/* Real-time Status Overlay Badges */}
        {isStreaming && (
          <div className="absolute top-4 left-4 flex items-center space-x-2">
            <div className="flex items-center space-x-2 bg-gray-900/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-gray-700 text-xs font-medium text-white">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
              <span>LIVE</span>
            </div>

            <div className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full border text-xs font-medium backdrop-blur-md ${
              wsConnected
                ? 'bg-emerald-900/60 border-emerald-500 text-emerald-300'
                : 'bg-amber-900/60 border-amber-500 text-amber-300'
            }`}>
              {wsConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
              <span>{wsConnected ? 'Backend Synced' : 'Connecting...'}</span>
            </div>
          </div>
        )}
      </div>

      {/* Camera & Overlay Controls */}
      <div className="flex flex-wrap items-center justify-between w-full max-w-3xl mt-4 px-2 gap-3">
        <div className="flex items-center space-x-3">
          {isStreaming ? (
            <Button variant="danger" size="sm" onClick={stopCamera}>
              <CameraOff className="w-4 h-4 mr-2" /> Stop Camera
            </Button>
          ) : (
            <Button variant="primary" size="sm" onClick={startCamera}>
              <Camera className="w-4 h-4 mr-2" /> Start Camera
            </Button>
          )}

          {isStreaming && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSkeleton(!showSkeleton)}
            >
              {showSkeleton ? 'Hide Skeleton' : 'Show Skeleton'}
            </Button>
          )}
        </div>

        {isStreaming && !wsConnected && (
          <Button variant="outline" size="sm" onClick={connectWebSocket}>
            <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Retry Connection
          </Button>
        )}
      </div>
    </div>
  );
};
