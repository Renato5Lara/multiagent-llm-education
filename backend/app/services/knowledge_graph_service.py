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
    existing_nodes = {
        n.external_id: n
        for n in db.query(KnowledgeNode)
        .filter(KnowledgeNode.node_type == "institutional_course")
        .all()
        if n.external_id
    }
    for course in courses:
        if course.id in existing_nodes:
            continue
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
    nodes = {
        n.external_id: n
        for n in db.query(KnowledgeNode)
        .filter(KnowledgeNode.node_type == "institutional_course")
        .all()
        if n.external_id
    }
    existing_edges = {
        (e.source_id, e.target_id)
        for e in db.query(KnowledgeEdge)
        .filter(KnowledgeEdge.relationship_type == "prerequisite")
        .all()
    }
    for prereq in prereqs:
        source = nodes.get(prereq.prerequisite_id)
        target = nodes.get(prereq.course_id)
        if source and target and (source.id, target.id) not in existing_edges:
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
    existing_nodes = {
        n.external_id: n
        for n in db.query(KnowledgeNode)
        .filter(KnowledgeNode.node_type == "competency")
        .all()
        if n.external_id
    }
    for comp in competencies:
        if comp.id in existing_nodes:
            continue
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

    course_nodes = {
        n.external_id: n
        for n in db.query(KnowledgeNode)
        .filter(KnowledgeNode.node_type == "institutional_course")
        .all()
        if n.external_id
    }
    comp_nodes = {
        n.external_id: n
        for n in db.query(KnowledgeNode)
        .filter(KnowledgeNode.node_type == "competency")
        .all()
        if n.external_id
    }
    existing_edges = {
        (e.source_id, e.target_id)
        for e in db.query(KnowledgeEdge)
        .filter(KnowledgeEdge.relationship_type == "teaches")
        .all()
    }

    assocs = db.query(CourseCompetency).all()
    for assoc in assocs:
        course_node = course_nodes.get(assoc.course_id)
        comp_node = comp_nodes.get(assoc.competency_id)
        if course_node and comp_node and (course_node.id, comp_node.id) not in existing_edges:
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
    if not weaknesses:
        return []

    filters = [
        KnowledgeNode.node_type == "competency",
    ]
    if len(weaknesses) == 1:
        like_clause = KnowledgeNode.label.ilike(f"%{weaknesses[0]}%")
        filters.append(like_clause)
    else:
        from sqlalchemy import or_
        like_clauses = [KnowledgeNode.label.ilike(f"%{w}%") for w in weaknesses]
        filters.append(or_(*like_clauses))

    weak_nodes = db.query(KnowledgeNode).filter(*filters).all()

    if not weak_nodes:
        return []

    weak_node_ids = [n.id for n in weak_nodes]
    weak_node_map = {n.id: n for n in weak_nodes}

    teaching_edges = (
        db.query(KnowledgeEdge)
        .filter(
            KnowledgeEdge.target_id.in_(weak_node_ids),
            KnowledgeEdge.relationship_type == "teaches",
        )
        .all()
    )

    if not teaching_edges:
        return []

    source_ids = list({e.source_id for e in teaching_edges})
    source_nodes = {
        n.id: n.label
        for n in db.query(KnowledgeNode).filter(KnowledgeNode.id.in_(source_ids)).all()
    }

    recommendations = []
    for edge in teaching_edges:
        course_label = source_nodes.get(edge.source_id)
        if not course_label:
            continue
        node = weak_node_map.get(edge.target_id)
        if not node:
            continue
        recommendations.append({
            "course": course_label,
            "competency": node.label,
            "reason": f"Refuerza {node.label} a través de {course_label}",
        })
    return recommendations
