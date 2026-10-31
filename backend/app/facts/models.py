"""
models.py - Data models for Phase Loop 4 Fact Extraction and Comparison.
Represents factual units (numbers, money, duration, area/length, multipliers, dates,
section references) and discrepancies across bilingual legal clauses.
"""

from enum import Enum
from typing import List, Optional, Any, Dict, Tuple
from pydantic import BaseModel, Field


class FactType(str, Enum):
    NUMBER = "NUMBER"
    PERCENT = "PERCENT"
    MONEY = "MONEY"
    DURATION = "DURATION"
    AREA_LENGTH = "AREA_LENGTH"
    MULTIPLIER = "MULTIPLIER"
    DATE = "DATE"
    SECTION_REF = "SECTION_REF"


class FactSpan(BaseModel):
    """
    Represents an extracted factual entity with character offsets and normalized value.
    """
    fact_type: FactType
    raw_text: str
    normalized_value: Any = Field(..., description="Canonical value (number, date string, or composite dict)")
    unit: Optional[str] = Field(None, description="Canonical unit, e.g. 'INR', 'day', 'acre', 'km', '%'")
    start_char: int
    end_char: int

    def is_equivalent(self, other: "FactSpan", tol: float = 1e-5) -> bool:
        """
        Tests if two FactSpans represent the same factual entity, accounting for numeric tolerance.
        """
        if self.fact_type != other.fact_type:
            return False

        # Compare units if present
        if self.unit != other.unit:
            return False

        # Compare normalized values
        val_a = self.normalized_value
        val_b = other.normalized_value

        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            return abs(val_a - val_b) <= tol

        if isinstance(val_a, dict) and isinstance(val_b, dict):
            if set(val_a.keys()) != set(val_b.keys()):
                return False
            for k in val_a:
                v_a = val_a[k]
                v_b = val_b[k]
                if isinstance(v_a, (int, float)) and isinstance(v_b, (int, float)):
                    if abs(v_a - v_b) > tol:
                        return False
                elif v_a != v_b:
                    return False
            return True

        return val_a == val_b


class FactDifference(BaseModel):
    """
    Represents a factual difference or omission detected between English and Hindi.
    """
    fact_type: FactType
    status: str = Field(..., description="'VALUE_MISMATCH', 'UNIT_MISMATCH', 'MISSING_IN_HI', 'MISSING_IN_EN'")
    en_fact: Optional[FactSpan] = None
    hi_fact: Optional[FactSpan] = None
    description: str
    evidence_en: str = ""
    evidence_hi: str = ""
    needs_semantic_stage: bool = Field(False, description="True for cases like 'ten times tax' vs 'tax plus ten times tax'")


class FactComparisonResult(BaseModel):
    """
    Outcome of comparing all facts extracted from an English-Hindi clause pair.
    """
    clause_path_en: Optional[str] = None
    clause_path_hi: Optional[str] = None
    en_facts: List[FactSpan] = Field(default_factory=list)
    hi_facts: List[FactSpan] = Field(default_factory=list)
    matched_pairs: List[Tuple[FactSpan, FactSpan]] = Field(default_factory=list)
    differences: List[FactDifference] = Field(default_factory=list)

    @property
    def is_consistent(self) -> bool:
        return len(self.differences) == 0
