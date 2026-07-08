"""
Agregados del Dashboard del Investigador (Research & Experiment Layer).

Todas las métricas salen de tablas persistidas por el flujo real del
estudiante — cero datos simulados: knowledge_test_attempts,
experiment_results, learning_paths, research_metrics, student_profiles,
learning_sessions y courses.
"""

import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.knowledge_test import KnowledgeTestAttempt
from app.models.learning_session import LearningSession
from app.models.research import ExperimentResult, ResearchMetric
from app.models.student_profile import StudentProfile
from app.models.student_progress import LearningPath
from app.services.research_metrics_service import (
    AI_ORCHESTRATION_MS,
    PATH_GENERATION_MS,
    TUTOR_LATENCY_MS,
    TUTOR_MESSAGE,
)

logger = logging.getLogger(__name__)

GROUP_LABEL = "Experimental"


def _completed_attempts(db: Session, kind: str, course_id: Optional[str]):
    q = db.query(KnowledgeTestAttempt).filter(
        KnowledgeTestAttempt.kind == kind,
        KnowledgeTestAttempt.status == "completed",
    )
    if course_id:
        q = q.filter(KnowledgeTestAttempt.course_id == course_id)
    return q


def _level_distribution(db: Session, kind: str, course_id: Optional[str]) -> dict:
    q = (
        db.query(KnowledgeTestAttempt.level, func.count(KnowledgeTestAttempt.id))
        .filter(
            KnowledgeTestAttempt.kind == kind,
            KnowledgeTestAttempt.status == "completed",
        )
        .group_by(KnowledgeTestAttempt.level)
    )
    if course_id:
        q = q.filter(KnowledgeTestAttempt.course_id == course_id)
    distribution = {"basico": 0, "intermedio": 0, "avanzado": 0}
    for level, count in q.all():
        if level in distribution:
            distribution[level] = count
    return distribution


def _avg_metric(db: Session, metric_type: str, course_id: Optional[str]) -> Optional[float]:
    q = db.query(func.avg(ResearchMetric.value)).filter(
        ResearchMetric.metric_type == metric_type,
        ResearchMetric.value.isnot(None),
    )
    if course_id:
        q = q.filter(ResearchMetric.course_id == course_id)
    value = q.scalar()
    return round(float(value), 1) if value is not None else None


def get_research_summary(db: Session, course_id: Optional[str] = None) -> dict:
    pre_q = _completed_attempts(db, "pre", course_id)
    post_q = _completed_attempts(db, "post", course_id)

    n_pre = pre_q.count()
    n_post = post_q.count()

    avg_pre = pre_q.with_entities(func.avg(KnowledgeTestAttempt.percentage)).scalar()
    avg_post = post_q.with_entities(func.avg(KnowledgeTestAttempt.percentage)).scalar()
    avg_pre_duration = pre_q.with_entities(
        func.avg(KnowledgeTestAttempt.duration_seconds)
    ).scalar()
    avg_post_duration = post_q.with_entities(
        func.avg(KnowledgeTestAttempt.duration_seconds)
    ).scalar()

    gains_q = db.query(
        func.avg(ExperimentResult.absolute_gain),
        func.avg(ExperimentResult.normalized_gain),
        func.count(ExperimentResult.id),
    )
    if course_id:
        gains_q = gains_q.filter(ExperimentResult.course_id == course_id)
    avg_gain, avg_norm_gain, n_compared = gains_q.first()

    paths_q = db.query(
        func.count(LearningPath.id), func.avg(LearningPath.generation_duration_ms)
    )
    if course_id:
        paths_q = paths_q.filter(LearningPath.course_id == course_id)
    paths_generated, avg_path_ms = paths_q.first()
    if avg_path_ms is None:
        avg_path_ms = _avg_metric(db, PATH_GENERATION_MS, course_id)

    students_by_profile = {
        (style or "sin_perfil"): count
        for style, count in db.query(
            StudentProfile.dominant_style, func.count(StudentProfile.id)
        )
        .group_by(StudentProfile.dominant_style)
        .all()
    }

    tutor_messages = db.query(func.count(ResearchMetric.id)).filter(
        ResearchMetric.metric_type == TUTOR_MESSAGE
    )
    tutor_students = db.query(
        func.count(func.distinct(ResearchMetric.student_id))
    ).filter(ResearchMetric.metric_type == TUTOR_MESSAGE)
    if course_id:
        tutor_messages = tutor_messages.filter(ResearchMetric.course_id == course_id)
        tutor_students = tutor_students.filter(ResearchMetric.course_id == course_id)
    n_tutor_messages = tutor_messages.scalar() or 0
    n_tutor_students = tutor_students.scalar() or 0

    return {
        "group_label": GROUP_LABEL,
        "n_students_pretested": n_pre,
        "n_students_posttested": n_post,
        "n_compared": n_compared or 0,
        "avg_pre_pct": round(float(avg_pre), 2) if avg_pre is not None else None,
        "avg_post_pct": round(float(avg_post), 2) if avg_post is not None else None,
        "avg_absolute_gain": round(float(avg_gain), 2) if avg_gain is not None else None,
        "avg_normalized_gain": round(float(avg_norm_gain), 4)
        if avg_norm_gain is not None
        else None,
        "level_distribution_pre": _level_distribution(db, "pre", course_id),
        "level_distribution_post": _level_distribution(db, "post", course_id),
        "avg_path_generation_ms": round(float(avg_path_ms), 1)
        if avg_path_ms is not None
        else None,
        "avg_ai_orchestration_ms": _avg_metric(db, AI_ORCHESTRATION_MS, course_id),
        "avg_tutor_latency_ms": _avg_metric(db, TUTOR_LATENCY_MS, course_id),
        "avg_pre_duration_seconds": round(float(avg_pre_duration), 1)
        if avg_pre_duration is not None
        else None,
        "avg_post_duration_seconds": round(float(avg_post_duration), 1)
        if avg_post_duration is not None
        else None,
        "students_by_profile": students_by_profile,
        "paths_generated": paths_generated or 0,
        "tutor_messages_total": n_tutor_messages,
        "avg_tutor_messages_per_student": round(n_tutor_messages / n_tutor_students, 1)
        if n_tutor_students
        else 0.0,
    }


def get_student_result_rows(db: Session, course_id: Optional[str] = None) -> list[dict]:
    """Una fila por estudiante con pre-test completado — el dataset exportable
    para SPSS/RStudio/Python."""
    pre_attempts = _completed_attempts(db, "pre", course_id).all()
    if not pre_attempts:
        return []

    student_ids = [a.student_id for a in pre_attempts]

    post_by_student = {
        a.student_id: a
        for a in _completed_attempts(db, "post", course_id)
        .filter(KnowledgeTestAttempt.student_id.in_(student_ids))
        .all()
    }

    results_q = db.query(ExperimentResult).filter(
        ExperimentResult.student_id.in_(student_ids)
    )
    if course_id:
        results_q = results_q.filter(ExperimentResult.course_id == course_id)
    result_by_student = {r.student_id: r for r in results_q.all()}

    profile_by_student = {
        p.student_id: p.dominant_style
        for p in db.query(StudentProfile)
        .filter(StudentProfile.student_id.in_(student_ids))
        .all()
    }

    paths_q = db.query(LearningPath).filter(LearningPath.student_id.in_(student_ids))
    if course_id:
        paths_q = paths_q.filter(LearningPath.course_id == course_id)
    path_by_student = {p.student_id: p for p in paths_q.all()}

    # Tiempo IA por estudiante = orquestación + latencia del tutor (ms)
    ai_ms_by_student = {
        sid: float(total or 0)
        for sid, total in db.query(
            ResearchMetric.student_id, func.sum(ResearchMetric.value)
        )
        .filter(
            ResearchMetric.student_id.in_(student_ids),
            ResearchMetric.metric_type.in_([AI_ORCHESTRATION_MS, TUTOR_LATENCY_MS]),
        )
        .group_by(ResearchMetric.student_id)
        .all()
    }

    # Tiempo de estudio (learning_sessions cerradas, en minutos → segundos)
    study_seconds_by_student = {
        sid: float(total or 0) * 60
        for sid, total in db.query(
            LearningSession.student_id, func.sum(LearningSession.duration_minutes)
        )
        .filter(LearningSession.student_id.in_(student_ids))
        .group_by(LearningSession.student_id)
        .all()
    }

    course_code_by_id = {
        c.id: c.code for c in db.query(Course).filter(
            Course.id.in_({a.course_id for a in pre_attempts})
        ).all()
    }

    rows: list[dict] = []
    for pre in pre_attempts:
        sid = pre.student_id
        post = post_by_student.get(sid)
        result = result_by_student.get(sid)
        path = path_by_student.get(sid)

        study_seconds = study_seconds_by_student.get(sid, 0.0)
        total_seconds = (
            study_seconds
            + (pre.duration_seconds or 0)
            + ((post.duration_seconds or 0) if post else 0)
        )

        rows.append(
            {
                "student_id": sid,
                "group": GROUP_LABEL,
                "pre_pct": pre.percentage,
                "post_pct": post.percentage if post else None,
                "absolute_gain": result.absolute_gain if result else None,
                "normalized_gain": result.normalized_gain if result else None,
                "level": (post.level if post else pre.level),
                "pre_level": pre.level,
                "post_level": post.level if post else None,
                "path_generation_ms": path.generation_duration_ms if path else None,
                "ai_time_ms": round(ai_ms_by_student.get(sid, 0.0), 1),
                "total_time_seconds": round(total_seconds, 1),
                "profile": profile_by_student.get(sid),
                "course": course_code_by_id.get(pre.course_id, pre.course_id),
                "date": pre.completed_at.date().isoformat() if pre.completed_at else None,
            }
        )
    return rows
