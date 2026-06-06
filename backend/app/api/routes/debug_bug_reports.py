"""
Debug router for inspecting bug reports at runtime.

Endpoints:
    GET  /api/debug/bug-reports       — list all bug reports
    GET  /api/debug/bug-reports/stats — aggregate statistics
    GET  /api/debug/bug-reports/{id}  — get a single report
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.bug_reports import BugReportGenerator, BugStatus

router = APIRouter(prefix="/api/debug", tags=["Debug"])

_generator = BugReportGenerator()


@router.get("/bug-reports")
def list_bug_reports(
    status: str | None = Query(None, description="Filter by status (open, fixed, verified, regression)"),
):
    if status:
        try:
            s = BugStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        reports = _generator.list_all(status=s)
    else:
        reports = _generator.list_all()

    return {
        "count": len(reports),
        "reports": [
            {
                "bug_id": r.bug_id,
                "title": r.title,
                "severity": r.severity.value if hasattr(r.severity, "value") else r.severity,
                "status": r.status.value if hasattr(r.status, "value") else r.status,
                "category": r.category.value if hasattr(r.category, "value") else r.category,
                "created_at": r.metadata.created_at,
            }
            for r in reports
        ],
    }


@router.get("/bug-reports/stats")
def bug_report_stats():
    return _generator.stats()


@router.get("/bug-reports/{bug_id}")
def get_bug_report(bug_id: str):
    report = _generator.get(bug_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Bug report {bug_id} not found")
    return {
        "bug_id": report.bug_id,
        "title": report.title,
        "severity": report.severity.value if hasattr(report.severity, "value") else report.severity,
        "status": report.status.value if hasattr(report.status, "value") else report.status,
        "category": report.category.value if hasattr(report.category, "value") else report.category,
        "symptoms": report.symptoms,
        "root_cause": report.root_cause,
        "reproduction_flow": report.reproduction_flow,
        "architectural_risk": report.architectural_risk,
        "swarm_impact": report.swarm_impact,
        "adaptation_impact": report.adaptation_impact,
        "consensus_impact": report.consensus_impact,
        "resilience_impact": report.resilience_impact,
        "shared_memory_impact": report.shared_memory_impact,
        "fix": {
            "description": report.fix.description if report.fix else None,
            "commit_hash": report.fix.commit_hash if report.fix else None,
        } if report.fix else None,
        "metadata": {
            "created_at": report.metadata.created_at,
            "updated_at": report.metadata.updated_at,
            "trace_id": report.metadata.trace_id,
            "correlation_id": report.metadata.correlation_id,
            "anomaly_id": report.metadata.anomaly_id,
        },
        "affected_files": report.affected_files,
        "tests": [{"name": t.name, "status": t.status} for t in report.tests],
        "markdown_path": report.markdown_path,
    }
