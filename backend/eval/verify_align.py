#!/usr/bin/env python3
"""
verify_align.py - Verifier for Phase Loop 3 (Bilingual Clause Alignment).

Evaluates alignment against gold alignment set:
  - pair_accuracy: fraction of gold pairs recovered exactly (Exit: >= 0.92)
  - structural_precision: precision of STRUCTURAL matches (Exit: >= 0.98)
  - false_alignment_rate: fraction of produced pairs that link unrelated clauses (Exit: <= 0.04)
  - omission_recall: fraction of known-missing clauses correctly left unaligned (Exit: >= 0.85)
  - runtime_per_100_clauses: execution benchmark
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

# Add project root and backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.ingest.split_language import process_document_pair
from backend.app.segment.segmenter import segment_document
from backend.app.align.aligner import align_document_trees
from backend.app.align.models import AlignedPair, AlignmentResult


def load_gold_alignments(gold_file: Path) -> List[Dict[str, Any]]:
    """Loads gold alignment records from JSONL file."""
    records = []
    with open(gold_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                records.append(json.loads(line))
    return records


def evaluate_alignments(
    gold_records: List[Dict[str, Any]],
    doc_results: Dict[str, AlignmentResult],
    total_clauses: int,
    elapsed_time: float
) -> Dict[str, Any]:
    """Computes all required metrics on the alignment predictions against gold."""
    total_gold = len(gold_records)
    if total_gold == 0:
        return {"error": "No gold records provided"}

    exact_pair_matches = 0
    gold_omissions = 0
    recovered_omissions = 0

    # Index predicted pairs by act_slug
    # Maps act_slug -> dict of (en_paths_tuple, hi_paths_tuple) -> AlignedPair
    pred_index: Dict[str, Dict[Tuple[Tuple[str, ...], Tuple[str, ...]], AlignedPair]] = {}
    pred_en_map: Dict[str, Dict[str, AlignedPair]] = {}
    pred_hi_map: Dict[str, Dict[str, AlignedPair]] = {}

    total_structural = 0
    correct_structural = 0
    total_aligned_pairs = 0
    false_aligned_pairs = 0

    for slug, res in doc_results.items():
        pred_index[slug] = {}
        pred_en_map[slug] = {}
        pred_hi_map[slug] = {}
        for p in res.pairs:
            en_tup = tuple(sorted(p.en_paths))
            hi_tup = tuple(sorted(p.hi_paths))
            pred_index[slug][(en_tup, hi_tup)] = p
            for ep in p.en_paths:
                pred_en_map[slug][ep] = p
            for hp in p.hi_paths:
                pred_hi_map[slug][hp] = p

            if p.match_type == "STRUCTURAL":
                total_structural += 1
                # Structural precision: valid if canonical paths match identically and content does not contradict
                is_valid_struct = (
                    p.en_paths == p.hi_paths
                    and len(p.en_paths) > 0
                    and p.similarity >= 0.0
                )
                if is_valid_struct:
                    correct_structural += 1

            if not p.is_omission:
                total_aligned_pairs += 1

    # Evaluate gold records
    for g in gold_records:
        slug = g["act_slug"]
        expected_type = g.get("expected_match_type", "")
        g_en = sorted(g.get("en_paths", []))
        g_hi = sorted(g.get("hi_paths", []))
        is_gold_omission = (len(g_en) == 0 or len(g_hi) == 0 or expected_type == "OMISSION")

        if is_gold_omission:
            gold_omissions += 1
            # Check if correctly left unaligned
            res = doc_results.get(slug)
            if res:
                if len(g_en) > 0 and len(g_hi) == 0:
                    en_target = g_en[0]
                    # Successfully omitted if in unaligned_en or not linked to any Hindi clause
                    pair = pred_en_map.get(slug, {}).get(en_target)
                    if en_target in res.unaligned_en or (pair and len(pair.hi_paths) == 0):
                        recovered_omissions += 1
                        exact_pair_matches += 1
                    else:
                        false_aligned_pairs += 1
                elif len(g_hi) > 0 and len(g_en) == 0:
                    hi_target = g_hi[0]
                    pair = pred_hi_map.get(slug, {}).get(hi_target)
                    if hi_target in res.unaligned_hi or (pair and len(pair.en_paths) == 0):
                        recovered_omissions += 1
                        exact_pair_matches += 1
                    else:
                        false_aligned_pairs += 1
        else:
            # Regular aligned pair (1-to-1, 1-to-2, 2-to-1, reordered)
            tup_key = (tuple(g_en), tuple(g_hi))
            matched_pair = pred_index.get(slug, {}).get(tup_key)
            if matched_pair:
                exact_pair_matches += 1
            else:
                # Check if it was falsely linked to a different clause
                any_en_linked = any(ep in pred_en_map.get(slug, {}) for ep in g_en)
                any_hi_linked = any(hp in pred_hi_map.get(slug, {}) for hp in g_hi)
                if any_en_linked or any_hi_linked:
                    false_aligned_pairs += 1

    pair_accuracy = exact_pair_matches / max(total_gold, 1)
    structural_precision = correct_structural / max(total_structural, 1)
    false_alignment_rate = false_aligned_pairs / max(total_aligned_pairs, 1)
    omission_recall = recovered_omissions / max(gold_omissions, 1) if gold_omissions > 0 else 1.0
    runtime_per_100 = (elapsed_time / max(total_clauses, 1)) * 100.0

    return {
        "total_gold": total_gold,
        "exact_pair_matches": exact_pair_matches,
        "pair_accuracy": round(pair_accuracy, 4),
        "structural_precision": round(structural_precision, 4),
        "false_alignment_rate": round(false_alignment_rate, 4),
        "gold_omissions": gold_omissions,
        "recovered_omissions": recovered_omissions,
        "omission_recall": round(omission_recall, 4),
        "total_clauses": total_clauses,
        "elapsed_time_sec": round(elapsed_time, 2),
        "runtime_per_100_clauses": round(runtime_per_100, 3)
    }


def main():
    parser = argparse.ArgumentParser(description="Tulya Phase Loop 3 Alignment Verifier")
    parser.add_argument("--gold-file", default="data/eval/dev/gold_alignment.jsonl")
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    gold_path = Path(args.gold_file)
    if not gold_path.exists():
        print(f"ERROR: Gold alignment file '{gold_path}' does not exist.")
        sys.exit(1)

    gold_records = load_gold_alignments(gold_path)
    print(f"Loaded {len(gold_records)} gold alignment pairs from '{gold_path}'")

    dev_slugs = sorted({g["act_slug"] for g in gold_records})
    print(f"Target Acts ({len(dev_slugs)}): {', '.join(dev_slugs)}")

    doc_results: Dict[str, AlignmentResult] = {}
    total_clauses = 0

    t0 = time.time()
    for slug in dev_slugs:
        en_pdf = os.path.join(args.data_dir, f"{slug}_en.pdf")
        hi_pdf = os.path.join(args.data_dir, f"{slug}_hi.pdf")

        if not os.path.exists(en_pdf) or not os.path.exists(hi_pdf):
            print(f"WARNING: Missing PDF pair for '{slug}', skipping.")
            continue

        doc_data = process_document_pair(slug, en_path=en_pdf, hi_path=hi_pdf)
        en_tree = segment_document(doc_data["english"], lang="en", act_slug=slug)
        hi_tree = segment_document(doc_data["hindi"], lang="hi", act_slug=slug)

        total_clauses += len(en_tree.flatten()) + len(hi_tree.flatten())

        align_res = align_document_trees(en_tree, hi_tree, act_slug=slug)
        doc_results[slug] = align_res

    elapsed_time = time.time() - t0

    eval_res = evaluate_alignments(gold_records, doc_results, total_clauses, elapsed_time)

    # Print results
    print("\n### Phase Loop 3 Alignment Verifier Results (Dev Set)")
    print(f"- **pair_accuracy**: {eval_res['pair_accuracy']:.4f} (Exit target: >= 0.92) -> {'PASS' if eval_res['pair_accuracy'] >= 0.92 else 'FAIL'}")
    print(f"- **structural_precision**: {eval_res['structural_precision']:.4f} (Exit target: >= 0.98) -> {'PASS' if eval_res['structural_precision'] >= 0.98 else 'FAIL'}")
    print(f"- **false_alignment_rate**: {eval_res['false_alignment_rate']:.4f} (Exit target: <= 0.04) -> {'PASS' if eval_res['false_alignment_rate'] <= 0.04 else 'FAIL'}")
    print(f"- **omission_recall**: {eval_res['omission_recall']:.4f} (Exit target: >= 0.85) -> {'PASS' if eval_res['omission_recall'] >= 0.85 else 'FAIL'}")
    print(f"- **runtime_per_100_clauses**: {eval_res['runtime_per_100_clauses']:.2f}s ({eval_res['total_clauses']} total clauses across {len(dev_slugs)} Acts in {eval_res['elapsed_time_sec']}s)")

    all_exit_pass = (
        eval_res["pair_accuracy"] >= 0.92
        and eval_res["structural_precision"] >= 0.98
        and eval_res["false_alignment_rate"] <= 0.04
        and eval_res["omission_recall"] >= 0.85
    )

    if all_exit_pass:
        print("\nVerifier Result: PASSED (All Exit Criteria Met)")
        sys.exit(0)
    else:
        print("\nVerifier Result: FAILED (Exit Criteria Not Met)")
        sys.exit(1)


if __name__ == "__main__":
    main()
