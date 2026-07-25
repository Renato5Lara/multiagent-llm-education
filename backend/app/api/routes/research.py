"""
Endpoints del Dashboard del Investigador (Modo Evidencia).

Requiere rol admin o docente (misma audiencia documentada para el acceso a
/evidencia). Expone solo agregados e identificadores — todas las métricas
salen de tablas persistidas por el flujo real, sin datos simulados.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_or_docente, get_db
from app.models.user import User
from app.services import research_dashboard_service, research_export_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["Investigación"])


@router.get("/summary")
def get_summary(
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_docente),
):
    return research_dashboard_service.get_research_summary(db, course_id)


@router.get("/students")
def get_students(
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_docente),
):
    rows = research_dashboard_service.get_student_result_rows(db, course_id)
    return {"total": len(rows), "rows": rows}


@router.get("/cycle-aggregates")
def get_cycle_aggregates(
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_docente),
):
    """Tiempo por concepto, tasa de remediación, frecuencia de rutas
    adaptativas y distribución de profundidad — agregados en vivo sobre
    research_metrics/CYCLE_EVIDENCE, antes solo visibles en el XLSX."""
    return research_dashboard_service.get_cycle_aggregates(db, course_id)


@router.get("/students/{student_id}/cycles")
def get_student_cycles(
    student_id: str,
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_docente),
):
    """Traza de explicabilidad de un estudiante: evidencia real de cada
    ciclo, la decisión de Adaptar y una justificación generada — nunca
    texto libre, siempre derivada de los mismos campos que se muestran."""
    rows = research_dashboard_service.get_student_cycle_rows(db, student_id, course_id)
    return {"total": len(rows), "rows": rows}


@router.get("/export")
def export_results(
    fmt: str = "csv",
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_docente),
):
    if fmt not in ("csv", "xlsx"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_FORMAT", "message": "Formato soportado: csv | xlsx"},
        )

    rows = research_dashboard_service.get_student_result_rows(db, course_id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    if fmt == "xlsx":
        if not research_export_service.excel_available():
            # Degradación consciente: sin openpyxl el CSV sigue disponible
            fmt = "csv"
        else:
            summary = research_dashboard_service.get_research_summary(db, course_id)
            content = research_export_service.rows_to_xlsx(rows, summary)
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="resultados_experimento_{stamp}.xlsx"'
                },
            )

    content = research_export_service.rows_to_csv(rows)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="resultados_experimento_{stamp}.csv"'
        },
    )


@router.get("/export-experiment")
def export_experiment(
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_docente),
):
    """Exportar experimento — un clic, un archivo: resumen por estudiante,
    detalle por ciclo (modalidad diagnosticada vs. modalidad de refuerzo) y
    estadísticas descriptivas, en tres hojas del mismo XLSX. No calcula
    nada nuevo: compone get_student_result_rows + get_cycle_evidence_rows +
    get_experiment_statistics, ya usados por el resto del dashboard."""
    if not research_export_service.excel_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "XLSX_UNAVAILABLE", "message": "openpyxl no disponible en el servidor"},
        )

    summary_rows = research_dashboard_service.get_student_result_rows(db, course_id)
    cycle_rows = research_dashboard_service.get_cycle_evidence_rows(db, course_id)
    statistics = research_dashboard_service.get_experiment_statistics(db, course_id)

    content = research_export_service.experiment_to_xlsx(summary_rows, cycle_rows, statistics)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="experimento_completo_{stamp}.xlsx"'
        },
    )
