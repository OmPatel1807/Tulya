"""
runner.py - End-to-End Clause & Document Auditing Pipeline Runner.

Orchestrates:
  1. Deterministic factual entity extraction and comparison.
  2. Grounded LLM semantic comparison.
  3. Report merge and Grounding Guard enforcement.
  4. Latency and token cost tracking.
"""

import time
from typing import List, Optional, Dict, Any

from backend.app.facts.comparator import compare_clause_facts
from backend.app.facts.models import FactComparisonResult
from backend.app.semantic.client import SemanticComparatorClient
from backend.app.semantic.models import SemanticComparisonResult
from backend.app.pipeline.models import ClauseAuditResult, AuditFinding
from backend.app.pipeline.merge import merge_clause_findings


class PipelineRunner:
    """
    Unified Pipeline Runner executing factual and semantic checks,
    merging findings into clean audit reports.
    """

    def __init__(
        self,
        semantic_client: Optional[SemanticComparatorClient] = None
    ):
        self.semantic_client = semantic_client or SemanticComparatorClient()

    def audit_clause_pair(
        self,
        case_id: str,
        en_text: str,
        hi_text: str,
        en_paths: Optional[List[str]] = None,
        hi_paths: Optional[List[str]] = None
    ) -> ClauseAuditResult:
        """
        Runs the end-to-end audit for a single bilingual clause pair.
        """
        t0 = time.perf_counter()
        en_paths = en_paths or []
        hi_paths = hi_paths or []
        en_path_str = ",".join(en_paths) if en_paths else ""
        hi_path_str = ",".join(hi_paths) if hi_paths else ""

        # 1. Deterministic Fact Comparison
        fact_res: FactComparisonResult = compare_clause_facts(
            en_text=en_text,
            hi_text=hi_text,
            en_path=en_path_str,
            hi_path=hi_path_str
        )

        # 2. Grounded LLM Semantic Comparison
        semantic_res: SemanticComparisonResult = self.semantic_client.compare_clause_pair(
            en_text=en_text,
            hi_text=hi_text,
            en_path=en_path_str,
            hi_path=hi_path_str
        )

        # 3. Report Merge
        valid_findings, discarded_findings = merge_clause_findings(
            fact_res=fact_res,
            semantic_res=semantic_res,
            en_text=en_text,
            hi_text=hi_text,
            case_id=case_id
        )

        for f in valid_findings:
            f.metadata.setdefault("en_paths", en_paths)
            f.metadata.setdefault("hi_paths", hi_paths)
            if "provision_en" not in f.metadata or not f.metadata["provision_en"]:
                f.metadata["provision_en"] = " > ".join(en_paths) if en_paths else case_id
            if "provision_hi" not in f.metadata or not f.metadata["provision_hi"]:
                f.metadata["provision_hi"] = " > ".join(hi_paths) if hi_paths else case_id

        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Cost estimation: $0.10 / 1M prompt, $0.40 / 1M completion (Gemini 3.8 Flash)
        cost_usd = (
            (semantic_res.tokens_prompt / 1_000_000.0) * 0.10 +
            (semantic_res.tokens_completion / 1_000_000.0) * 0.40
        )

        return ClauseAuditResult(
            case_id=case_id,
            en_paths=en_paths,
            hi_paths=hi_paths,
            en_text=en_text,
            hi_text=hi_text,
            findings=valid_findings,
            discarded_findings=discarded_findings,
            fact_diff_count=len(fact_res.differences),
            semantic_finding_count=len(semantic_res.findings),
            merged_finding_count=len(valid_findings),
            cost_usd=cost_usd,
            latency_ms=latency_ms
        )
