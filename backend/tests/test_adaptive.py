"""
Tests para el servicio de replanificación adaptativa.

NOTA: evaluate_module_completion y check_adaptive_unlocks ahora
reciben UnitOfWork. generate_adaptive_recommendation sigue
recibiendo Session (read-only).
"""

from app.services.adaptive_service import evaluate_module_completion


def _make_path_module(db, estudiante_user, code_prefix, total_mods=2, docente_token=None, client=None):
    """Helper: crea curso, learning path y modulos para tests."""
    from app.models.student_progress import LearningPath, PathModule
    cr = client.post("/api/courses", headers={"Authorization": f"Bearer {docente_token}"}, json={
        "code": code_prefix, "name": f"Adaptive {code_prefix}", "cycle": 1, "year": 2026,
    })
    cid = cr.json()["id"]
    path = LearningPath(student_id=estudiante_user.id, course_id=cid, total_modules=total_mods,
                        completed_modules=0)
    db.add(path)
    db.flush()
    m1 = PathModule(path_id=path.id, title="Mod 1", order=1, status="available", bloom_level=2)
    db.add(m1)
    modules = [m1]
    for i in range(1, total_mods):
        m = PathModule(path_id=path.id, title=f"Mod {i+1}", order=i+1, status="locked")
        db.add(m)
        modules.append(m)
    db.commit()
    return cid, path, modules


class TestEvaluateModuleCompletion:
    def test_high_score_unlocks_next(self, test_uow, estudiante_user, docente_token, client, db):
        cid, path, modules = _make_path_module(db, estudiante_user, "ADA-HI", docente_token=docente_token, client=client)
        result = evaluate_module_completion(test_uow, estudiante_user.id, modules[0].id, 0.85)
        test_uow.commit()
        assert "unlocked" in result
        assert result["unlocked"] == "Mod 2"

    def test_medium_score_does_not_block(self, test_uow, estudiante_user, docente_token, client, db):
        cid, path, modules = _make_path_module(db, estudiante_user, "ADA-MED", docente_token=docente_token, client=client)
        result = evaluate_module_completion(test_uow, estudiante_user.id, modules[0].id, 0.5)
        test_uow.commit()
        assert result.get("unlocked") == "Mod 2"

    def test_low_score_locks_next(self, test_uow, estudiante_user, docente_token, client, db):
        cid, path, modules = _make_path_module(db, estudiante_user, "ADA-LOW", docente_token=docente_token, client=client)
        result = evaluate_module_completion(test_uow, estudiante_user.id, modules[0].id, 0.2)
        test_uow.commit()
        assert result.get("locked") is True
        assert "reject threshold" in result.get("reason", "")

    def test_module_not_found(self, test_uow, estudiante_user):
        result = evaluate_module_completion(test_uow, estudiante_user.id, "non-existent", 0.8)
        assert "error" in result

    def test_last_module_completes_path(self, test_uow, estudiante_user, docente_token, client, db):
        cid, path, modules = _make_path_module(db, estudiante_user, "ADA-LAST", total_mods=1, docente_token=docente_token, client=client)
        result = evaluate_module_completion(test_uow, estudiante_user.id, modules[0].id, 0.9)
        test_uow.commit()
        assert result.get("completed") is True


class TestCheckAdaptiveUnlocks:
    def test_no_enrollments_returns_empty(self, test_uow, estudiante_user):
        from app.services.adaptive_service import check_adaptive_unlocks
        unlocks = check_adaptive_unlocks(test_uow, estudiante_user)
        assert unlocks == []

    def test_course_not_completed_no_unlock(self, test_uow, estudiante_user, docente_token, client, db):
        from app.models.enrollment import Enrollment, EnrollmentStatus
        from app.models.student_progress import LearningPath
        cr = client.post("/api/courses", headers={"Authorization": f"Bearer {docente_token}"}, json={
            "code": "ADA-UNL", "name": "Adaptive Unlock", "cycle": 1, "year": 2026,
        })
        cid = cr.json()["id"]
        enroll = Enrollment(student_id=estudiante_user.id, course_id=cid, status=EnrollmentStatus.ACTIVO)
        db.add(enroll)
        path = LearningPath(student_id=estudiante_user.id, course_id=cid, total_modules=4,
                            completed_modules=1)
        db.add(path)
        db.commit()

        from app.services.adaptive_service import check_adaptive_unlocks
        unlocks = check_adaptive_unlocks(test_uow, estudiante_user)
        assert len(unlocks) == 0


class TestGenerateAdaptiveRecommendation:
    def test_empty_recommendation(self, db, estudiante_user):
        from app.services.adaptive_service import generate_adaptive_recommendation
        result = generate_adaptive_recommendation(db, estudiante_user)
        assert result["weak_areas"] == []
        assert result["needs_remediation"] is False
        assert "Buen progreso" in result["suggested_focus"]

    def test_recommendation_with_weakness(self, test_uow, estudiante_user, db):
        from app.services.memory_service import store_memory
        store_memory(test_uow, estudiante_user.id, "competency", "recursion", "debil", score=0.3)
        test_uow.commit()
        from app.services.adaptive_service import generate_adaptive_recommendation
        result = generate_adaptive_recommendation(db, estudiante_user)
        assert "recursion" in result["weak_areas"]
        assert result["needs_remediation"] is True
