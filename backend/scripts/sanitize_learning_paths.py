"""
Saneamiento de LearningPath contaminados por el pipeline legado.

Contexto: antes del fix del 2026-07-20 (desacoplar Ciclo de
academic_activation_pipeline.activate_student en user_service.py), crear o
editar un estudiante con Ciclo desde Administrador disparaba la matricula
legada por malla curricular, que generaba un LearningPath de inmediato -
incluyendo, si el ciclo coincidia, uno para IS301 (Fundamentos de
Programacion) - sin que el estudiante hubiera rendido nunca el pre-test.
Como knowledge_test_service.get_test_status() exige `not has_learning_path`
para exigir el pre-test, esos estudiantes quedaron con `pretest_required`
en False para siempre.

Este script identifica, respalda y opcionalmente elimina unicamente esos
LearningPath contaminados, con criterios conservadores para no tocar nada
que pueda ser legitimo:

  1. course.code == 'IS301' (el unico curso donde el pre-test aplica)
  2. learning_path.knowledge_level IS NULL (marca del creador legado;
     generate_learning_path_adaptive, el creador moderno, siempre lo puebla)
  3. NO existe un KnowledgeTestAttempt(kind='pre', status='completed') para
     ese (student_id, course_id) - si existe, el NULL tiene otra causa y
     el candidato se excluye para revision manual, no se toca a ciegas.
  4. Ningun PathModule de esa ruta fue tocado por el estudiante (todos en
     status locked/available, sin completed_at ni score) - si el estudiante
     ya avanzo en la ruta contaminada, se excluye para revision manual.
  5. generated_at < CUTOFF (por defecto, el momento de ejecucion del script;
     con --cutoff se puede fijar una fecha exacta) - nada generado despues
     del fix puede ser legado por construccion, pero se deja como cinturon
     de seguridad adicional, no como criterio unico.

Modo por defecto: DRY RUN. Solo audita, exporta un respaldo completo de los
candidatos (con sus PathModule) a backend/backups/, y escribe un reporte.
Nada se borra hasta pasar --apply explicitamente. Tras aplicar, se
reverifica con knowledge_test_service.get_test_status() que cada estudiante
afectado quedo con pretest_required=True.

Uso (desde backend/, con el venv activado):
    python scripts/sanitize_learning_paths.py                # dry run + reporte
    python scripts/sanitize_learning_paths.py --apply         # aplica el saneamiento
    python scripts/sanitize_learning_paths.py --cutoff 2026-07-20
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.models.engagement import EngagementSession  # noqa: E402
from app.models.evaluation_attempt import EvaluationAttempt  # noqa: E402
from app.models.knowledge_test import KnowledgeTestAttempt  # noqa: E402
from app.models.learning_session import LearningSession  # noqa: E402
from app.models.student_progress import LearningPath, PathModule  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import knowledge_test_service  # noqa: E402

# Toda tabla que referencia path_modules.id por FK (ForeignKeyViolation si se
# ignora): evidencia de que el estudiante SI interactuo con el modulo, aunque
# su status/score/completed_at sigan en el valor por defecto.
MODULE_REFERENCING_MODELS = [EvaluationAttempt, EngagementSession, LearningSession]

BACKUPS_DIR = ROOT / "backups"
ANCHOR_COURSE_CODE = "IS301"


def find_candidates(db, cutoff: datetime) -> tuple[list[dict], list[dict]]:
    """Devuelve (aceptados, excluidos). Cada elemento trae toda la evidencia
    usada para decidir, no solo el id."""
    rows = (
        db.query(LearningPath, Course, User)
        .join(Course, Course.id == LearningPath.course_id)
        .join(User, User.id == LearningPath.student_id)
        .filter(
            Course.code == ANCHOR_COURSE_CODE,
            LearningPath.knowledge_level.is_(None),
            LearningPath.generated_at < cutoff,
        )
        .all()
    )

    accepted, excluded = [], []
    for path, course, student in rows:
        modules = db.query(PathModule).filter(PathModule.path_id == path.id).all()
        pre_completed = (
            db.query(KnowledgeTestAttempt)
            .filter(
                KnowledgeTestAttempt.student_id == student.id,
                KnowledgeTestAttempt.course_id == course.id,
                KnowledgeTestAttempt.kind == "pre",
                KnowledgeTestAttempt.status == "completed",
            )
            .first()
        )
        touched_modules = [
            m for m in modules
            if m.status not in ("locked", "available") or m.completed_at is not None or m.score is not None
        ]
        module_ids = [m.id for m in modules]
        referenced_elsewhere = []
        if module_ids:
            for model in MODULE_REFERENCING_MODELS:
                hit = db.query(model.module_id).filter(model.module_id.in_(module_ids)).first()
                if hit is not None:
                    referenced_elsewhere.append(model.__tablename__)

        record = {
            "learning_path_id": path.id,
            "student_id": student.id,
            "student_email": student.email,
            "course_id": course.id,
            "course_code": course.code,
            "generated_at": path.generated_at.isoformat(),
            "total_modules": path.total_modules,
            "module_ids": [m.id for m in modules],
            "reason_excluded": None,
        }

        if pre_completed is not None:
            record["reason_excluded"] = (
                f"tiene un KnowledgeTestAttempt pre completado (attempt_id={pre_completed.id}) "
                "pese a knowledge_level NULL: el NULL no es del origen legado esperado, requiere revision manual"
            )
            excluded.append(record)
            continue

        if touched_modules:
            record["reason_excluded"] = (
                f"{len(touched_modules)} modulo(s) de la ruta ya fueron tocados por el estudiante "
                "(status/completed_at/score): no es una ruta huerfana, requiere revision manual"
            )
            excluded.append(record)
            continue

        if referenced_elsewhere:
            record["reason_excluded"] = (
                f"modulo(s) referenciados desde {', '.join(referenced_elsewhere)}: "
                "hay evidencia de interaccion aunque status/score/completed_at sigan en su valor por defecto"
            )
            excluded.append(record)
            continue

        accepted.append(record)

    return accepted, excluded


def export_backup(accepted: list[dict], excluded: list[dict], stamp: str) -> Path:
    BACKUPS_DIR.mkdir(exist_ok=True)
    backup_path = BACKUPS_DIR / f"learning_path_sanitization_{stamp}.json"
    with backup_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "anchor_course_code": ANCHOR_COURSE_CODE,
                "candidates_accepted": accepted,
                "candidates_excluded": excluded,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    return backup_path


def apply_deletion(db, accepted: list[dict]) -> None:
    try:
        for record in accepted:
            db.query(PathModule).filter(PathModule.path_id == record["learning_path_id"]).delete()
            db.query(LearningPath).filter(LearningPath.id == record["learning_path_id"]).delete()
        db.commit()
    except Exception:
        db.rollback()
        print("\n*** Fallo el borrado, se hizo rollback completo: no se elimino nada. ***", file=sys.stderr)
        raise


def verify(db, accepted: list[dict]) -> list[dict]:
    results = []
    for record in accepted:
        status = knowledge_test_service.get_test_status(db, record["student_id"], record["course_id"])
        results.append({
            "student_email": record["student_email"],
            "pretest_required_now": status["pretest_required"],
            "has_learning_path_now": status["has_learning_path"],
            "ok": status["pretest_required"] is True and status["has_learning_path"] is False,
        })
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Aplica el borrado. Sin esto, solo audita y respalda (dry run).")
    parser.add_argument("--cutoff", type=str, default=None, help="Fecha ISO (YYYY-MM-DD). Por defecto: ahora.")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc)
    if args.cutoff:
        cutoff = datetime.fromisoformat(args.cutoff).replace(tzinfo=timezone.utc)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    db = SessionLocal()
    try:
        accepted, excluded = find_candidates(db, cutoff)

        print(f"=== Saneamiento de LearningPath contaminados (curso {ANCHOR_COURSE_CODE}) ===")
        print(f"Cutoff: {cutoff.isoformat()}")
        print(f"Candidatos a eliminar (huerfanos, sin pre-test, sin avance): {len(accepted)}")
        print(f"Excluidos para revision manual: {len(excluded)}")
        for record in excluded:
            print(f"  - EXCLUIDO {record['student_email']}: {record['reason_excluded']}")

        backup_path = export_backup(accepted, excluded, stamp)
        print(f"\nRespaldo completo escrito en: {backup_path}")

        if not args.apply:
            print("\nDRY RUN: no se elimino nada. Ejecuta con --apply para aplicar el saneamiento.")
            return

        if not accepted:
            print("\nNada que aplicar (0 candidatos aceptados).")
            return

        apply_deletion(db, accepted)
        print(f"\nEliminados {len(accepted)} LearningPath contaminados (y sus PathModule).")

        verification = verify(db, accepted)
        report_path = BACKUPS_DIR / f"learning_path_sanitization_{stamp}_verification.json"
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(verification, f, indent=2, ensure_ascii=False)

        n_ok = sum(1 for v in verification if v["ok"])
        print(f"Verificacion post-saneamiento: {n_ok}/{len(verification)} estudiantes con pretest_required=True")
        for v in verification:
            if not v["ok"]:
                print(f"  ** REVISAR: {v['student_email']} -> {v}")
        print(f"Reporte de verificacion: {report_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
