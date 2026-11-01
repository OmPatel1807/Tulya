"""
models.py - Data schemas for Tulya REST API.

Defines schemas for job tracking, background progress, audit report responses,
sample catalogs, and export options.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.app.pipeline.models import AuditFinding, AuditCategory, AuditSeverity, AuditSource


LEGAL_DISCLAIMER = (
    "Tulya flags differences for human review. It does not decide or imply "
    "which version is legally authoritative, nor does it provide legal advice."
)


class JobStage(str, Enum):
    QUEUED = "QUEUED"
    INGESTION = "INGESTION"
    SEGMENTATION = "SEGMENTATION"
    ALIGNMENT = "ALIGNMENT"
    FACTS = "FACTS"
    SEMANTIC = "SEMANTIC"
    MERGE = "MERGE"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobProgress(BaseModel):
    job_id: str
    status: JobStatus
    stage: JobStage
    progress_percent: float = Field(..., ge=0.0, le=100.0)
    stage_message: str
    error: Optional[str] = None
    fallback_used: bool = False
    created_at: str
    updated_at: str


class AuditReportResponse(BaseModel):
    job_id: str
    act_slug: str
    title: str
    status: JobStatus = JobStatus.COMPLETED
    fallback_used: bool = False
    summary: Dict[str, Any]
    findings: List[AuditFinding]
    aligned_pairs: List[Dict[str, Any]] = Field(default_factory=list)
    disclaimer: str = LEGAL_DISCLAIMER
    metrics: Dict[str, Any] = Field(default_factory=dict)


class SampleItem(BaseModel):
    id: str
    title: str
    slug: str
    category: str
    pages_en: int
    pages_hi: int
    description: str
    has_reported_issues: bool = False
    highlighted_issues: List[str] = Field(default_factory=list)


class SampleListResponse(BaseModel):
    samples: List[SampleItem]
    total: int

