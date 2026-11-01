"""
test_pipeline.py - Unit Tests for End-to-End Pipeline, Report Merge, and Grounding.

Tests:
  1. PipelineRunner single pair audit execution.
  2. Report Merge: deterministic only, LLM only, both merged.
  3. Grounding Guard (Rule R2) enforcement in merge stage.
  4. Regression suite execution and pattern verification.
"""

import pytest

from backend.app.pipeline.models import AuditCategory, AuditSource, AuditSeverity
from backend.app.pipeline.runner import PipelineRunner
from backend.app.pipeline.merge import merge_clause_findings
from backend.app.facts.models import FactComparisonResult, FactDifference, FactType, FactSpan
from backend.app.semantic.models import SemanticComparisonResult, SemanticFinding, SemanticCategory, SemanticSeverity
from backend.eval.eval_harness import evaluate_regression_cases


def test_merge_deterministic_only():
    """Verifies that purely factual differences without semantic counterparts are labeled DETERMINISTIC."""
    en_text = "The penalty shall be 500 rupees."
    hi_text = "शास्ति पाँच हजार रुपये होगी।"

    fd = FactDifference(
        fact_type=FactType.MONEY,
        status="VALUE_MISMATCH",
        description="Value mismatch in MONEY",
        evidence_en="500 rupees",
        evidence_hi="पाँच हजार रुपये"
    )
    fact_res = FactComparisonResult(differences=[fd])
    sem_res = SemanticComparisonResult(findings=[])

    valid, discarded = merge_clause_findings(fact_res, sem_res, en_text, hi_text)
    assert len(valid) == 1
    assert len(discarded) == 0
    assert valid[0].source == AuditSource.DETERMINISTIC
    assert valid[0].category == AuditCategory.NUMERIC
    assert valid[0].quote_en == "500 rupees"
    assert valid[0].quote_hi == "पाँच हजार रुपये"


def test_merge_llm_only():
    """Verifies that semantic findings without factual differences are labeled LLM."""
    en_text = "The Magistrate may grant an order."
    hi_text = "मजिस्ट्रेट आदेश देगा।"

    sf = SemanticFinding(
        category=SemanticCategory.MODALITY,
        severity=SemanticSeverity.HIGH,
        explanation="Discretionary power made mandatory in Hindi",
        quote_en="may grant",
        quote_hi="आदेश देगा",
        confidence=0.95
    )
    fact_res = FactComparisonResult(differences=[])
    sem_res = SemanticComparisonResult(findings=[sf])

    valid, discarded = merge_clause_findings(fact_res, sem_res, en_text, hi_text)
    assert len(valid) == 1
    assert valid[0].source == AuditSource.LLM
    assert valid[0].category == AuditCategory.MODALITY
    assert valid[0].quote_en == "may grant"
    assert valid[0].quote_hi == "आदेश देगा"


def test_merge_both_confirmed():
    """Verifies that overlapping fact and semantic findings are reconciled into BOTH."""
    en_text = "shall be liable to a penalty of ten times the tax."
    hi_text = "कर के अतिरिक्त दस गुना शास्ति के दायित्व के अधीन होगा।"

    fd = FactDifference(
        fact_type=FactType.MULTIPLIER,
        status="VALUE_MISMATCH",
        description="Additive syntax detected: tax plus multiplier",
        evidence_en="ten times the tax",
        evidence_hi="दस गुना शास्ति",
        needs_semantic_stage=True
    )
    sf = SemanticFinding(
        category=SemanticCategory.ADDITION,
        severity=SemanticSeverity.HIGH,
        explanation="Hindi adds an additional requirement 'कर के अतिरिक्त'",
        quote_en="ten times the tax",
        quote_hi="कर के अतिरिक्त",
        confidence=0.96
    )
    fact_res = FactComparisonResult(differences=[fd])
    sem_res = SemanticComparisonResult(findings=[sf])

    valid, discarded = merge_clause_findings(fact_res, sem_res, en_text, hi_text)
    assert len(valid) == 1
    assert valid[0].source == AuditSource.BOTH
    assert valid[0].category == AuditCategory.ADDITION


def test_merge_grounding_guard_rejection():
    """Verifies that non-verbatim hallucinated quotes are rejected under Rule R2."""
    en_text = "The authority shall forward a copy to the District Magistrate."
    hi_text = "प्राधिकारी जिला मजिस्ट्रेट को एक प्रति अग्रेषित करेगा।"

    sf = SemanticFinding(
        category=SemanticCategory.SCOPE,
        severity=SemanticSeverity.HIGH,
        explanation="Hallucinated quote test",
        quote_en="hallucinated english quote",
        quote_hi="प्राधिकारी",
        confidence=0.90
    )
    fact_res = FactComparisonResult(differences=[])
    sem_res = SemanticComparisonResult(findings=[sf])

    valid, discarded = merge_clause_findings(fact_res, sem_res, en_text, hi_text)
    assert len(valid) == 0
    assert len(discarded) == 1
    assert discarded[0].grounded is False


def test_pipeline_runner_audit_clause_pair():
    """Verifies end-to-end ClauseAuditResult generation with latency and cost tracking."""
    runner = PipelineRunner()
    res = runner.audit_clause_pair(
        case_id="test_pair_01",
        en_text="The duration shall be thirty days.",
        hi_text="अवधि तीस दिन होगी।",
        en_paths=["1.1"],
        hi_paths=["1.1"]
    )
    assert res.case_id == "test_pair_01"
    assert res.findings == []  # Clean pair
    assert res.latency_ms > 0.0
    assert res.cost_usd >= 0.0


def test_regression_cases_all_flagged():
    """Verifies that all synthetic reproductions of reported real-world patterns are flagged."""
    reg_eval = evaluate_regression_cases()
    assert reg_eval["all_flagged"] is True
    assert reg_eval["flagged_count"] == 6
