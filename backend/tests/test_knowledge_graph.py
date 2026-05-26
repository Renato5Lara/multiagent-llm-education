"""
Tests para el servicio del grafo de conocimiento académico.
"""


class TestEnsureCourseNodes:
    def test_creates_nodes_from_institutional_courses(self, db):
        from app.models.institutional_course import InstitutionalCourse
        inst = InstitutionalCourse(code="KG-101", name="Knowledge Graph 101", credits=3, cycle=1)
        db.add(inst)
        db.commit()

        from app.services.knowledge_graph_service import ensure_course_nodes
        ensure_course_nodes(db)

        from app.models.knowledge_graph import KnowledgeNode
        nodes = db.query(KnowledgeNode).filter(KnowledgeNode.node_type == "institutional_course").all()
        assert len(nodes) == 1
        assert nodes[0].label == "KG-101: Knowledge Graph 101"
        assert nodes[0].metadata_json["cycle"] == 1

    def test_idempotent_node_creation(self, db):
        from app.models.institutional_course import InstitutionalCourse
        inst = InstitutionalCourse(code="IDEM", name="Idempotent", credits=3, cycle=1)
        db.add(inst)
        db.commit()

        from app.services.knowledge_graph_service import ensure_course_nodes
        ensure_course_nodes(db)
        ensure_course_nodes(db)

        from app.models.knowledge_graph import KnowledgeNode
        count = db.query(KnowledgeNode).filter(KnowledgeNode.node_type == "institutional_course").count()
        assert count == 1


class TestEnsurePrerequisiteEdges:
    def test_creates_edges(self, db):
        from app.models.institutional_course import InstitutionalCourse, InstitutionalCoursePrerequisite
        base = InstitutionalCourse(code="BASE", name="Base Course", credits=3, cycle=1)
        adv = InstitutionalCourse(code="ADV", name="Advanced Course", credits=3, cycle=2)
        db.add(base)
        db.add(adv)
        db.flush()
        prereq = InstitutionalCoursePrerequisite(course_id=adv.id, prerequisite_id=base.id)
        db.add(prereq)
        db.commit()

        from app.services.knowledge_graph_service import ensure_prerequisite_edges
        ensure_prerequisite_edges(db)

        from app.models.knowledge_graph import KnowledgeEdge
        edges = db.query(KnowledgeEdge).filter(KnowledgeEdge.relationship_type == "prerequisite").all()
        assert len(edges) == 1
        assert edges[0].weight == 1.0

    def test_no_duplicate_edges(self, db):
        from app.models.institutional_course import InstitutionalCourse, InstitutionalCoursePrerequisite
        base = InstitutionalCourse(code="DUP", name="Duplicate Test", credits=3, cycle=1)
        adv = InstitutionalCourse(code="DUP2", name="Duplicate Test 2", credits=3, cycle=2)
        db.add(base)
        db.add(adv)
        db.flush()
        prereq = InstitutionalCoursePrerequisite(course_id=adv.id, prerequisite_id=base.id)
        db.add(prereq)
        db.commit()

        from app.services.knowledge_graph_service import ensure_prerequisite_edges
        ensure_prerequisite_edges(db)
        ensure_prerequisite_edges(db)

        from app.models.knowledge_graph import KnowledgeEdge
        count = db.query(KnowledgeEdge).filter(KnowledgeEdge.relationship_type == "prerequisite").count()
        assert count == 1


class TestEnsureCompetencyNodes:
    def test_creates_competency_nodes(self, db):
        from app.models.competency import Competency, CompetencyType
        comp = Competency(name="Analytical Thinking", description="Analyze problems",
                          competency_type=CompetencyType.INSTITUTIONAL)
        db.add(comp)
        db.commit()

        from app.services.knowledge_graph_service import ensure_competency_nodes
        ensure_competency_nodes(db)

        from app.models.knowledge_graph import KnowledgeNode
        nodes = db.query(KnowledgeNode).filter(KnowledgeNode.node_type == "competency").all()
        assert len(nodes) == 1
        assert "Analytical Thinking" in nodes[0].label


class TestGetStudentKnowledgeGraph:
    def test_returns_graph_structure(self, db, estudiante_user):
        from app.services.knowledge_graph_service import get_student_knowledge_graph
        result = get_student_knowledge_graph(db, estudiante_user)
        assert "nodes" in result
        assert "edges" in result
        assert isinstance(result["nodes"], list)
        assert isinstance(result["edges"], list)

    def test_graph_contains_completed_flag(self, db, estudiante_user):
        from app.models.institutional_course import InstitutionalCourse
        inst = InstitutionalCourse(code="FLAG", name="Flag Test", credits=3, cycle=1)
        db.add(inst)
        db.commit()

        from app.services.knowledge_graph_service import get_student_knowledge_graph
        result = get_student_knowledge_graph(db, estudiante_user)
        inst_nodes = [n for n in result["nodes"] if n["type"] == "institutional_course"]
        for node in inst_nodes:
            assert "completed" in node


class TestGetCourseRecommendationsFromGraph:
    def test_recommendations_empty_no_data(self, db):
        from app.services.knowledge_graph_service import get_course_recommendations_from_graph
        recs = get_course_recommendations_from_graph(db, ["unknown_topic"])
        assert recs == []

    def test_recommendations_found(self, db):
        from app.models.competency import Competency, CompetencyType
        from app.models.institutional_course import InstitutionalCourse
        from app.models.knowledge_graph import KnowledgeNode, KnowledgeEdge

        comp = Competency(name="Logic", description="Logic skills", competency_type=CompetencyType.INSTITUTIONAL)
        db.add(comp)
        db.flush()

        inst = InstitutionalCourse(code="LOGIC-101", name="Logic 101", credits=3, cycle=1)
        db.add(inst)
        db.flush()

        comp_node = KnowledgeNode(node_type="competency", label="Logic", external_id=comp.id)
        course_node = KnowledgeNode(node_type="institutional_course", label="Logic 101", external_id=inst.id)
        db.add(comp_node)
        db.add(course_node)
        db.flush()

        edge = KnowledgeEdge(source_id=course_node.id, target_id=comp_node.id, relationship_type="teaches")
        db.add(edge)
        db.commit()

        from app.services.knowledge_graph_service import get_course_recommendations_from_graph
        recs = get_course_recommendations_from_graph(db, ["Logic"])
        assert len(recs) >= 1
        assert "Logic" in recs[0]["competency"]
