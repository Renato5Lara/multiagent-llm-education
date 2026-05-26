import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.competency import Competency, CourseCompetency
from app.models.institutional_course import InstitutionalCourse, InstitutionalCoursePrerequisite
from app.models.knowledge_graph import KnowledgeNode, KnowledgeEdge
from app.models.user import User

logger = logging.getLogger(__name__)


def ensure_course_nodes(db: Session):
    courses = db.query(InstitutionalCourse).all()
    for course in courses:
        existing = (
            db.query(KnowledgeNode)
            .filter(
                KnowledgeNode.node_type == "institutional_course",
                KnowledgeNode.external_id == course.id,
            )
            .first()
        )
        if not existing:
            node = KnowledgeNode(
                node_type="institutional_course",
                label=f"{course.code}: {course.name}",
                description=course.competencies,
                external_id=course.id,
                metadata_json={
                    "code": course.code,
                    "credits": course.credits,
                    "cycle": course.cycle,
                },
            )
            db.add(node)
    db.commit()


def ensure_prerequisite_edges(db: Session):
    ensure_course_nodes(db)
    prereqs = db.query(InstitutionalCoursePrerequisite).all()
    for prereq in prereqs:
        source = (
            db.query(KnowledgeNode)
            .filter(
                KnowledgeNode.node_type == "institutional_course",
                KnowledgeNode.external_id == prereq.prerequisite_id,
            )
            .first()
        )
        target = (
            db.query(KnowledgeNode)
            .filter(
                KnowledgeNode.node_type == "institutional_course",
                KnowledgeNode.external_id == prereq.course_id,
            )
            .first()
        )
        if source and target:
            existing = (
                db.query(KnowledgeEdge)
                .filter(
                    KnowledgeEdge.source_id == source.id,
                    KnowledgeEdge.target_id == target.id,
                    KnowledgeEdge.relationship_type == "prerequisite",
                )
                .first()
            )
            if not existing:
                edge = KnowledgeEdge(
                    source_id=source.id,
                    target_id=target.id,
                    relationship_type="prerequisite",
                    weight=1.0,
                )
                db.add(edge)
    db.commit()


def ensure_competency_nodes(db: Session):
    competencies = db.query(Competency).all()
    for comp in competencies:
        existing = (
            db.query(KnowledgeNode)
            .filter(
                KnowledgeNode.node_type == "competency",
                KnowledgeNode.external_id == comp.id,
            )
            .first()
        )
        if not existing:
            node = KnowledgeNode(
                node_type="competency",
                label=comp.name,
                description=comp.description,
                external_id=comp.id,
                metadata_json={"competency_type": comp.competency_type.value if hasattr(comp.competency_type, 'value') else comp.competency_type},
            )
            db.add(node)
    db.commit()


def ensure_competency_course_edges(db: Session):
    ensure_competency_nodes(db)
    ensure_course_nodes(db)

    assocs = db.query(CourseCompetency).all()
    for assoc in assocs:
        course_node = (
            db.query(KnowledgeNode)
            .filter(
                KnowledgeNode.node_type == "institutional_course",
                KnowledgeNode.external_id == assoc.course_id,
            )
            .first()
        )
        comp_node = (
            db.query(KnowledgeNode)
            .filter(
                KnowledgeNode.node_type == "competency",
                KnowledgeNode.external_id == assoc.competency_id,
            )
            .first()
        )
        if course_node and comp_node:
            existing = (
                db.query(KnowledgeEdge)
                .filter(
                    KnowledgeEdge.source_id == course_node.id,
                    KnowledgeEdge.target_id == comp_node.id,
                    KnowledgeEdge.relationship_type == "teaches",
                )
                .first()
            )
            if not existing:
                edge = KnowledgeEdge(
                    source_id=course_node.id,
                    target_id=comp_node.id,
                    relationship_type="teaches",
                )
                db.add(edge)
    db.commit()


def get_student_knowledge_graph(db: Session, student: User) -> dict:
    ensure_prerequisite_edges(db)
    ensure_competency_course_edges(db)

    nodes = db.query(KnowledgeNode).all()
    edges = db.query(KnowledgeEdge).all()

    from app.models.enrollment import Enrollment
    from app.models.student_progress import StudentProgress

    completed_course_ids = set()
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
    for e in enrollments:
        if e.status.value == "completado":
            completed_course_ids.add(e.course_id)

    course_id_to_inst = {}
    courses = db.query(Course).filter(Course.institutional_course_id.isnot(None)).all()
    for c in courses:
        course_id_to_inst[c.id] = c.institutional_course_id

    completed_node_ids = set()
    for n in nodes:
        if n.node_type == "institutional_course" and n.external_id:
            for cid, inst_id in course_id_to_inst.items():
                if inst_id == n.external_id and cid in completed_course_ids:
                    completed_node_ids.add(n.id)

    return {
        "nodes": [
            {
                "id": n.id,
                "type": n.node_type,
                "label": n.label,
                "description": n.description,
                "metadata": n.metadata_json or {},
                "completed": n.id in completed_node_ids,
            }
            for n in nodes
        ],
        "edges": [
            {
                "id": e.id,
                "source": e.source_id,
                "target": e.target_id,
                "relationship": e.relationship_type,
                "weight": e.weight,
            }
            for e in edges
        ],
    }


def get_course_recommendations_from_graph(db: Session, weaknesses: list[str]) -> list[dict]:
    recommendations = []
    for weakness in weaknesses:
        weak_nodes = (
            db.query(KnowledgeNode)
            .filter(
                KnowledgeNode.node_type == "competency",
                KnowledgeNode.label.ilike(f"%{weakness}%"),
            )
            .all()
        )
        for node in weak_nodes:
            teaching_edges = (
                db.query(KnowledgeEdge)
                .filter(
                    KnowledgeEdge.target_id == node.id,
                    KnowledgeEdge.relationship_type == "teaches",
                )
                .all()
            )
            for edge in teaching_edges:
                course_node = db.query(KnowledgeNode).filter(KnowledgeNode.id == edge.source_id).first()
                if course_node:
                    recommendations.append({
                        "course": course_node.label,
                        "competency": node.label,
                        "reason": f"Refuerza {node.label} a través de {course_node.label}",
                    })
    return recommendations
