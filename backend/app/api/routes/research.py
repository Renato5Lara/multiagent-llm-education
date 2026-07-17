"""
Endpoints del Dashboard del Investigador (Modo Evidencia).

Misma política de acceso que /api/evidence: sin autenticación, pensado para
la sustentación. Expone solo agregados e identificadores — todas las métricas
salen de tablas persistidas por el flujo real, sin datos simulados.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import research_dashboard_service, research_export_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["Investigación"])


@router.get("/summary")
def get_summary(
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return research_dashboard_service.get_research_summary(db, course_id)


@router.get("/students")
def get_students(
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    rows = research_dashboard_service.get_student_result_rows(db, course_id)
    return {"total": len(rows), "rows": rows}


@router.get("/export")
def export_results(
    fmt: str = "csv",
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
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
