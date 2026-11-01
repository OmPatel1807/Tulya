"""
models.py - Data Models for Tulya End-to-End Auditing Pipeline.

Defines unified AuditFinding, AuditCategory, AuditSeverity, AuditSource,
and ClauseAuditResult structures.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AuditCategory(str, Enum):
    NUMERIC = "NUMERIC"
    OMISSION = "OMISSION"
    ADDITION = "ADDITION"
    MODALITY = "MODALITY"
    SCOPE = "SCOPE"
    DEFINITION = "DEFINITION"
    REORDERED = "REORDERED"


class AuditSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AuditSource(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"  # Flagged only by deterministic fact stage
    LLM = "LLM"                      # Flagged only by LLM semantic stage
    BOTH = "BOTH"                    # Confirmed by both deterministic facts & LLM


class AuditFinding(BaseModel):
    finding_id: str = Field(description="Unique identifier for finding")
    category: AuditCategory
    source: AuditSource
    severity: AuditSeverity = AuditSeverity.HIGH
    explanation: str
    quote_en: Optional[str] = None
    quote_hi: Optional[str] = None
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    grounded: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClauseAuditResult(BaseModel):
    case_id: str
    en_paths: List[str] = Field(default_factory=list)
    hi_paths: List[str] = Field(default_factory=list)
    en_text: str
    hi_text: str
    findings: List[AuditFinding] = Field(default_factory=list)
    discarded_findings: List[AuditFinding] = Field(default_factory=list)
    fact_diff_count: int = 0
    semantic_finding_count: int = 0
    merged_finding_count: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
