"""
routes.py - FastAPI router defining Tulya REST API endpoints.

Endpoints:
  - POST /analyze: initiate audit job (via file upload or sample specification)
  - GET /jobs/{id}: query live job progress and stage status
  - GET /jobs/{id}/report: retrieve completed audit report
  - GET /jobs/{id}/export?format=json|csv|md: export findings in structured formats
  - GET /samples: list available bundled statutory acts
  - POST /samples/{id}/analyze: initiate audit on bundled sample
"""

import os
import shutil
import tempfile
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException, Response, status
from pydantic import BaseModel

from backend.app.api.models import (
    JobProgress,
    JobStatus,
    AuditReportResponse,
    SampleListResponse,
    LEGAL_DISCLAIMER
)
from backend.app.api.jobs import job_manager
from backend.app.api.samples import BUNDLED_SAMPLES, get_sample_by_id
from backend.app.api.export import export_as_json, export_as_csv, export_as_markdown

router = APIRouter()


class AnalyzeSampleRequest(BaseModel):
    sample_id: str
    force_deterministic: bool = False


@router.get("/samples", response_model=SampleListResponse)
def list_samples():
    """Returns catalog of bundled official Indian statutory pairs."""
    return SampleListResponse(
        samples=BUNDLED_SAMPLES,
        total=len(BUNDLED_SAMPLES)
    )


@router.post("/samples/{sample_id}/analyze", status_code=status.HTTP_202_ACCEPTED, response_model=JobProgress)
def analyze_bundled_sample(
    sample_id: str,
    force_deterministic: bool = Query(False, description="Run fact engine only without LLM")
):
    """Initiates an audit job on a bundled sample act."""
    sample = get_sample_by_id(sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found in catalog.")

    en_path = os.path.join("data/raw", f"{sample.slug}_en.pdf")
    hi_path = os.path.join("data/raw", f"{sample.slug}_hi.pdf")
    if not os.path.exists(en_path) or not os.path.exists(hi_path):
        raise HTTPException(status_code=404, detail=f"Bundled PDF files for sample '{sample_id}' not found on server.")

    prog = job_manager.create_job(act_slug=sample.slug)
    job_manager.process_job_async(
        job_id=prog.job_id,
        act_slug=sample.slug,
        en_path=en_path,
        hi_path=hi_path,
        force_deterministic=force_deterministic,
        title=sample.title
    )
    return prog


@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED, response_model=JobProgress)
async def analyze_documents(
    en_file: Optional[UploadFile] = File(None, description="English Act PDF"),
    hi_file: Optional[UploadFile] = File(None, description="Hindi Act PDF"),
    sample_id: Optional[str] = Form(None, description="Optional bundled sample ID"),
    act_slug: Optional[str] = Form(None, description="Slug name for uploaded Act"),
    title: Optional[str] = Form(None, description="Display title for uploaded Act"),
    force_deterministic: bool = Form(False, description="Run deterministic fact engine only")
):
    """
    Submits an asynchronous bilingual audit job.
    Accepts uploaded English & Hindi PDFs, or a sample_id.
    """
    # 1. Handle sample_id specification
    if sample_id:
        sample = get_sample_by_id(sample_id)
        if not sample:
            raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found in catalog.")
        en_path = os.path.join("data/raw", f"{sample.slug}_en.pdf")
        hi_path = os.path.join("data/raw", f"{sample.slug}_hi.pdf")
        if not os.path.exists(en_path) or not os.path.exists(hi_path):
            raise HTTPException(status_code=404, detail=f"Bundled PDF files for sample '{sample_id}' not found.")

        prog = job_manager.create_job(act_slug=sample.slug)
        job_manager.process_job_async(
            job_id=prog.job_id,
            act_slug=sample.slug,
            en_path=en_path,
            hi_path=hi_path,
            force_deterministic=force_deterministic,
            title=title or sample.title
        )
        return prog

    # 2. Handle file uploads
    if not en_file or not hi_file:
        raise HTTPException(
            status_code=400,
            detail="Both 'en_file' and 'hi_file' must be uploaded, or 'sample_id' must be specified."
        )

    # Validate non-empty uploads
    en_bytes = await en_file.read()
    hi_bytes = await hi_file.read()

    if len(en_bytes) == 0:
        raise HTTPException(status_code=400, detail="English PDF file is empty (0 bytes).")
    if len(hi_bytes) == 0:
        raise HTTPException(status_code=400, detail="Hindi PDF file is empty (0 bytes).")

    slug = act_slug or os.path.splitext(en_file.filename)[0].lower().replace(" ", "_")
    prog = job_manager.create_job(act_slug=slug)

    # Save to temp directory
    temp_dir = tempfile.mkdtemp(prefix=f"tulya_upload_{prog.job_id}_")
    temp_en = os.path.join(temp_dir, f"{slug}_en.pdf")
    temp_hi = os.path.join(temp_dir, f"{slug}_hi.pdf")

    with open(temp_en, "wb") as f_en:
        f_en.write(en_bytes)
    with open(temp_hi, "wb") as f_hi:
        f_hi.write(hi_bytes)

    job_manager.process_job_async(
        job_id=prog.job_id,
        act_slug=slug,
        en_path=temp_en,
        hi_path=temp_hi,
        force_deterministic=force_deterministic,
        title=title or slug.replace("_", " ").title()
    )

    return prog


@router.get("/jobs/{job_id}", response_model=JobProgress)
def get_job_status(job_id: str):
    """Retrieves current execution progress and stage details for a job."""
    prog = job_manager.get_progress(job_id)
    if not prog:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return prog


@router.get("/jobs/{job_id}/report", response_model=AuditReportResponse)
def get_job_report(job_id: str):
    """Retrieves the completed statutory audit report."""
    prog = job_manager.get_progress(job_id)
    if not prog:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    if prog.status == JobStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Job '{job_id}' failed during {prog.stage.value}: {prog.error}"
        )

    if prog.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job '{job_id}' is still in progress (stage: {prog.stage.value}, {prog.progress_percent:.1f}%)."
        )

    report = job_manager.get_report(job_id)
    if not report:
        raise HTTPException(status_code=500, detail=f"Report for job '{job_id}' is missing from storage.")

    return report


@router.get("/jobs/{job_id}/export")
def export_job_report(
    job_id: str,
    format: str = Query("json", pattern="^(json|csv|md)$", description="Export format: json, csv, or md")
):
    """Exports findings in json, csv, or markdown formats."""
    prog = job_manager.get_progress(job_id)
    if not prog:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    if prog.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job '{job_id}' is not yet completed. Status: {prog.status.value}"
        )

    report = job_manager.get_report(job_id)
    if not report:
        raise HTTPException(status_code=500, detail="Report data is unavailable.")

    fmt = format.lower()
    if fmt == "csv":
        csv_content = export_as_csv(report)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=tulya_{report.act_slug}_findings.csv"}
        )
    elif fmt == "md":
        md_content = export_as_markdown(report)
        return Response(
            content=md_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=tulya_{report.act_slug}_report.md"}
        )
    else:
        json_content = export_as_json(report)
        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=tulya_{report.act_slug}_report.json"}
        )
