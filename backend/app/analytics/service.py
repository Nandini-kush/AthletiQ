"""
AthletiQ Stage 7 — Analytics Service.
Coordinates database queries, progress calculations, and athlete analytics reports.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.session import ExerciseSession
from app.analytics.metrics import (
    calculate_pace_rpm,
    compare_sessions,
    SCIENTIFIC_DISCLAIMER,
)
from app.analytics.schemas import (
    AthleteOverviewResponse,
    PerExerciseSummary,
    ExerciseProgressResponse,
    ExerciseProgressPoint,
    SessionAnalyticsResponse,
    JointAngleStat,
    SymmetryStat,
    FormFeedbackSummary,
    DataQualitySummary,
    BaselineComparison,
)

class AnalyticsService:

    @staticmethod
    def _apply_time_filter(query, time_filter: str):
        now = datetime.now(timezone.utc)
        if time_filter == "7d":
            cutoff = now - timedelta(days=7)
            return query.filter(ExerciseSession.started_at >= cutoff)
        elif time_filter == "30d":
            cutoff = now - timedelta(days=30)
            return query.filter(ExerciseSession.started_at >= cutoff)
        return query

    @classmethod
    def get_athlete_overview(cls, db: Session, athlete_id: int) -> AthleteOverviewResponse:
        """
        Produce a high-level performance overview across all sessions for an athlete.
        """
        sessions = (
            db.query(ExerciseSession)
            .filter(ExerciseSession.athlete_id == athlete_id)
            .order_by(ExerciseSession.started_at.desc())
            .all()
        )

        if not sessions:
            return AthleteOverviewResponse(
                total_sessions=0,
                total_repetitions=0,
                total_duration_seconds=0,
                most_frequent_exercise=None,
                exercises_practiced=[],
                per_exercise_summary={},
                recent_sessions=[]
            )

        total_sessions = len(sessions)
        total_repetitions = sum(s.total_repetitions for s in sessions)
        total_duration_seconds = sum(s.duration for s in sessions)

        # Per-exercise breakdown
        exercise_counts: Dict[str, int] = {}
        exercise_reps: Dict[str, int] = {}
        exercise_duration: Dict[str, int] = {}
        exercise_paces: Dict[str, List[float]] = {}
        exercise_last_date: Dict[str, datetime] = {}

        for s in sessions:
            name = s.exercise_name
            exercise_counts[name] = exercise_counts.get(name, 0) + 1
            exercise_reps[name] = exercise_reps.get(name, 0) + s.total_repetitions
            exercise_duration[name] = exercise_duration.get(name, 0) + s.duration
            
            pace = s.avg_pace_rpm or calculate_pace_rpm(s.total_repetitions, s.duration)
            if pace is not None:
                exercise_paces.setdefault(name, []).append(pace)

            if name not in exercise_last_date or s.started_at > exercise_last_date[name]:
                exercise_last_date[name] = s.started_at

        # Most frequent exercise
        most_frequent = max(exercise_counts, key=exercise_counts.get) if exercise_counts else None

        per_exercise: Dict[str, PerExerciseSummary] = {}
        for name, count in exercise_counts.items():
            paces = exercise_paces.get(name, [])
            avg_pace = round(sum(paces) / len(paces), 2) if paces else None
            per_exercise[name] = PerExerciseSummary(
                exercise_name=name,
                total_sessions=count,
                total_repetitions=exercise_reps[name],
                total_duration_seconds=exercise_duration[name],
                avg_pace_rpm=avg_pace,
                last_performed_at=exercise_last_date.get(name)
            )

        # Recent 5 sessions
        recent = []
        for s in sessions[:5]:
            pace = s.avg_pace_rpm or calculate_pace_rpm(s.total_repetitions, s.duration)
            recent.append({
                "id": s.id,
                "exercise_name": s.exercise_name,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "duration": s.duration,
                "total_repetitions": s.total_repetitions,
                "avg_pace_rpm": pace,
            })

        return AthleteOverviewResponse(
            total_sessions=total_sessions,
            total_repetitions=total_repetitions,
            total_duration_seconds=total_duration_seconds,
            most_frequent_exercise=most_frequent,
            exercises_practiced=list(exercise_counts.keys()),
            per_exercise_summary=per_exercise,
            recent_sessions=recent
        )

    @classmethod
    def get_exercise_progress(
        cls,
        db: Session,
        athlete_id: int,
        exercise_name: str,
        time_filter: str = "all"
    ) -> ExerciseProgressResponse:
        """
        Retrieve chronological progression points for a specific exercise.
        """
        query = (
            db.query(ExerciseSession)
            .filter(
                ExerciseSession.athlete_id == athlete_id,
                ExerciseSession.exercise_name.ilike(exercise_name)
            )
        )
        query = cls._apply_time_filter(query, time_filter)
        sessions = query.order_by(ExerciseSession.started_at.asc()).all()

        if not sessions:
            return ExerciseProgressResponse(
                exercise_name=exercise_name,
                total_sessions=0,
                total_repetitions=0,
                avg_pace_rpm=None,
                best_pace_rpm=None,
                avg_primary_rom_deg=None,
                time_filter_applied=time_filter,
                history=[],
                baseline_summary="No sessions found for this exercise in the selected timeframe."
            )

        history: List[ExerciseProgressPoint] = []
        paces: List[float] = []
        primary_roms: List[float] = []

        # Determine primary joint for exercise
        ex_lower = exercise_name.lower()
        primary_joint_key = "knee" if "squat" in ex_lower else ("elbow" if ("push" in ex_lower or "curl" in ex_lower) else None)

        for s in sessions:
            pace = s.avg_pace_rpm or calculate_pace_rpm(s.total_repetitions, s.duration)
            if pace is not None:
                paces.append(pace)

            # Extract primary ROM
            metrics = s.summary_metrics or {}
            rom_stats = metrics.get("rom_stats", {})
            rom_val = None
            if primary_joint_key:
                rom_val = rom_stats.get(primary_joint_key) or rom_stats.get(f"{primary_joint_key}_rom")
                if rom_val is not None:
                    try:
                        rom_val = float(rom_val)
                        primary_roms.append(rom_val)
                    except (ValueError, TypeError):
                        rom_val = None

            history.append(ExerciseProgressPoint(
                session_id=s.id,
                date=s.started_at,
                repetitions=s.total_repetitions,
                duration_seconds=s.duration,
                pace_rpm=pace,
                primary_rom_deg=rom_val
            ))

        avg_pace = round(sum(paces) / len(paces), 2) if paces else None
        best_pace = round(max(paces), 2) if paces else None
        avg_rom = round(sum(primary_roms) / len(primary_roms), 1) if primary_roms else None

        # Baseline comparison between first and latest session
        baseline_summary = None
        if len(sessions) > 1:
            first = sessions[0]
            latest = sessions[-1]
            rep_diff = latest.total_repetitions - first.total_repetitions
            pace_first = first.avg_pace_rpm or calculate_pace_rpm(first.total_repetitions, first.duration)
            pace_latest = latest.avg_pace_rpm or calculate_pace_rpm(latest.total_repetitions, latest.duration)
            pace_diff = round(pace_latest - pace_first, 2) if (pace_latest is not None and pace_first is not None) else None

            parts = [f"Baseline set from first session on {first.started_at.strftime('%Y-%m-%d')}"]
            if rep_diff != 0:
                parts.append(f"{rep_diff:+d} reps in latest session")
            if pace_diff is not None:
                parts.append(f"{pace_diff:+.1f} rpm cadence change")
            baseline_summary = ". ".join(parts) + "."
        else:
            baseline_summary = "Single session recorded. Additional sessions will unlock longitudinal trend comparisons."

        return ExerciseProgressResponse(
            exercise_name=exercise_name,
            total_sessions=len(sessions),
            total_repetitions=sum(s.total_repetitions for s in sessions),
            avg_pace_rpm=avg_pace,
            best_pace_rpm=best_pace,
            avg_primary_rom_deg=avg_rom,
            time_filter_applied=time_filter,
            history=history,
            baseline_summary=baseline_summary
        )

    @classmethod
    def get_session_analytics(
        cls,
        db: Session,
        athlete_id: int,
        session_id: int
    ) -> Optional[SessionAnalyticsResponse]:
        """
        Retrieve comprehensive performance analytics for a single exercise session.
        """
        session = (
            db.query(ExerciseSession)
            .filter(
                ExerciseSession.id == session_id,
                ExerciseSession.athlete_id == athlete_id
            )
            .first()
        )

        if not session:
            return None

        pace = session.avg_pace_rpm or calculate_pace_rpm(session.total_repetitions, session.duration)

        metrics = session.summary_metrics or {}
        
        # Parse JointAngleStat objects
        raw_joint_stats = metrics.get("joint_angle_stats", {})
        joint_angle_stats: Dict[str, JointAngleStat] = {}
        for joint, stat in raw_joint_stats.items():
            if isinstance(stat, dict):
                joint_angle_stats[joint] = JointAngleStat(
                    min=stat.get("min", 0.0),
                    max=stat.get("max", 0.0),
                    mean=stat.get("mean", 0.0),
                    rom=stat.get("rom", 0.0),
                    sample_count=stat.get("sample_count", 0)
                )

        # Parse ROM stats
        rom_stats = metrics.get("rom_stats", {})

        # Parse Symmetry
        raw_sym = metrics.get("symmetry_stats")
        symmetry = None
        if raw_sym and isinstance(raw_sym, dict):
            symmetry = SymmetryStat(
                avg_symmetry_score=raw_sym.get("avg_symmetry_score"),
                knee_diff_deg=raw_sym.get("knee_diff_deg") or raw_sym.get("avg_knee_diff_deg"),
                elbow_diff_deg=raw_sym.get("elbow_diff_deg") or raw_sym.get("avg_elbow_diff_deg"),
                observation=raw_sym.get("observation")
            )

        # Parse Form Summary
        raw_form = metrics.get("form_summary")
        form_summary = None
        if raw_form and isinstance(raw_form, dict):
            form_summary = FormFeedbackSummary(
                total_findings=raw_form.get("total_findings", 0),
                total_warnings=raw_form.get("total_warnings", 0),
                total_infos=raw_form.get("total_infos", 0),
                finding_counts=raw_form.get("finding_counts", {}),
                primary_cues=raw_form.get("primary_cues", [])
            )

        # Parse Data Quality
        raw_quality = metrics.get("data_quality")
        data_quality = None
        if raw_quality and isinstance(raw_quality, dict):
            data_quality = DataQualitySummary(
                valid_frames=raw_quality.get("valid_frames", 0),
                total_frames=raw_quality.get("total_frames", 0),
                tracking_ratio=raw_quality.get("tracking_ratio", 0.0),
                limitations=raw_quality.get("limitations", [])
            )

        # Compare with immediately preceding session of the same exercise
        previous_session = (
            db.query(ExerciseSession)
            .filter(
                ExerciseSession.athlete_id == athlete_id,
                ExerciseSession.exercise_name == session.exercise_name,
                ExerciseSession.started_at < session.started_at
            )
            .order_by(ExerciseSession.started_at.desc())
            .first()
        )

        comparison_raw = compare_sessions(session, previous_session)
        baseline_comparison = None
        if comparison_raw:
            baseline_comparison = BaselineComparison(
                baseline_session_id=comparison_raw["baseline_session_id"],
                baseline_date=comparison_raw["baseline_date"],
                rep_diff=comparison_raw["rep_diff"],
                duration_diff_sec=comparison_raw["duration_diff_sec"],
                pace_diff_rpm=comparison_raw["pace_diff_rpm"],
                rom_diff_deg=comparison_raw["rom_diff_deg"],
                summary_note=comparison_raw["summary_note"]
            )

        return SessionAnalyticsResponse(
            session_id=session.id,
            exercise_name=session.exercise_name,
            started_at=session.started_at,
            ended_at=session.ended_at,
            duration_seconds=session.duration,
            total_repetitions=session.total_repetitions,
            pace_rpm=pace,
            joint_angle_stats=joint_angle_stats,
            rom_stats=rom_stats,
            symmetry=symmetry,
            form_summary=form_summary,
            data_quality=data_quality,
            baseline_comparison=baseline_comparison,
            scientific_disclaimer=SCIENTIFIC_DISCLAIMER
        )

    @classmethod
    def get_filtered_sessions(
        cls,
        db: Session,
        athlete_id: int,
        exercise_name: Optional[str] = None,
        time_filter: str = "all",
        limit: int = 50,
        offset: int = 0
    ) -> List[ExerciseSession]:
        """
        Query sessions with optional exercise, timeframe, and pagination filters.
        """
        query = db.query(ExerciseSession).filter(ExerciseSession.athlete_id == athlete_id)
        if exercise_name:
            query = query.filter(ExerciseSession.exercise_name.ilike(f"%{exercise_name}%"))
        query = cls._apply_time_filter(query, time_filter)
        return query.order_by(ExerciseSession.started_at.desc()).offset(offset).limit(limit).all()
