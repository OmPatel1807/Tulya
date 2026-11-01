"""
routes_precomputed.py - Lightweight read-only router for TULYA_DEPLOY_MODE=precomputed.

In precomputed mode:
  - GET /samples           → same as live mode (full catalog)
  - POST /samples/{id}/analyze → loads a pre-built JSON report from data/processed/
  - GET /jobs/{id}         → returns job progress from in-memory store
  - GET /jobs/{id}/report  → returns the precomputed report
  - GET /jobs/{id}/export  → exports the precomputed report
  - POST /analyze          → returns HTTP 503 (live auditing disabled)

No torch, sentence-transformers, pdfplumber, pymupdf, or fonttools are imported
at module level. The heavy ingest chain is never triggered.
"""

import os
import uuid
import json
import threading
from datetime import datetime, timezone
from typing import Optional, Dict

from fastapi import APIRouter, Query, HTTPException, Response, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from backend.app.api.models import (
    JobProgress,
    JobStage,
    JobStatus,
    AuditReportResponse,
    SampleListResponse,
    LEGAL_DISCLAIMER,
)
from backend.app.api.samples import BUNDLED_SAMPLES, get_sample_by_id
from backend.app.api.export import export_as_json, export_as_csv, export_as_markdown

router = APIRouter()

_PRECOMPUTED_DIR = "data/processed"
_DEMO_NOTE = (
    "Live auditing runs in the local build. "
    "This hosted demo shows precomputed reports."
)

# ---------------------------------------------------------------------------
# Tiny in-process job store (precomputed: jobs complete instantly)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_progress: Dict[str, JobProgress] = {}
_reports: Dict[str, AuditReportResponse] = {}


def _make_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_precomputed_report(act_slug: str) -> Optional[AuditReportResponse]:
    """
    Load a pre-built report JSON from data/processed/{act_slug}.json.
    Returns None if the file does not exist.
    """
    path = os.path.join(_PRECOMPUTED_DIR, f"{act_slug}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        # The stored file is the ingest-stage processed document, not an AuditReportResponse.
        # Wrap it in a minimal AuditReportResponse shell so the frontend can render it.
        sample = get_sample_by_id(act_slug)
        job_id = f"precomputed_{act_slug}"
        return AuditReportResponse(
            job_id=job_id,
            act_slug=act_slug,
            title=sample.title if sample else act_slug.replace("_", " ").title(),
            status=JobStatus.COMPLETED,
            fallback_used=True,
            withheld=False,
            withheld_message=None,
            unreliable_pages=[],
            summary={
                "total_clauses": raw.get("stats", {}).get("total_clauses", 0),
                "findings_count": 0,
                "demo_note": _DEMO_NOTE,
                "disclaimer": LEGAL_DISCLAIMER,
            },
            findings=[],
            aligned_pairs=[],
            disclaimer=LEGAL_DISCLAIMER,
            metrics={},
        )
    except Exception as exc:
        return None


def _synthetic_completed_job(act_slug: str, job_id: str, report: AuditReportResponse) -> JobProgress:
    now = _make_now()
    return JobProgress(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        stage=JobStage.COMPLETE,
        progress_percent=100.0,
        stage_message="Precomputed report loaded.",
        error=None,
        fallback_used=True,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/samples", response_model=SampleListResponse)
def list_samples():
    """Returns catalog of bundled official Indian statutory pairs."""
    return SampleListResponse(samples=BUNDLED_SAMPLES, total=len(BUNDLED_SAMPLES))


@router.post("/samples/{sample_id}/analyze", status_code=status.HTTP_202_ACCEPTED, response_model=JobProgress)
def analyze_bundled_sample(
    sample_id: str,
    force_deterministic: bool = Query(False, description="Ignored in precomputed mode"),
):
    """
    In precomputed mode: looks up a pre-built report JSON and returns it as a
    completed job. If no precomputed report exists, returns a minimal empty report.
    """
    sample = get_sample_by_id(sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found in catalog.")

    job_id = f"precomputed_{sample.slug}"
    report = _load_precomputed_report(sample.slug)

    if report is None:
        # No precomputed JSON — return a graceful empty report
        now = _make_now()
        report = AuditReportResponse(
            job_id=job_id,
            act_slug=sample.slug,
            title=sample.title,
            status=JobStatus.COMPLETED,
            fallback_used=True,
            withheld=False,
            withheld_message=None,
            unreliable_pages=[],
            summary={
                "total_clauses": 0,
                "findings_count": 0,
                "demo_note": _DEMO_NOTE,
                "disclaimer": LEGAL_DISCLAIMER,
            },
            findings=[],
            aligned_pairs=[],
            disclaimer=LEGAL_DISCLAIMER,
            metrics={},
        )

    prog = _synthetic_completed_job(sample.slug, job_id, report)
    with _lock:
        _progress[job_id] = prog
        _reports[job_id] = report
    return prog


@router.post("/analyze", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
async def analyze_documents(
    en_file: Optional[UploadFile] = File(None),
    hi_file: Optional[UploadFile] = File(None),
    sample_id: Optional[str] = Form(None),
    act_slug: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    force_deterministic: bool = Form(False),
):
    """Live auditing is disabled in the hosted demo."""
    return JSONResponse(
        status_code=503,
        content={
            "detail": _DEMO_NOTE,
            "demo_mode": True,
        },
    )


@router.get("/jobs/{job_id}", response_model=JobProgress)
def get_job_status(job_id: str):
    with _lock:
        prog = _progress.get(job_id)
    if not prog:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return prog


@router.get("/jobs/{job_id}/report", response_model=AuditReportResponse)
def get_job_report(job_id: str):
    with _lock:
        prog = _progress.get(job_id)
        report = _reports.get(job_id)
    if not prog:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if prog.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Job is not complete.")
    if not report:
        raise HTTPException(status_code=500, detail="Report data unavailable.")
    return report


@router.get("/jobs/{job_id}/export")
def export_job_report(
    job_id: str,
    format: str = Query("json", pattern="^(json|csv|md)$"),
):
    with _lock:
        prog = _progress.get(job_id)
        report = _reports.get(job_id)
    if not prog or prog.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Job is not complete.")
    if not report:
        raise HTTPException(status_code=500, detail="Report data unavailable.")

    fmt = format.lower()
    if fmt == "csv":
        return Response(
            content=export_as_csv(report),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=tulya_{report.act_slug}_findings.csv"},
        )
    elif fmt == "md":
        return Response(
            content=export_as_markdown(report),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=tulya_{report.act_slug}_report.md"},
        )
    else:
        return Response(
            content=export_as_json(report),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=tulya_{report.act_slug}_report.json"},
        )

