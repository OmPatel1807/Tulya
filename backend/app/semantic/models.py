"""
models.py - Data Models for Phase Loop 5 (Semantic Comparison & Grounded Auditing).
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SemanticCategory(str, Enum):
    """Substantive discrepancy categories in legal effect."""
    MODALITY = "MODALITY"       # Mandatory vs discretionary shift (shall vs may, करेगा vs कर सकेगा)
    OMISSION = "OMISSION"       # Legal right, obligation, or qualification absent in one version
    ADDITION = "ADDITION"       # Requirement or qualification present only in one version
    SCOPE = "SCOPE"             # Difference in applicability, authority, jurisdiction, or entity scope
    DEFINITION = "DEFINITION"   # Substantive variation in a defined statutory term
    REORDERED = "REORDERED"     # Provision misplaced or moved to another section (not omitted)
    FACT_LEAK = "FACT_LEAK"     # Numerical or factual entity variance identified in semantic stage


class SemanticSeverity(str, Enum):
    """Severity ranking of legal impact."""
    HIGH = "HIGH"       # Changes legal obligation, penalty, right, or jurisdiction
    MEDIUM = "MEDIUM"   # Alters procedural timeframe, discretion, or non-critical condition
    LOW = "LOW"         # Minor stylistic or framing divergence without major enforcement impact


class SemanticFinding(BaseModel):
    """A single grounded semantic difference between English and Hindi clauses."""
    category: SemanticCategory = Field(..., description="Category of substantive legal divergence")
    severity: SemanticSeverity = Field(..., description="Severity of legal impact (HIGH/MEDIUM/LOW)")
    explanation: str = Field(..., description="One-sentence explanation of how legal effect changes")
    quote_en: Optional[str] = Field(None, description="Exact substring from English clause (null if missing)")
    quote_hi: Optional[str] = Field(None, description="Exact substring from Hindi clause (null if missing)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")


class SemanticComparisonResult(BaseModel):
    """Aggregate result of semantic analysis for an aligned pair or unaligned clause."""
    en_path: Optional[str] = None
    hi_path: Optional[str] = None
    en_text: str = ""
    hi_text: str = ""
    findings: List[SemanticFinding] = Field(default_factory=list)
    discarded_findings: List[SemanticFinding] = Field(default_factory=list)
    is_reordered: bool = False
    reordered_target_path: Optional[str] = None
    raw_response: Optional[str] = None
    prompt_version: str = "v1"
    provider: str = "gemini"
    model: str = "gemini-3.8-flash"
    tokens_prompt: int = 0
    tokens_completion: int = 0
    cached: bool = False
    json_retry_performed: bool = False
