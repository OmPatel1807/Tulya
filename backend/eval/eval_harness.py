"""
eval_harness.py - End-to-End Evaluation Harness for Bilingual Statutory Consistency Auditing.

Computes:
  - Per-category precision, recall, and F1 (NUMERIC, OMISSION, ADDITION, MODALITY, SCOPE).
  - Overall precision, recall, F1.
  - False-positive rate on clean pairs (findings per 100 clauses).
  - Contribution breakdown: deterministic only, LLM only, both.
  - Ungrounded discards count and rate (Rule R2).
  - Cost and latency per 100 clauses.
  - Regression case verification across reported real-world patterns.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict

from backend.app.pipeline.runner import PipelineRunner
from backend.app.pipeline.models import AuditCategory, AuditSource, ClauseAuditResult


def category_matches(expected_cat: str, found_cat: str) -> bool:
    """Checks if predicted category matches ground truth category under permissible equivalences."""
    e = expected_cat.upper()
    f = found_cat.upper()
    if e == f:
        return True
    # Permissible semantic overlaps (e.g. additive penalties, numerical scope limits)
    if e == "NUMERIC" and f in ["NUMERIC", "SCOPE"]:
        return True
    if e == "SCOPE" and f in ["SCOPE", "NUMERIC", "DEFINITION"]:
        return True
    if e == "ADDITION" and f in ["ADDITION", "SCOPE"]:
        return True
    if e == "OMISSION" and f in ["OMISSION", "SCOPE"]:
        return True
    return False


def run_evaluation(
    dataset_path: str,
    runner: Optional[PipelineRunner] = None,
    dataset_name: str = "dev"
) -> Dict[str, Any]:
    """
    Executes end-to-end evaluation over an annotated JSONL dataset.
    """
    if runner is None:
        runner = PipelineRunner()

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Evaluation dataset '{dataset_path}' not found.")

    cases = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))

    # Metric accumulators
    clean_cases_count = 0
    injected_cases_count = 0

    category_totals = defaultdict(int)
    category_tp = defaultdict(int)
    category_fp = defaultdict(int)
    category_fn = defaultdict(int)

    overall_tp = 0
    overall_fp = 0
    overall_fn = 0

    clean_false_positive_clauses = 0
    clean_false_positive_findings = 0

    contribution = {
        "deterministic_only": 0,
        "llm_only": 0,
        "both": 0
    }

    total_valid_findings = 0
    total_discarded_findings = 0
    total_latency_ms = 0.0
    total_cost_usd = 0.0

    misses = []
    false_positives = []
    case_results = []

    for case in cases:
        c_id = case["case_id"]
        en_text = case["en_text"]
        hi_text = case["hi_text"]
        en_paths = case.get("en_paths", [])
        hi_paths = case.get("hi_paths", [])
        is_synthetic = case.get("is_synthetic", False)
        gt = case.get("ground_truth")

        audit_res: ClauseAuditResult = runner.audit_clause_pair(
            case_id=c_id,
            en_text=en_text,
            hi_text=hi_text,
            en_paths=en_paths,
            hi_paths=hi_paths
        )

        total_latency_ms += audit_res.latency_ms
        total_cost_usd += audit_res.cost_usd
        total_valid_findings += len(audit_res.findings)
        total_discarded_findings += len(audit_res.discarded_findings)

        # Track contribution
        for f in audit_res.findings:
            if f.source == AuditSource.DETERMINISTIC:
                contribution["deterministic_only"] += 1
            elif f.source == AuditSource.LLM:
                contribution["llm_only"] += 1
            elif f.source == AuditSource.BOTH:
                contribution["both"] += 1

        if not is_synthetic:
            # Clean case
            clean_cases_count += 1
            if len(audit_res.findings) > 0:
                clean_false_positive_clauses += 1
                clean_false_positive_findings += len(audit_res.findings)
                overall_fp += len(audit_res.findings)
                for f in audit_res.findings:
                    false_positives.append({
                        "case_id": c_id,
                        "type": "clean_fp",
                        "finding": f.model_dump(),
                        "en_text": en_text,
                        "hi_text": hi_text
                    })
        else:
            # Injected case
            injected_cases_count += 1
            expected_cat = gt["category"] if gt else "UNKNOWN"
            category_totals[expected_cat] += 1

            matched_finding = None
            for f in audit_res.findings:
                if category_matches(expected_cat, f.category.value):
                    matched_finding = f
                    break

            if matched_finding is not None:
                category_tp[expected_cat] += 1
                overall_tp += 1
                # Any extra finding beyond the matched one is an FP
                if len(audit_res.findings) > 1:
                    extra_fps = len(audit_res.findings) - 1
                    category_fp[expected_cat] += extra_fps
                    overall_fp += extra_fps
            else:
                category_fn[expected_cat] += 1
                overall_fn += 1
                misses.append({
                    "case_id": c_id,
                    "expected_category": expected_cat,
                    "ground_truth": gt,
                    "en_text": en_text,
                    "hi_text": hi_text,
                    "findings_returned": [f.model_dump() for f in audit_res.findings]
                })

        case_results.append({
            "case_id": c_id,
            "is_synthetic": is_synthetic,
            "findings_count": len(audit_res.findings),
            "findings": [f.model_dump() for f in audit_res.findings]
        })

    # Per-category metrics
    all_categories = sorted(list(set(list(category_totals.keys()) + ["NUMERIC", "OMISSION", "ADDITION", "MODALITY", "SCOPE"])))
    per_category = {}
    for cat in all_categories:
        tp = category_tp[cat]
        fn = category_fn[cat]
        fp = category_fp[cat]
        prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if tp == 0 and fp == 0 else 0.0)
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        per_category[cat] = {
            "total_injected": category_totals[cat],
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4)
        }

    overall_prec = overall_tp / (overall_tp + overall_fp) if (overall_tp + overall_fp) > 0 else 0.0
    overall_rec = overall_tp / (overall_tp + overall_fn) if (overall_tp + overall_fn) > 0 else 0.0
    overall_f1 = (2 * overall_prec * overall_rec) / (overall_prec + overall_rec) if (overall_prec + overall_rec) > 0 else 0.0

    clean_fp_rate_per_100 = (clean_false_positive_clauses / clean_cases_count * 100.0) if clean_cases_count > 0 else 0.0

    ungrounded_discard_rate = (
        total_discarded_findings / (total_valid_findings + total_discarded_findings)
        if (total_valid_findings + total_discarded_findings) > 0 else 0.0
    )

    cost_per_100 = (total_cost_usd / len(cases) * 100.0) if cases else 0.0
    latency_per_100_ms = (total_latency_ms / len(cases) * 100.0) if cases else 0.0

    return {
        "dataset_name": dataset_name,
        "total_cases": len(cases),
        "clean_cases_count": clean_cases_count,
        "injected_cases_count": injected_cases_count,
        "overall": {
            "precision": round(overall_prec, 4),
            "recall": round(overall_rec, 4),
            "f1": round(overall_f1, 4),
            "true_positives": overall_tp,
            "false_positives": overall_fp,
            "false_negatives": overall_fn
        },
        "per_category": per_category,
        "clean_false_positive_rate_per_100": round(clean_fp_rate_per_100, 2),
        "clean_fp_findings_total": clean_false_positive_findings,
        "contribution_breakdown": contribution,
        "ungrounded_discards": {
            "discarded_count": total_discarded_findings,
            "valid_count": total_valid_findings,
            "discard_rate": round(ungrounded_discard_rate, 4)
        },
        "efficiency": {
            "total_latency_seconds": round(total_latency_ms / 1000.0, 3),
            "latency_per_100_clauses_seconds": round(latency_per_100_ms / 1000.0, 3),
            "total_cost_usd": round(total_cost_usd, 6),
            "cost_per_100_clauses_usd": round(cost_per_100, 4)
        },
        "misses": misses,
        "false_positives": false_positives,
        "case_results": case_results
    }


def evaluate_regression_cases(
    cases_path: str = "data/eval/dev/real_inspired_synthetic/cases.jsonl",
    runner: Optional[PipelineRunner] = None
) -> Dict[str, Any]:
    """
    Evaluates synthetic reproductions of reported real-world patterns.
    """
    if runner is None:
        runner = PipelineRunner()

    if not os.path.exists(cases_path):
        raise FileNotFoundError(f"Regression cases file '{cases_path}' not found.")

    cases = []
    with open(cases_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    results = []
    flagged_count = 0

    for case in cases:
        c_id = case["case_id"]
        pt = case.get("pattern_type", "unknown")
        en_text = case["en_text"]
        hi_text = case["hi_text"]
        gt = case.get("ground_truth", {})

        audit_res = runner.audit_clause_pair(
            case_id=c_id,
            en_text=en_text,
            hi_text=hi_text,
            en_paths=case.get("en_paths", []),
            hi_paths=case.get("hi_paths", [])
        )

        is_flagged = len(audit_res.findings) > 0
        if is_flagged:
            flagged_count += 1

        results.append({
            "case_id": c_id,
            "pattern_type": pt,
            "is_flagged": is_flagged,
            "findings_count": len(audit_res.findings),
            "expected_category": gt.get("category"),
            "findings": [f.model_dump() for f in audit_res.findings],
            "reason_if_missed": "None (successfully flagged)" if is_flagged else "Finding missed by extraction/semantic comparison"
        })

    return {
        "total_regression_cases": len(cases),
        "flagged_count": flagged_count,
        "all_flagged": flagged_count == len(cases),
        "cases": results
    }
