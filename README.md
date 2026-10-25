<<<<<<< HEAD
# AthletiQ

**AthletiQ: An AI-Based Real-Time Athlete Performance, Strength, and Biomechanical Analysis System**

---

## Current Development Stage: STAGE 6 (Exercise Form Correction and Real-Time Feedback)
- **Stage 1**: Foundation (Frontend React/Vite/Tailwind + FastAPI Backend) — ✅ COMPLETE
- **Stage 2**: Database Models + User Authentication (SQLAlchemy + Alembic + JWT + Protected Routes) — ✅ COMPLETE
- **Stage 3**: Real-Time Webcam + MediaPipe Pose Estimation (WebSocket `/ws/pose` + HTML5 Canvas Skeleton Overlay + 33-Landmark Telemetry) — ✅ COMPLETE
- **Stage 4**: Biomechanics Engine (Joint Angles, Segment Distances, Bilateral Symmetry, Dynamic ROM, Kinematics, Temporal Smoothing) — ✅ COMPLETE
- **Stage 5**: Exercise Classification & Repetition State Machines (Squat, Push-up, Bicep Curl, Temporal Hysteresis, Form Cues, Session API Persistence) — ✅ COMPLETE
- **Stage 6**: Real-Time Rule-Based Form Correction & Feedback (Deterministic Rules, Temporal Dwell Stabilization, Cooldown, Severity Grading, Live UI Visualizer) — ✅ COMPLETE
- **Stage 7**: Advanced Fatigue Tracking & Longitudinal Performance Analytics — ⏳ PLANNED NEXT

---

## Technology Stack
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Lucide Icons, React Router v7
- **Backend**: FastAPI, Python 3.13, MediaPipe 1.0.1 (Tasks API), OpenCV 5.0, NumPy 2.5, Uvicorn, WebSockets
- **Database & Auth**: PostgreSQL / SQLite (Local Dev Fallback), SQLAlchemy 2.0, Alembic, Passlib (Bcrypt), Python-Jose (JWT)

---

## Project Structure
```text
AthletiQ/
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable components (LiveCamera, Button, Card, ProtectedRoute)
│   │   ├── context/          # React AuthContext
│   │   ├── layouts/          # MainLayout with sidebar & header
│   │   ├── pages/            # Landing, Login, Register, Dashboard, LiveAnalysis, History, Profile
│   │   └── services/         # Typed API client (sessions, profile, auth)
│   └── package.json
├── backend/
│   ├── alembic/              # Database migrations
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py       # JWT auth dependency
│   │   │   └── routers/      # auth, users, athletes, sessions, ws_pose
│   │   ├── biomechanics/     # Dedicated Biomechanics Engine
│   │   │   ├── __init__.py
│   │   │   ├── angles.py     # 3-point trigonometric vector joint angle formulas
│   │   │   ├── distances.py  # Normalized Euclidean segment distance measurements
│   │   │   ├── engine.py     # BiomechanicsEngine orchestrator
│   │   │   ├── movement.py   # RangeOfMotionTracker & KinematicMovementTracker
│   │   │   ├── smoothing.py  # ExponentialMovingAverageFilter (EMA)
│   │   │   └── symmetry.py   # Bilateral symmetry and movement balance index
│   │   ├── exercises/        # Stage 5 Exercise Analysis & Repetition Counting
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # ExerciseStateMachine base with hysteresis & debounce
│   │   │   ├── squat.py      # SquatStateMachine (standing -> descending -> bottom -> ascending)
│   │   │   ├── push_up.py    # PushUpStateMachine (top_plank -> lowering -> bottom -> pushing)
│   │   │   ├── bicep_curl.py # BicepCurlStateMachine (extended -> curling -> contracted -> lowering)
│   │   │   ├── classifier.py # Advisory heuristic posture classifier
│   │   │   └── manager.py    # ExerciseAnalysisManager
│   │   ├── form_analysis/    # Stage 6 Real-Time Exercise Form Feedback
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py    # Pydantic schemas (FormFinding, FormAnalysisResult)
│   │   │   ├── rules.py      # Deterministic form rules & threshold definitions
│   │   │   ├── feedback.py   # FeedbackStabilizer (dwell confirmation & repeat cooldown)
│   │   │   └── analyzer.py   # FormAnalyzer coordinator
│   │   ├── core/             # config, security (hashing, JWT)
│   │   ├── cv/               # pose_estimator, frame_processor, landmarks
│   │   │   └── models/       # MediaPipe pose_landmarker_lite.task
│   │   ├── db/               # session, base
│   │   ├── models/           # SQLAlchemy models (User, AthleteProfile, ExerciseSession)
│   │   ├── schemas/          # Pydantic schemas (exercise, biomechanics, pose, auth, etc.)
│   │   └── main.py           # FastAPI entrypoint
│   ├── requirements.txt
│   ├── test_stage2.py        # Automated test suite for Stage 2
│   ├── test_stage3.py        # Automated test suite for Stage 3
│   ├── test_stage4.py        # Automated test suite for Stage 4
│   ├── test_stage5.py        # Automated test suite for Stage 5
│   └── test_stage6.py        # Automated test suite for Stage 6
├── .env.example
└── README.md
```

---

## Exercise State Machines & Repetition Counting (Stage 5)

AthletiQ tracks exercise repetitions using deterministic Finite State Machines (FSM). Repetitions are counted **strictly upon the completion of a full range-of-motion cycle**. Partial movements, premature reversals, and noisy jitter are rejected.

### 1. Squat Analysis
- **Phases**: `standing` $\to$ `descending` $\to$ `bottom` $\to$ `ascending` $\to$ `standing`
- **Configurable Thresholds**:
  - `standing_knee`: $\ge 160.0^\circ$ (upright posture)
  - `descending_knee`: $< 145.0^\circ$ (knees flexing downward)
  - `bottom_knee`: $\le 100.0^\circ$ (depth target)
  - `ascending_knee`: $> 115.0^\circ$ (rising from hole)
  - `valgus_ratio`: $0.85$ (knee distance / ankle distance)
- **Counting Rule**: Repetition increments only when transitioning from `ascending` to `standing` after `bottom` has been successfully reached.
- **Partial Rep Rejection**: If an athlete descends and returns to `standing` without reaching $\le 100.0^\circ$, the state resets to `standing` with zero rep count and a cue: *"Squat deeper for full depth"*.
- **Form Cues**:
  - Knee Valgus check: Alerts if knees cave inward relative to ankles during movement.
  - Forward Lean check: Alerts if hip flexion drops below $65^\circ$.
  - Depth feedback: Confirms when valid squat depth is achieved.

### 2. Push-up Analysis
- **Phases**: `top_plank` $\to$ `lowering` $\to$ `bottom` $\to$ `pushing` $\to$ `top_plank`
- **Configurable Thresholds**:
  - `top_elbow`: $\ge 150.0^\circ$ (arms extended in plank)
  - `lowering_elbow`: $< 135.0^\circ$ (flexing elbows downward)
  - `bottom_elbow`: $\le 90.0^\circ$ (chest lowered to floor)
  - `pushing_elbow`: $> 105.0^\circ$ (pushing upward)
  - `min_hip_angle`: $140.0^\circ$ (torso plank alignment)
- **Counting Rule**: Repetition increments only when completing the full cycle back to `top_plank` after hitting $\le 90.0^\circ$.
- **Partial Rep Rejection**: Reversing early without reaching $\le 90^\circ$ returns to `top_plank` without incrementing repetitions.
- **Form Cues**:
  - Hip Sag / Piking check: Alerts if hip angle drops below $140^\circ$ (*"Keep core tight — avoid sagging or piking hips"*).
  - Depth check: Prompts to lower chest closer to the floor if descending is aborted.

### 3. Bicep Curl Analysis
- **Phases**: `extended` $\to$ `curling` $\to$ `contracted` $\to$ `lowering` $\to$ `extended`
- **Configurable Thresholds**:
  - `extended_elbow`: $\ge 150.0^\circ$ (full bottom arm extension)
  - `curling_elbow`: $< 135.0^\circ$ (curling upward)
  - `contracted_elbow`: $\le 65.0^\circ$ (peak contraction at top)
  - `lowering_elbow`: $> 80.0^\circ$ (extending downward)
- **Counting Rule**: Repetition increments only when returning to `extended` ($\ge 150^\circ$) after hitting peak contraction ($\le 65^\circ$).
- **Partial Rep Rejection**: Reversing downward before peak contraction resets phase with zero rep awarded.
- **Form Cues**:
  - Full bottom extension prompt if starting before $\ge 140^\circ$.
  - Peak contraction confirmation at the top of the curl.

---

## Hysteresis & Duplicate-Count Prevention
To eliminate double counts and chatter around phase boundaries:
1. **Minimum Rep Interval**: Enforces a temporal dwell window (default $0.6 - 0.7\text{s}$) between counted repetitions.
2. **Phase Dwell Debounce**: Requires a minimum duration in a given phase ($0.15\text{s}$) before permitting subsequent transitions.
3. **Temporal Filtering**: Uses EMA joint angle smoothing ($\alpha = 0.70$) to prevent single-frame landmark flutter from triggering state transitions.

---

## Session API & Database Integration
- Real-time video frames and landmark streams remain strictly in-memory over the WebSocket pipeline.
- The athlete initiates workout tracking by clicking **Start Session**, which begins a live in-memory timer and repetition accumulator.
- Clicking **Finish & Save** aggregates session duration and total repetitions, committing a single record to the database via authenticated `POST /api/sessions/`:
  ```json
  {
    "exercise_name": "Squat",
    "started_at": "2026-10-25T11:00:00.000Z",
    "ended_at": "2026-10-25T11:02:30.000Z",
    "duration": 150,
    "total_repetitions": 15
  }
  ```
- All session records are securely isolated to the authenticated athlete's profile.

---

## Real-Time Exercise Form Analysis & Feedback (Stage 6)

Stage 6 builds a deterministic, rule-based form evaluation engine that analyzes movement execution in real time without black-box ML guesswork or medical claims.

### 1. Architecture Pipeline
```text
WEBCAM FRAME
     ↓
MEDIAPIPE POSE (33 landmarks, visibility scores)
     ↓
BIOMECHANICS ENGINE (joint angles, segment distances, bilateral symmetry)
     ↓
EXERCISE STATE MACHINE (current phase: bottom, top, ascending, etc.)
     ↓
FORM RULES EVALUATOR (squat, push-up, bicep curl rules)
     ↓
FEEDBACK STABILIZER (2-frame dwell confirmation, 1.8s cooldown)
     ↓
WEBSOCKET /ws/pose (form_feedback payload)
     ↓
LIVE ANALYSIS UI (status badge, active findings cards, suggestions, measurements)
```

### 2. Supported Exercise Rules & Fault Codes

#### Squat Rules
- **`SQUAT_DEPTH_LIMITED`** (Warning): Bottom phase knee angle $> 105.0^\circ$. Cue: *"Descend deeper until thighs reach parallel with the floor."*
- **`EXCESSIVE_TORSO_LEAN`** (Warning): Bottom/ascending phase hip angle $< 60.0^\circ$. Cue: *"Keep your chest proud and brace your core to prevent excessive forward tilt."*
- **`KNEE_ASYMMETRY`** (Warning): Active phase knee angle difference $> 15.0^\circ$. Cue: *"Distribute body weight evenly across both feet."*
- **`KNEE_VALGUS`** (Warning): Bottom/ascending phase knee-to-ankle width ratio $< 0.82$. Cue: *"Drive knees outward tracking over your mid-toes."*
- **`INCOMPLETE_LOCKOUT`** (Info): Standing phase knee angle $< 155.0^\circ$. Cue: *"Stand tall and fully extend knees at the top of each rep."*

#### Push-up Rules
- **`PUSHUP_DEPTH_LIMITED`** (Warning): Bottom phase elbow angle $> 100.0^\circ$. Cue: *"Lower your chest closer to the floor (aim for 90° elbow bend)."*
- **`HIP_SAG`** (Warning): Any phase hip angle $< 140.0^\circ$. Cue: *"Engage core and glutes to maintain a straight plank line from shoulders to ankles."*
- **`ELBOW_ASYMMETRY`** (Warning): Active phase elbow angle difference $> 15.0^\circ$. Cue: *"Press evenly through both palms to balance chest loading."*
- **`PUSHUP_INCOMPLETE_LOCKOUT`** (Info): Top plank elbow angle $< 145.0^\circ$. Cue: *"Lock out arms smoothly at the top of the plank before the next rep."*

#### Bicep Curl Rules
- **`CURL_INCOMPLETE_FLEXION`** (Warning): Contracted phase elbow angle $> 75.0^\circ$. Cue: *"Curl dumbbell fully upward to achieve peak bicep contraction."*
- **`CURL_INCOMPLETE_EXTENSION`** (Info): Extended phase elbow angle $< 140.0^\circ$. Cue: *"Lower weight fully for a complete stretch before starting the next rep."*
- **`CURL_ASYMMETRY`** (Warning): Active phase elbow angle difference $> 20.0^\circ$. Cue: *"Sync curling speed across both arms for balanced loading."*
- **`EXCESSIVE_TORSO_SWAY`** (Warning): Curling phase shoulder-hip horizontal offset $> 0.08$ normalized units. Cue: *"Pin elbows by your sides and avoid swinging your torso to cheat the weight up."*

### 3. Feedback Stabilization & Noise Rejection
- **Confirmation Dwell Window**: Rules require 2 consecutive frames meeting fault criteria before a finding is confirmed, preventing single-frame detector jitter from flashing warnings.
- **Repeat Cooldown Window**: A 1.8-second refractory period prevents identical findings from re-alerting immediately after resolution.
- **Stale Finding Clearing**: Once an athlete corrects their posture, the fault clears promptly.
- **State Machine Isolation**: When the athlete switches exercises or resets their session, stabilizer state resets completely.

### 4. Severity Hierarchy
- **`unavailable`**: Landmark visibility $< 0.50$ or body out of frame. Feedback reports limitations without making false accusations.
- **`warning`**: Observable kinematic alignment deviation requiring athlete correction.
- **`info`**: Guidance cue for optimal range of motion or repetition lockout.

---

## Scientific Scope & Honest Limitations
1. **Camera Angle & Parallax**: Landmark accuracy depends on camera angle, distance, lighting, and occlusion. Lateral views are recommended for squats and push-ups; frontal views are recommended for bilateral symmetry and bicep curls.
2. **Normalized Coordinates**: Speeds and distances are in normalized image space ($[0.0, 1.0]$), not physical meters or kilograms.
3. **Movement Guidance**: Form cues provide kinematic alignment observations based on joint geometry; they are **not medical advice**, clinical therapy, or injury diagnosis.

---

## How to Install and Run

### 1. Backend Setup
```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Documentation (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- WebSocket Pose & Exercise Stream: `ws://127.0.0.1:8000/ws/pose`

### 2. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
- Web Application: [http://localhost:5173](http://localhost:5173)

---

## Running Verification Tests

```powershell
cd backend
.\venv\Scripts\activate

# Stage 6: Real-Time Exercise Form Feedback & Rules
python test_stage6.py

# Stage 5: Exercise State Machines & Repetition Counting
python test_stage5.py

# Stage 4: Biomechanics Engine
python test_stage4.py

# Stage 3: Computer Vision & WebSocket
python test_stage3.py

# Stage 2: Database Models & Authentication
python test_stage2.py
```

Frontend Typecheck & Build:
```powershell
cd frontend
npx tsc --noEmit
npm run build
```
=======
# AthletiQ
>>>>>>> 940414605a126f3b950b7b5ce48ec05393c20d94
