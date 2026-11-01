"""
verify_pipeline.py - Verifier & Outer Loop Runner for Phase Loop 6 (End-to-End Pipeline).

Exit Criteria:
  - overall injected-error recall >= 0.80 on dev
  - overall precision >= 0.80 on dev
  - clean false-positive rate <= 5.0 per 100 clauses
  - every regression case flagged or honestly documented as missed with a reason

Outputs:
  - Displays metrics, category breakdowns, and diagnostic clusters of misses/FPs.
  - Generates eval/report.md and eval/results.json.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.eval.eval_harness import run_evaluation, evaluate_regression_cases
from backend.app.pipeline.runner import PipelineRunner


def print_evaluation_summary(res: Dict[str, Any], reg_res: Dict[str, Any] = None) -> bool:
    """Prints a structured scorecard and checks exit criteria."""
    print("=" * 72)
    print(f"Tulya Phase Loop 6: End-to-End Pipeline Evaluation ({res['dataset_name'].upper()})")
    print("=" * 72)

    print(f"\nEvaluated Cases: {res['total_cases']} ({res['clean_cases_count']} clean, {res['injected_cases_count']} injected)")

    print("\n--- 1. Per-Category Breakdown (Injected Discrepancies) ---")
    print(f"{'Category':<12} | {'Injected':<8} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Precision':<9} | {'Recall':<8} | {'F1':<6}")
    print("-" * 72)
    for cat, m in sorted(res["per_category"].items()):
        if m["total_injected"] > 0 or m["true_positives"] > 0:
            print(f"{cat:<12} | {m['total_injected']:<8} | {m['true_positives']:<4} | {m['false_positives']:<4} | {m['false_negatives']:<4} | {m['precision']:<9.1%} | {m['recall']:<8.1%} | {m['f1']:<6.3f}")

    ov = res["overall"]
    print("-" * 72)
    print(f"{'OVERALL':<12} | {res['injected_cases_count']:<8} | {ov['true_positives']:<4} | {ov['false_positives']:<4} | {ov['false_negatives']:<4} | {ov['precision']:<9.1%} | {ov['recall']:<8.1%} | {ov['f1']:<6.3f}")

    print("\n--- 2. False Positive Rate on Clean Pairs ---")
    clean_fp = res["clean_false_positive_rate_per_100"]
    clean_pass = clean_fp <= 5.0
    status_str = "PASS" if clean_pass else "FAIL"
    print(f"  - Clean FP Rate: {clean_fp:.2f} per 100 clauses (Exit Target: <= 5.0) -> {status_str}")
    print(f"  - Total Clean FP Findings: {res['clean_fp_findings_total']}")

    print("\n--- 3. Contribution Breakdown across Stages ---")
    contrib = res["contribution_breakdown"]
    total_findings = sum(contrib.values())
    if total_findings > 0:
        det_pct = contrib["deterministic_only"] / total_findings * 100
        llm_pct = contrib["llm_only"] / total_findings * 100
        both_pct = contrib["both"] / total_findings * 100
    else:
        det_pct = llm_pct = both_pct = 0.0

    print(f"  - Deterministic Only (Fact Stage) : {contrib['deterministic_only']:<3} ({det_pct:.1f}%)")
    print(f"  - LLM Only (Semantic Stage)       : {contrib['llm_only']:<3} ({llm_pct:.1f}%)")
    print(f"  - Both (Confirmed & Merged)       : {contrib['both']:<3} ({both_pct:.1f}%)")

    print("\n--- 4. Grounding Guard (Rule R2) & Resilience ---")
    gd = res["ungrounded_discards"]
    print(f"  - Discarded Non-Verbatim Findings : {gd['discarded_count']}")
    print(f"  - Ungrounded Discard Rate         : {gd['discard_rate']:.1%}")

    print("\n--- 5. Cost & Latency Performance ---")
    eff = res["efficiency"]
    print(f"  - Latency per 100 Clauses         : {eff['latency_per_100_clauses_seconds']:.2f} s")
    print(f"  - Cost per 100 Clauses            : ${eff['cost_per_100_clauses_usd']:.4f}")

    reg_pass = True
    if reg_res:
        print("\n--- 6. Regression Cases (Reported Statutory Divergences) ---")
        print(f"  - Total Cases: {reg_res['total_regression_cases']}, Flagged: {reg_res['flagged_count']}")
        for c in reg_res["cases"]:
            tag = "FLAGGED" if c["is_flagged"] else "MISSED"
            print(f"    [{tag}] {c['case_id']}: {c['pattern_type']} ({len(c['findings'])} findings)")
        reg_pass = reg_res["all_flagged"]

    # Exit check
    rec_pass = ov["recall"] >= 0.80
    prec_pass = ov["precision"] >= 0.80
    all_pass = rec_pass and prec_pass and clean_pass and reg_pass

    print("\n" + "=" * 72)
    print("EXIT CRITERIA EVALUATION:")
    print(f"  - Injected Recall >= 0.80   : {ov['recall']:.1%} -> {'PASS' if rec_pass else 'FAIL'}")
    print(f"  - Overall Precision >= 0.80 : {ov['precision']:.1%} -> {'PASS' if prec_pass else 'FAIL'}")
    print(f"  - Clean FP Rate <= 5.0      : {clean_fp:.2f} -> {'PASS' if clean_pass else 'FAIL'}")
    reg_count_str = f"{reg_res['flagged_count']}/{reg_res['total_regression_cases']}" if reg_res else "N/A (Dev Only)"
    print(f"  - Regression Cases Flagged  : {reg_count_str} -> {'PASS' if reg_pass else 'FAIL'}")
    print(f"VERIFIER RESULT: {'PASSED (All Exit Criteria Satisfied)' if all_pass else 'FAILED (Iteration Required)'}")
    print("=" * 72)

    return all_pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tulya Phase Loop 6 Pipeline Verifier")
    parser.add_argument("--heldout", action="store_true", help="Run on frozen held-out dataset")
    args = parser.parse_args()

    if args.heldout:
        dataset_path = "data/eval/heldout/e2e_cases.jsonl"
        d_name = "heldout"
        reg_res = None
    else:
        dataset_path = "data/eval/dev/e2e_cases.jsonl"
        d_name = "dev"
        reg_res = evaluate_regression_cases()

    runner = PipelineRunner()
    res = run_evaluation(dataset_path=dataset_path, runner=runner, dataset_name=d_name)
    success = print_evaluation_summary(res, reg_res)
    sys.exit(0 if success else 1)
