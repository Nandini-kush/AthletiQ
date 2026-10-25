import React, { useState, useEffect } from 'react';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { LiveCamera } from '../components/LiveCamera';
import type { PoseDetectionResult } from '../components/LiveCamera';
import { createSession } from '../services/api';
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  Zap,
  Layers,
  Gauge,
  Info,
  RotateCcw,
  Scale,
  Compass,
  Ruler,
  TrendingUp,
  Play,
  Square,
  Award,
  Sparkles,
  ShieldAlert,
} from 'lucide-react';

export const LiveAnalysis: React.FC = () => {
  const [poseData, setPoseData] = useState<PoseDetectionResult | null>(null);
  const [resetRomTrigger, setResetRomTrigger] = useState<number>(0);
  const [resetExerciseTrigger, setResetExerciseTrigger] = useState<number>(0);

  // Exercise selection & session lifecycle
  const [selectedExercise, setSelectedExercise] = useState<string | null>('squat');
  const [isSessionActive, setIsSessionActive] = useState<boolean>(false);
  const [sessionStartTime, setSessionStartTime] = useState<Date | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [sessionSaveStatus, setSessionSaveStatus] = useState<{ success?: boolean; message?: string } | null>(null);

  const isDetected = poseData?.pose_detected ?? false;
  const landmarkCount = poseData?.landmarks?.length ?? 0;
  const confidencePercent = poseData ? Math.round(poseData.confidence * 100) : 0;
  const latencyMs = poseData?.inference_time_ms ?? 0;

  const bio = poseData?.biomechanics;
  const jointAngles = bio?.joint_angles ?? {};
  const segmentDistances = bio?.segment_distances_norm ?? {};
  const symmetry = bio?.symmetry;
  const romData = bio?.range_of_motion ?? {};
  const kinematics = bio?.kinematics;

  // Active exercise telemetry from backend state machine
  const exerciseInfo = poseData?.exercise;
  const repetitions = exerciseInfo?.repetitions ?? 0;
  const currentPhase = exerciseInfo?.phase ?? (selectedExercise ? 'standing' : 'idle');
  const formCues = exerciseInfo?.form_cues ?? [];
  const progressPct = exerciseInfo?.phase_progress_pct ?? 0.0;
  const candidateDetected = exerciseInfo?.candidate_detected;

  // Stage 6 Form Feedback & Correction telemetry
  const formFeedback = poseData?.form_feedback;
  const formStatus = formFeedback?.form_status ?? 'unavailable';
  const analysisAvailable = formFeedback?.analysis_available ?? false;
  const formFindings = formFeedback?.findings ?? [];
  const formLimitations = formFeedback?.limitations ?? [];

  // Live session timer
  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;
    if (isSessionActive) {
      timer = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isSessionActive]);

  const handleStartSession = () => {
    setIsSessionActive(true);
    setSessionStartTime(new Date());
    setElapsedSeconds(0);
    setSessionSaveStatus(null);
    setResetExerciseTrigger((prev) => prev + 1);
  };

  const handleFinishSession = async () => {
    if (!isSessionActive || !sessionStartTime) return;

    const endTime = new Date();
    const duration = Math.max(1, elapsedSeconds);
    const exerciseName = selectedExercise ? selectedExercise.replace(/_/g, ' ') : 'General Workout';

    try {
      await createSession({
        exercise_name: exerciseName.replace(/\b\w/g, (c) => c.toUpperCase()),
        started_at: sessionStartTime.toISOString(),
        ended_at: endTime.toISOString(),
        duration,
        total_repetitions: repetitions,
      });

      setSessionSaveStatus({
        success: true,
        message: `Session saved: ${repetitions} reps in ${formatTime(duration)} logged to athlete history!`,
      });
    } catch (err: any) {
      setSessionSaveStatus({
        success: false,
        message: err.message || 'Failed to save session to athlete profile.',
      });
    } finally {
      setIsSessionActive(false);
      setSessionStartTime(null);
    }
  };

  const handleResetReps = () => {
    setResetExerciseTrigger((prev) => prev + 1);
  };

  const handleResetRom = () => {
    setResetRomTrigger((prev) => prev + 1);
  };

  const formatTime = (totalSec: number): string => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatAngle = (val: number | null | undefined): string => {
    if (val === null || val === undefined || isNaN(val)) return 'N/A';
    return `${Math.round(val)}°`;
  };

  const formatDiff = (val: number | null | undefined): string => {
    if (val === null || val === undefined || isNaN(val)) return 'N/A';
    return `${Math.round(val)}°`;
  };

  const formatDistance = (val: number | null | undefined): string => {
    if (val === null || val === undefined || isNaN(val)) return 'N/A';
    return `${val.toFixed(3)} norm`;
  };

  const getPhaseBadgeColor = (phase: string) => {
    switch (phase.toLowerCase()) {
      case 'bottom':
      case 'contracted':
        return 'bg-purple-100 text-purple-900 border-purple-300';
      case 'descending':
      case 'lowering':
      case 'curling':
        return 'bg-amber-100 text-amber-900 border-amber-300';
      case 'ascending':
      case 'pushing':
        return 'bg-blue-100 text-blue-900 border-blue-300';
      case 'standing':
      case 'top_plank':
      case 'extended':
        return 'bg-emerald-100 text-emerald-900 border-emerald-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getFormStatusBadge = (status: string) => {
    switch (status) {
      case 'good':
        return 'bg-emerald-100 text-emerald-900 border-emerald-300';
      case 'needs_attention':
        return 'bg-amber-100 text-amber-900 border-amber-300';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-300';
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
            Live Exercise & Form Feedback Analysis
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time finite state repetition counting, rule-based form correction, and joint trigonometry.
          </p>
        </div>

        {/* Dynamic Pose Status Badge & ROM Reset */}
        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetRom}
            className="flex items-center text-xs"
            title="Reset Range of Motion tracking memory"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
            Reset ROM
          </Button>

          <div
            className={`inline-flex items-center px-4 py-2 rounded-xl text-sm font-semibold border shadow-sm transition-all duration-300 ${
              isDetected
                ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                : 'bg-amber-50 border-amber-300 text-amber-800'
            }`}
          >
            {isDetected ? (
              <>
                <CheckCircle2 className="w-5 h-5 mr-2 text-emerald-600 animate-pulse" />
                <span>Pose Detected</span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-5 h-5 mr-2 text-amber-600" />
                <span>No Pose Detected</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Exercise Selector & Session Action Bar */}
      <Card className="p-4 bg-gradient-to-r from-slate-900 via-gray-900 to-indigo-950 text-white shadow-xl border-gray-800">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          {/* Exercise Selection Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 mr-2">
              Exercise:
            </span>
            {[
              { id: 'squat', label: 'Squat' },
              { id: 'push_up', label: 'Push-up' },
              { id: 'bicep_curl', label: 'Bicep Curl' },
              { id: null, label: 'Free Form' },
            ].map(({ id, label }) => {
              const active = selectedExercise === id;
              return (
                <button
                  key={label}
                  onClick={() => setSelectedExercise(id)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm ${
                    active
                      ? 'bg-blue-600 text-white ring-2 ring-blue-400 shadow-blue-500/30'
                      : 'bg-gray-800/80 text-gray-300 hover:bg-gray-700/80 hover:text-white border border-gray-700'
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>

          {/* Session Timer & Action Controls */}
          <div className="flex items-center space-x-3">
            {isSessionActive && (
              <div className="flex items-center space-x-2 bg-gray-800/90 border border-emerald-500/40 px-3 py-1.5 rounded-lg">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                <span className="text-xs font-mono font-bold text-emerald-300">
                  {formatTime(elapsedSeconds)}
                </span>
              </div>
            )}

            {!isSessionActive ? (
              <Button
                variant="primary"
                size="sm"
                onClick={handleStartSession}
                className="flex items-center text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-bold"
              >
                <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
                Start Session
              </Button>
            ) : (
              <Button
                variant="danger"
                size="sm"
                onClick={handleFinishSession}
                className="flex items-center text-xs bg-rose-600 hover:bg-rose-500 text-white font-bold"
              >
                <Square className="w-3.5 h-3.5 mr-1.5 fill-current" />
                Finish & Save
              </Button>
            )}

            {selectedExercise && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetReps}
                className="text-xs text-gray-300 border-gray-700 hover:bg-gray-800 hover:text-white"
              >
                <RotateCcw className="w-3.5 h-3.5 mr-1" />
                Reset Reps
              </Button>
            )}
          </div>
        </div>

        {/* Session Saved Notification */}
        {sessionSaveStatus && (
          <div
            className={`mt-3 p-2.5 rounded-lg text-xs flex items-center justify-between ${
              sessionSaveStatus.success
                ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-200'
                : 'bg-rose-500/20 border border-rose-500/40 text-rose-200'
            }`}
          >
            <span className="font-medium">{sessionSaveStatus.message}</span>
            <button
              onClick={() => setSessionSaveStatus(null)}
              className="text-gray-400 hover:text-white ml-2 text-xs font-bold"
            >
              ×
            </button>
          </div>
        )}
      </Card>

      {/* Stage 5 Real-Time Exercise HUD Panel (when exercise is selected) */}
      {selectedExercise && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* 1. Large Repetition Counter Card */}
          <Card className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-700 flex items-center">
                <Award className="w-4 h-4 mr-1 text-blue-600" />
                Repetitions
              </span>
              <span className="text-[10px] bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full font-bold">
                {selectedExercise.toUpperCase()}
              </span>
            </div>
            <div className="my-2 text-center">
              <div className="text-5xl font-black text-blue-900 font-mono tracking-tight">
                {repetitions}
              </div>
              <div className="text-xs text-blue-600 font-medium mt-1">
                Completed cycles
              </div>
            </div>
            <div className="text-[11px] text-gray-500 text-center">
              Full range motion only
            </div>
          </Card>

          {/* 2. Exercise Movement Phase & Cycle Progress Card */}
          <Card className="p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
                  Current Phase
                </span>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-bold border uppercase tracking-wider ${getPhaseBadgeColor(
                    currentPhase
                  )}`}
                >
                  {currentPhase.replace(/_/g, ' ')}
                </span>
              </div>

              {/* Rep cycle progress meter */}
              <div className="mt-3">
                <div className="flex justify-between text-xs font-semibold text-gray-700 mb-1">
                  <span>Cycle Progress</span>
                  <span>{Math.round(progressPct)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-200"
                    style={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="mt-3 text-[11px] text-gray-400">
              State transitions require full range
            </div>
          </Card>

          {/* 3. Primary Joint Angle Telemetry Card */}
          <Card className="p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center">
                <Compass className="w-4 h-4 mr-1 text-indigo-600" />
                Target Angle
              </span>
              <span className="text-[10px] bg-indigo-50 text-indigo-700 font-bold px-2 py-0.5 rounded-full border border-indigo-200">
                {exerciseInfo?.primary_metric_name?.replace(/_/g, ' ') || 'Joint Angle'}
              </span>
            </div>

            <div className="my-2 text-center">
              <div className="text-4xl font-extrabold text-indigo-900 font-mono">
                {exerciseInfo?.primary_metric_value !== null && exerciseInfo?.primary_metric_value !== undefined
                  ? `${exerciseInfo.primary_metric_value}°`
                  : '—'}
              </div>
              <div className="text-xs text-indigo-600 font-medium mt-1">
                {selectedExercise === 'squat'
                  ? 'Knee Flexion (Goal: ≤ 100°)'
                  : selectedExercise === 'push_up'
                  ? 'Elbow Flexion (Goal: ≤ 90°)'
                  : 'Elbow Contraction (Goal: ≤ 65°)'}
              </div>
            </div>

            <div className="text-[11px] text-gray-400 text-center">
              Filtered with temporal smoothing
            </div>
          </Card>

          {/* 4. Real-Time Form Cues & Posture Card */}
          <Card className="p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center">
                <Sparkles className="w-4 h-4 mr-1 text-amber-500" />
                Movement Cues
              </span>
              {candidateDetected && (
                <span className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded font-mono">
                  Posture: {candidateDetected}
                </span>
              )}
            </div>

            <div className="space-y-1.5 my-1 max-h-[85px] overflow-y-auto">
              {formCues.length > 0 ? (
                formCues.map((cue, idx) => (
                  <div
                    key={idx}
                    className="p-1.5 bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded font-medium flex items-center"
                  >
                    <Info className="w-3.5 h-3.5 mr-1.5 text-amber-600 shrink-0" />
                    <span>{cue}</span>
                  </div>
                ))
              ) : (
                <div className="p-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded font-medium flex items-center">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-600 shrink-0" />
                  <span>Good form — keep moving!</span>
                </div>
              )}
            </div>

            <div className="text-[11px] text-gray-400">
              Form guidance based on actual joint geometry
            </div>
          </Card>
        </div>
      )}

      {/* Stage 6 Real-Time Exercise Form Correction & Feedback Panel */}
      {selectedExercise && (
        <Card className="p-5 border-l-4 border-l-blue-600 bg-white shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-gray-100 gap-2 mb-4">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-5 h-5 text-blue-600" />
              <h3 className="font-bold text-gray-900 text-sm tracking-tight">
                Real-Time Form Correction & Biomechanical Feedback
              </h3>
              <span className="text-[11px] text-gray-500 font-medium hidden sm:inline">
                (Rule-based evaluation)
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-xs text-gray-500 font-medium">Form Status:</span>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${getFormStatusBadge(
                  formStatus
                )}`}
              >
                {formStatus === 'good' && <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />}
                {formStatus === 'needs_attention' && <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-600" />}
                {formStatus === 'unavailable' && <Info className="w-3.5 h-3.5 mr-1 text-gray-500" />}
                {formStatus === 'good'
                  ? 'Good Form'
                  : formStatus === 'needs_attention'
                  ? 'Needs Attention'
                  : 'Analysis Limited'}
              </span>
            </div>
          </div>

          {/* Active Findings List */}
          {formFindings.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
              {formFindings.map((f, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-xl border flex flex-col justify-between text-xs ${
                    f.severity === 'warning'
                      ? 'bg-amber-50/70 border-amber-200 text-amber-950'
                      : 'bg-blue-50/70 border-blue-200 text-blue-950'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wide ${
                          f.severity === 'warning'
                            ? 'bg-amber-200 text-amber-900'
                            : 'bg-blue-200 text-blue-900'
                        }`}
                      >
                        {f.severity === 'warning' ? 'Form Correction' : 'Movement Indicator'}
                      </span>
                      {f.measurement?.value !== null && f.measurement?.value !== undefined && (
                        <span className="font-mono font-bold bg-white/90 px-2 py-0.5 rounded border text-[11px] text-gray-800 shadow-2xs">
                          {f.measurement.name.replace(/_/g, ' ')}: {f.measurement.value}
                          {f.measurement.unit === 'degrees' ? '°' : ''}
                        </span>
                      )}
                    </div>
                    <p className="font-semibold text-gray-900 mt-1">{f.message}</p>
                  </div>
                  <div className="mt-2.5 pt-2 border-t border-black/5 flex items-start text-gray-700 leading-relaxed">
                    <span className="font-bold mr-1 text-gray-900 shrink-0">Suggestion:</span>
                    <span>{f.recommendation}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : analysisAvailable ? (
            <div className="p-3.5 bg-emerald-50/80 border border-emerald-200 rounded-xl flex items-center text-xs text-emerald-900 font-medium">
              <CheckCircle2 className="w-4 h-4 mr-2.5 text-emerald-600 shrink-0" />
              <span>
                <strong>Optimal Movement Pattern:</strong> Joint kinematics match standard form parameters through this movement phase.
              </span>
            </div>
          ) : (
            <div className="p-3.5 bg-gray-50 border border-gray-200 rounded-xl flex items-center text-xs text-gray-600">
              <Info className="w-4 h-4 mr-2 text-gray-500 shrink-0" />
              <span>Form analysis will update as you execute the movement cycle in view of the camera.</span>
            </div>
          )}

          {/* Camera View Notice / Limitations */}
          {formLimitations.length > 0 && (
            <div className="mt-3 p-2 bg-gray-100 rounded-lg text-[11px] text-gray-600 flex items-center space-x-2">
              <Info className="w-3.5 h-3.5 text-gray-500 shrink-0" />
              <span>
                <strong>Camera View Notice:</strong> {formLimitations.join(' ')}
              </span>
            </div>
          )}
        </Card>
      )}

      {/* Main Viewport & Real-Time Biomechanics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Live Camera & Skeleton Viewport */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="p-4 bg-white/80 backdrop-blur-sm border-gray-200">
            <LiveCamera
              onPoseResult={setPoseData}
              targetFps={15}
              resetRomTrigger={resetRomTrigger}
              selectedExercise={selectedExercise}
              resetExerciseTrigger={resetExerciseTrigger}
            />
          </Card>

          {/* Performance & Stream Telemetry */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="p-3 text-center">
              <div className="flex items-center justify-center text-blue-600 mb-1">
                <Zap className="w-4 h-4 mr-1" />
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Latency</span>
              </div>
              <p className="text-lg font-bold text-gray-900">
                {latencyMs > 0 ? `${latencyMs} ms` : '—'}
              </p>
            </Card>

            <Card className="p-3 text-center">
              <div className="flex items-center justify-center text-emerald-600 mb-1">
                <Gauge className="w-4 h-4 mr-1" />
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</span>
              </div>
              <p className="text-lg font-bold text-gray-900">
                {confidencePercent > 0 ? `${confidencePercent}%` : '—'}
              </p>
            </Card>

            <Card className="p-3 text-center">
              <div className="flex items-center justify-center text-indigo-600 mb-1">
                <Layers className="w-4 h-4 mr-1" />
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Landmarks</span>
              </div>
              <p className="text-lg font-bold text-gray-900">
                {landmarkCount > 0 ? `${landmarkCount} / 33` : '0 / 33'}
              </p>
            </Card>

            <Card className="p-3 text-center">
              <div className="flex items-center justify-center text-purple-600 mb-1">
                <TrendingUp className="w-4 h-4 mr-1" />
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Speed (norm/s)</span>
              </div>
              <p className="text-lg font-bold text-gray-900">
                {kinematics?.overall_movement_speed_norm_per_sec !== undefined
                  ? kinematics.overall_movement_speed_norm_per_sec.toFixed(3)
                  : '—'}
              </p>
            </Card>
          </div>
        </div>

        {/* Right Column: Key Biomechanical Angles & Symmetry */}
        <div className="space-y-4">
          <Card className="p-5 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b pb-3 mb-4">
                <h3 className="font-semibold text-gray-900 flex items-center">
                  <Compass className="w-4 h-4 mr-2 text-blue-600" />
                  Real-Time Joint Angles
                </h3>
                <span className="text-xs bg-blue-50 text-blue-700 font-medium px-2 py-0.5 rounded-full border border-blue-200">
                  Trigonometric
                </span>
              </div>

              {/* Bilateral Comparison Table */}
              <div className="space-y-3">
                {/* Knees */}
                <div className="p-3 rounded-xl border border-gray-200 bg-gray-50/70">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">Knees</span>
                    <span className="text-xs text-gray-500 font-mono">
                      Diff: <strong className="text-gray-900">{formatDiff(symmetry?.joint_angle_differences_deg?.knee_diff_deg)}</strong>
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div className="bg-white p-2 rounded-lg border border-gray-100 shadow-sm">
                      <div className="text-[11px] text-gray-500 font-medium">Left Knee</div>
                      <div className="text-lg font-extrabold text-blue-600 font-mono">
                        {formatAngle(jointAngles.left_knee)}
                      </div>
                    </div>
                    <div className="bg-white p-2 rounded-lg border border-gray-100 shadow-sm">
                      <div className="text-[11px] text-gray-500 font-medium">Right Knee</div>
                      <div className="text-lg font-extrabold text-indigo-600 font-mono">
                        {formatAngle(jointAngles.right_knee)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Elbows */}
                <div className="p-3 rounded-xl border border-gray-200 bg-gray-50/70">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">Elbows</span>
                    <span className="text-xs text-gray-500 font-mono">
                      Diff: <strong className="text-gray-900">{formatDiff(symmetry?.joint_angle_differences_deg?.elbow_diff_deg)}</strong>
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div className="bg-white p-2 rounded-lg border border-gray-100 shadow-sm">
                      <div className="text-[11px] text-gray-500 font-medium">Left Elbow</div>
                      <div className="text-lg font-extrabold text-blue-600 font-mono">
                        {formatAngle(jointAngles.left_elbow)}
                      </div>
                    </div>
                    <div className="bg-white p-2 rounded-lg border border-gray-100 shadow-sm">
                      <div className="text-[11px] text-gray-500 font-medium">Right Elbow</div>
                      <div className="text-lg font-extrabold text-indigo-600 font-mono">
                        {formatAngle(jointAngles.right_elbow)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Shoulders */}
                <div className="p-3 rounded-xl border border-gray-200 bg-gray-50/70">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">Shoulders</span>
                    <span className="text-xs text-gray-500 font-mono">
                      Diff: <strong className="text-gray-900">{formatDiff(symmetry?.joint_angle_differences_deg?.shoulder_diff_deg)}</strong>
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div className="bg-white p-2 rounded-lg border border-gray-100 shadow-sm">
                      <div className="text-[11px] text-gray-500 font-medium">Left Shoulder</div>
                      <div className="text-lg font-extrabold text-blue-600 font-mono">
                        {formatAngle(jointAngles.left_shoulder)}
                      </div>
                    </div>
                    <div className="bg-white p-2 rounded-lg border border-gray-100 shadow-sm">
                      <div className="text-[11px] text-gray-500 font-medium">Right Shoulder</div>
                      <div className="text-lg font-extrabold text-indigo-600 font-mono">
                        {formatAngle(jointAngles.right_shoulder)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Hips */}
                <div className="p-3 rounded-xl border border-gray-200 bg-gray-50/70">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">Hips</span>
                    <span className="text-xs text-gray-500 font-mono">
                      Diff: <strong className="text-gray-900">{formatDiff(symmetry?.joint_angle_differences_deg?.hip_diff_deg)}</strong>
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div className="bg-white p-2 rounded-lg border border-gray-100 shadow-sm">
                      <div className="text-[11px] text-gray-500 font-medium">Left Hip</div>
                      <div className="text-lg font-extrabold text-blue-600 font-mono">
                        {formatAngle(jointAngles.left_hip)}
                      </div>
                    </div>
                    <div className="bg-white p-2 rounded-lg border border-gray-100 shadow-sm">
                      <div className="text-[11px] text-gray-500 font-medium">Right Hip</div>
                      <div className="text-lg font-extrabold text-indigo-600 font-mono">
                        {formatAngle(jointAngles.right_hip)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Symmetry Score Badge */}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200 flex items-center justify-between">
                <div className="flex items-center">
                  <Scale className="w-5 h-5 text-blue-600 mr-2" />
                  <div>
                    <div className="text-xs font-bold text-gray-800">Movement Symmetry Score</div>
                    <div className="text-[11px] text-gray-500">Bilateral kinematic balance</div>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-lg font-extrabold text-blue-700 font-mono">
                    {symmetry?.movement_symmetry_score !== null && symmetry?.movement_symmetry_score !== undefined
                      ? `${symmetry.movement_symmetry_score}%`
                      : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Secondary Biomechanics Detail Panels: ROM, Segment Distances & Kinematics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Dynamic Range of Motion (ROM) */}
        <Card className="p-5">
          <div className="flex items-center justify-between border-b pb-3 mb-4">
            <h3 className="font-semibold text-gray-900 flex items-center">
              <Activity className="w-4 h-4 mr-2 text-emerald-600" />
              Dynamic Range of Motion (ROM)
            </h3>
            <span className="text-xs bg-emerald-50 text-emerald-700 font-medium px-2 py-0.5 rounded-full border border-emerald-200">
              Max - Min
            </span>
          </div>

          <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
            {['left_knee', 'right_knee', 'left_elbow', 'right_elbow', 'left_shoulder', 'right_shoulder', 'left_hip', 'right_hip'].map(
              (jointKey) => {
                const item = romData[jointKey];
                const formattedName = jointKey.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
                return (
                  <div key={jointKey} className="p-2.5 rounded-lg border border-gray-100 bg-gray-50 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-medium text-gray-900">{formattedName}</div>
                      <div className="text-gray-500 text-[11px] font-mono mt-0.5">
                        Min: {formatAngle(item?.min_angle)} | Max: {formatAngle(item?.max_angle)}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="inline-block px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-bold font-mono text-xs">
                        ROM: {item?.rom !== null && item?.rom !== undefined ? `${Math.round(item.rom)}°` : 'N/A'}
                      </span>
                    </div>
                  </div>
                );
              }
            )}
          </div>
        </Card>

        {/* Body Segment Distances */}
        <Card className="p-5">
          <div className="flex items-center justify-between border-b pb-3 mb-4">
            <h3 className="font-semibold text-gray-900 flex items-center">
              <Ruler className="w-4 h-4 mr-2 text-indigo-600" />
              Segment Distances (Normalized)
            </h3>
            <span className="text-xs bg-indigo-50 text-indigo-700 font-medium px-2 py-0.5 rounded-full border border-indigo-200">
              Euclidean
            </span>
          </div>

          <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
            {[
              { key: 'shoulder_width', label: 'Shoulder Width' },
              { key: 'hip_width', label: 'Hip Width' },
              { key: 'left_upper_arm', label: 'Left Upper Arm' },
              { key: 'right_upper_arm', label: 'Right Upper Arm' },
              { key: 'left_forearm', label: 'Left Forearm' },
              { key: 'right_forearm', label: 'Right Forearm' },
              { key: 'left_thigh', label: 'Left Thigh' },
              { key: 'right_thigh', label: 'Right Thigh' },
              { key: 'left_lower_leg', label: 'Left Lower Leg' },
              { key: 'right_lower_leg', label: 'Right Lower Leg' },
            ].map(({ key, label }) => {
              const val = segmentDistances[key];
              return (
                <div key={key} className="p-2 rounded-lg border border-gray-100 bg-gray-50 flex items-center justify-between text-xs">
                  <span className="font-medium text-gray-700">{label}</span>
                  <span className="font-mono font-bold text-gray-900">{formatDistance(val)}</span>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Kinematic Extremities & Speed */}
        <Card className="p-5">
          <div className="flex items-center justify-between border-b pb-3 mb-4">
            <h3 className="font-semibold text-gray-900 flex items-center">
              <TrendingUp className="w-4 h-4 mr-2 text-purple-600" />
              Extremities Kinematics
            </h3>
            <span className="text-xs bg-purple-50 text-purple-700 font-medium px-2 py-0.5 rounded-full border border-purple-200">
              Image Space
            </span>
          </div>

          <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
            {kinematics?.landmarks_kinematics && Object.keys(kinematics.landmarks_kinematics).length > 0 ? (
              Object.entries(kinematics.landmarks_kinematics).map(([ptName, k]) => {
                const formattedName = ptName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
                return (
                  <div key={ptName} className="p-2.5 rounded-lg border border-gray-100 bg-gray-50 text-xs">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-medium text-gray-900">{formattedName}</span>
                      <span className="font-mono text-xs font-bold text-purple-700">
                        {k.speed_norm_per_sec.toFixed(3)} /s
                      </span>
                    </div>
                    <div className="text-[11px] text-gray-500 font-mono flex justify-between">
                      <span>Disp: {k.displacement_norm.toFixed(3)}</span>
                      <span>Accel: {k.acceleration_norm_per_sec2.toFixed(2)} /s²</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-10 text-gray-400">
                <p className="text-xs">No active movement kinematics tracked yet.</p>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Scientific & Academic Limitations Disclaimer */}
      <Card className="p-4 bg-blue-50/80 border-blue-200 text-blue-900 text-xs leading-relaxed">
        <div className="flex items-start">
          <Info className="w-5 h-5 mr-3 text-blue-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold text-blue-950">
              Scientific & Academic Biomechanics & Exercise Disclaimer
            </div>
            <p>
              AthletiQ uses webcam-based computer vision for geometric estimation. Coordinates and segment distances
              are normalized image-space measurements, not calibrated metric units (meters/centimeters). Joint angles
              are 3-point trigonometric vector projections subject to camera perspective, parallax, and landmark visibility.
              Form correction observations and movement symmetry indicators reflect bilateral geometric alignment and are <strong>not medical advice</strong>, clinical rehabilitation assessments, or injury diagnoses.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
