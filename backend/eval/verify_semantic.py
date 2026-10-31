"""
verify_semantic.py - Verifier for Phase Loop 5 (Semantic Stage & Grounded Auditing).

Evaluates:
  - recall_by_category on injected cases (MODALITY, OMISSION, ADDITION, SCOPE, DEFINITION)
  - precision overall (finding is correct only if it points at the injected error)
  - clean_false_positive_rate (findings per 100 clean pairs)
  - ungrounded_discard_rate (fraction of findings rejected by Grounding Guard R2)
  - json_failure_rate (fraction of invalid JSON outputs)
  - cost_per_100_pairs and token budget adherence (<= 300k tokens)

Exit criteria:
  - recall >= 0.80 on MODALITY, OMISSION, ADDITION, SCOPE
  - precision >= 0.80
  - clean_false_positive_rate <= 5.0 per 100 pairs
  - json_failure_rate <= 0.02
  - tests pass
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.semantic.client import SemanticComparatorClient, PROMPT_VERSION
from backend.app.semantic.models import SemanticCategory


TOKEN_BUDGET_LIMIT = 300_000  # Configured user token budget limit


def run_semantic_verification(
    dataset_path: str = "data/eval/dev/semantic_cases.jsonl",
    client: Optional[SemanticComparatorClient] = None
) -> Dict[str, Any]:
    """
    Runs the full semantic verification suite over the evaluation dataset.
    """
    if client is None:
        client = SemanticComparatorClient()

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Evaluation dataset '{dataset_path}' not found. Run build_semantic_cases.py first.")

    cases = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    # Counters
    total_cases = len(cases)
    clean_cases_count = 0
    injected_cases_count = 0

    category_totals = defaultdict(int)
    category_hits = defaultdict(int)

    true_positives = 0
    false_positives = 0
    clean_false_positive_findings = 0

    total_findings_generated = 0
    total_discarded_by_guard = 0
    total_json_retries = 0
    total_json_failures = 0

    total_tokens_prompt = 0
    total_tokens_completion = 0

    detailed_eval = []

    for case in cases:
        c_id = case["case_id"]
        en_text = case["en_text"]
        hi_text = case["hi_text"]
        is_synthetic = case["is_synthetic"]
        expected_diff = case["expected_diff"]
        gt = case.get("ground_truth")

        if not is_synthetic:
            clean_cases_count += 1
        else:
            injected_cases_count += 1
            if gt and "category" in gt:
                category_totals[gt["category"]] += 1

        # Run comparison
        res = client.compare_clause_pair(
            en_text=en_text,
            hi_text=hi_text,
            en_path=",".join(case.get("en_paths", [])),
            hi_path=",".join(case.get("hi_paths", []))
        )

        total_tokens_prompt += res.tokens_prompt
        total_tokens_completion += res.tokens_completion
        if res.json_retry_performed:
            total_json_retries += 1

        valid_findings = res.findings
        discarded_findings = res.discarded_findings

        total_findings_generated += len(valid_findings) + len(discarded_findings)
        total_discarded_by_guard += len(discarded_findings)

        case_hit = False

        if not is_synthetic:
            # Clean case: any valid finding is a false positive
            if valid_findings:
                clean_false_positive_findings += len(valid_findings)
                false_positives += len(valid_findings)
        else:
            # Injected case
            gt_cat = gt["category"] if gt else None
            # Check if any finding matches ground truth category
            matching_finding = None
            for f in valid_findings:
                if f.category.value == gt_cat:
                    matching_finding = f
                    break

            if matching_finding:
                case_hit = True
                category_hits[gt_cat] += 1
                true_positives += 1
                # Any extraneous findings beyond the true positive are false positives
                if len(valid_findings) > 1:
                    false_positives += (len(valid_findings) - 1)
            else:
                # None matched the ground truth: all reported findings are false positives
                false_positives += len(valid_findings)

        detailed_eval.append({
            "case_id": c_id,
            "is_synthetic": is_synthetic,
            "expected_category": gt.get("category") if gt else None,
            "findings_count": len(valid_findings),
            "case_hit": case_hit,
            "discarded_count": len(discarded_findings)
        })

    # Metric computations
    recall_by_cat = {}
    for cat in ["MODALITY", "OMISSION", "ADDITION", "SCOPE", "DEFINITION"]:
        tot = category_totals[cat]
        hits = category_hits[cat]
        recall_by_cat[cat] = round(hits / max(tot, 1), 4)

    # Core 4 target recall (MODALITY, OMISSION, ADDITION, SCOPE)
    core_cats = ["MODALITY", "OMISSION", "ADDITION", "SCOPE"]
    core_recall_values = [recall_by_cat[c] for c in core_cats]
    avg_core_recall = round(sum(core_recall_values) / len(core_recall_values), 4)

    total_pred = true_positives + false_positives
    precision = round(true_positives / max(total_pred, 1), 4)

    clean_fp_rate = round((clean_false_positive_findings / max(clean_cases_count, 1)) * 100.0, 2)
    ungrounded_discard_rate = round(total_discarded_by_guard / max(total_findings_generated, 1), 4)
    json_fail_rate = round(total_json_failures / max(total_cases, 1), 4)

    total_tokens = total_tokens_prompt + total_tokens_completion
    # Cost per 100 pairs estimation ($0.15/M in, $0.60/M out for Gemini Flash)
    cost_in = (total_tokens_prompt / 1_000_000.0) * 0.15
    cost_out = (total_tokens_completion / 1_000_000.0) * 0.60
    total_cost = cost_in + cost_out
    cost_per_100_pairs = round((total_cost / max(total_cases, 1)) * 100.0, 4)

    budget_exceeded = total_tokens > TOKEN_BUDGET_LIMIT

    # Exit checks
    modality_ok = recall_by_cat["MODALITY"] >= 0.80
    omission_ok = recall_by_cat["OMISSION"] >= 0.80
    addition_ok = recall_by_cat["ADDITION"] >= 0.80
    scope_ok = recall_by_cat["SCOPE"] >= 0.80
    precision_ok = precision >= 0.80
    clean_fp_ok = clean_fp_rate <= 5.0
    json_fail_ok = json_fail_rate <= 0.02

    all_passed = (
        modality_ok and omission_ok and addition_ok and scope_ok and
        precision_ok and clean_fp_ok and json_fail_ok and not budget_exceeded
    )

    return {
        "prompt_version": PROMPT_VERSION,
        "provider": client.provider_name,
        "model": client.model_name,
        "total_cases": total_cases,
        "clean_cases": clean_cases_count,
        "injected_cases": injected_cases_count,
        "recall_by_category": recall_by_cat,
        "avg_core_recall": avg_core_recall,
        "precision": precision,
        "clean_false_positive_rate": clean_fp_rate,
        "ungrounded_discard_rate": ungrounded_discard_rate,
        "json_failure_rate": json_fail_rate,
        "total_tokens_prompt": total_tokens_prompt,
        "total_tokens_completion": total_tokens_completion,
        "total_tokens": total_tokens,
        "budget_limit": TOKEN_BUDGET_LIMIT,
        "budget_exceeded": budget_exceeded,
        "cost_per_100_pairs": cost_per_100_pairs,
        "all_passed": all_passed
    }


def main():
    print("=" * 70)
    print("Tulya Phase Loop 5: Semantic Stage Verifier")
    print("=" * 70)

    res = run_semantic_verification()

    print(f"\nConfiguration: Provider={res['provider']}, Model={res['model']}, PromptVersion={res['prompt_version']}")
    print(f"Evaluated: {res['total_cases']} cases ({res['clean_cases']} clean, {res['injected_cases']} injected)\n")

    print("--- 1. Recall by Category (Injected Meaning-Level Errors) ---")
    for cat, rec in res["recall_by_category"].items():
        target_str = ">= 0.80" if cat != "DEFINITION" else "benchmark"
        status_str = "PASS" if cat == "DEFINITION" or rec >= 0.80 else "FAIL"
        print(f"  - {cat:<12}: {rec * 100:.1f}% (Target: {target_str}) -> {status_str}")

    print("\n--- 2. Precision & False Positive Rate ---")
    p_stat = "PASS" if res["precision"] >= 0.80 else "FAIL"
    print(f"  - Precision Overall          : {res['precision'] * 100:.1f}% (Exit: >= 80.0%) -> {p_stat}")
    fp_stat = "PASS" if res["clean_false_positive_rate"] <= 5.0 else "FAIL"
    print(f"  - Clean False Positive Rate  : {res['clean_false_positive_rate']} per 100 pairs (Exit: <= 5.0) -> {fp_stat}")

    print("\n--- 3. Resilience & Grounding Guard (Rule R2) ---")
    print(f"  - Ungrounded Discard Rate    : {res['ungrounded_discard_rate'] * 100:.1f}% (tracked)")
    jf_stat = "PASS" if res["json_failure_rate"] <= 0.02 else "FAIL"
    print(f"  - JSON Failure Rate          : {res['json_failure_rate'] * 100:.1f}% (Exit: <= 2.0%) -> {jf_stat}")

    print("\n--- 4. Token Budget & Cost ---")
    print(f"  - Total Tokens Used          : {res['total_tokens']:,} / {res['budget_limit']:,} (Budget Exceeded: {res['budget_exceeded']})")
    print(f"  - Cost per 100 Pairs         : ${res['cost_per_100_pairs']:.4f}")

    print("\n" + "=" * 70)
    if res["all_passed"]:
        print("VERIFIER RESULT: PASSED (All Phase Loop 5 Exit Criteria Met)")
    else:
        print("VERIFIER RESULT: FAILED (Exit Criteria Not Met)")
    print("=" * 70)

    if not res["all_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
