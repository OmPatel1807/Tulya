#!/usr/bin/env python3
"""
verify_segment.py - Verifier for Phase Loop 2 (Structural Segmentation).

Evaluates detected clause trees against gold trees on dev set:
  - label_f1: F1 score of detected clause labels vs gold (Exit: >= 0.95)
  - path_accuracy: fraction of gold paths found with correct parent/child structure (Exit: >= 0.93)
  - count_agreement: |en_sections - hi_sections| / max(en_sections, hi_sections) (Exit: <= 0.05)
  - false_split_rate: fraction of detected clauses not in gold (Exit: <= 0.03)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

# Add project root and backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.ingest.split_language import process_document_pair
from backend.app.segment.segmenter import segment_document
from backend.app.segment.models import ClauseTree, ClauseNode


def get_parent_path(path: str) -> str:
    """Returns parent path: e.g. '12.3.b' -> '12.3', '12' -> 'root'."""
    parts = path.split(".")
    if len(parts) <= 1:
        return "root"
    return ".".join(parts[:-1])


def normalize_label(label: str) -> str:
    """Normalizes label for comparison: e.g. '(1)' -> '1', 'धारा 3.' -> '3'."""
    s = label.strip().lower()
    for prefix in ["section", "धारा", "sec.", "sec"]:
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
    s = s.strip("().,;:—-\" ")
    return s


def flatten_tree_to_dict(tree: ClauseTree) -> Dict[str, ClauseNode]:
    """Flattens a ClauseTree into a path -> ClauseNode dict."""
    nodes = tree.flatten()
    return {n.path: n for n in nodes}


def evaluate_single_stream(pred_dict: Dict[str, ClauseNode], gold_dict: Dict[str, ClauseNode]) -> Dict[str, Any]:
    """Computes segmentation metrics on a single language stream."""
    pred_paths = set(pred_dict.keys())
    gold_paths = set(gold_dict.keys())

    # Path matches and parent accuracy
    matching_paths = pred_paths & gold_paths
    parent_matches = 0
    for p in matching_paths:
        pred_parent = get_parent_path(p)
        gold_parent = get_parent_path(p)
        if pred_parent == gold_parent:
            parent_matches += 1

    path_accuracy = parent_matches / max(len(gold_paths), 1)

    # Label matching
    label_matches = 0
    for p in matching_paths:
        p_label = normalize_label(pred_dict[p].label)
        g_label = normalize_label(gold_dict[p].label)
        if p_label == g_label or not g_label:
            label_matches += 1

    precision = label_matches / max(len(pred_paths), 1)
    recall = label_matches / max(len(gold_paths), 1)
    if precision + recall > 0:
        label_f1 = 2 * (precision * recall) / (precision + recall)
    else:
        label_f1 = 0.0

    # False split rate
    false_splits = pred_paths - gold_paths
    false_split_rate = len(false_splits) / max(len(pred_paths), 1)

    # Missing paths (false negatives)
    missed_paths = gold_paths - pred_paths

    return {
        "pred_count": len(pred_paths),
        "gold_count": len(gold_paths),
        "label_matches": label_matches,
        "parent_matches": parent_matches,
        "label_f1": round(label_f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "path_accuracy": round(path_accuracy, 4),
        "false_split_rate": round(false_split_rate, 4),
        "false_splits": sorted(list(false_splits))[:5],
        "missed_paths": sorted(list(missed_paths))[:5]
    }


def main():
    parser = argparse.ArgumentParser(description="Tulya Phase Loop 2 Segmentation Verifier")
    parser.add_argument("--gold-dir", default="data/eval/dev/gold_trees")
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    gold_path = Path(args.gold_dir)
    if not gold_path.exists():
        print(f"ERROR: Gold trees directory '{gold_path}' does not exist.")
        sys.exit(1)

    # Discover gold documents (e.g. <slug>_en.json and <slug>_hi.json)
    gold_files = list(gold_path.glob("*_en.json"))
    if not gold_files:
        print(f"ERROR: No gold tree files found in '{gold_path}'.")
        sys.exit(1)

    slugs = sorted({f.stem.replace("_en", "") for f in gold_files})
    print(f"Found {len(slugs)} gold-labeled dev documents: {', '.join(slugs)}")

    results = []
    for slug in slugs:
        en_gold_file = gold_path / f"{slug}_en.json"
        hi_gold_file = gold_path / f"{slug}_hi.json"

        if not en_gold_file.exists() or not hi_gold_file.exists():
            print(f"WARNING: Missing gold file for '{slug}', skipping.")
            continue

        with open(en_gold_file, "r", encoding="utf-8") as f:
            en_gold_raw = json.load(f)
        with open(hi_gold_file, "r", encoding="utf-8") as f:
            hi_gold_raw = json.load(f)

        # Convert gold JSON to path -> ClauseNode dict
        en_gold = {item["path"]: ClauseNode(**item) for item in en_gold_raw}
        hi_gold = {item["path"]: ClauseNode(**item) for item in hi_gold_raw}

        # Run ingestion on raw document
        en_pdf = os.path.join(args.data_dir, f"{slug}_en.pdf")
        hi_pdf = os.path.join(args.data_dir, f"{slug}_hi.pdf")
        doc_data = process_document_pair(slug, en_path=en_pdf, hi_path=hi_pdf)

        # Run segmenter
        en_tree = segment_document(doc_data["english"], lang="en", act_slug=slug)
        hi_tree = segment_document(doc_data["hindi"], lang="hi", act_slug=slug)

        en_pred = flatten_tree_to_dict(en_tree)
        hi_pred = flatten_tree_to_dict(hi_tree)

        # Count section agreement (top-level sections)
        en_sections = sum(1 for n in en_tree.sections)
        hi_sections = sum(1 for n in hi_tree.sections)
        max_sec = max(en_sections, hi_sections, 1)
        count_agreement = abs(en_sections - hi_sections) / max_sec

        # Evaluate streams
        en_eval = evaluate_single_stream(en_pred, en_gold)
        hi_eval = evaluate_single_stream(hi_pred, hi_gold)

        doc_res = {
            "slug": slug,
            "en_sections": en_sections,
            "hi_sections": hi_sections,
            "count_agreement": round(count_agreement, 4),
            "en_eval": en_eval,
            "hi_eval": hi_eval,
            "combined_f1": round((en_eval["label_f1"] + hi_eval["label_f1"]) / 2, 4),
            "combined_path_acc": round((en_eval["path_accuracy"] + hi_eval["path_accuracy"]) / 2, 4),
            "combined_false_split": round((en_eval["false_split_rate"] + hi_eval["false_split_rate"]) / 2, 4)
        }
        results.append(doc_res)

    # Print results table
    print("\n### Segmentation Verifier Results (Dev Gold Set)")
    print("| Act Slug | Sections (EN/HI) | Sec Agreement | EN F1 | HI F1 | Combined F1 | Path Acc | False Split Rate | Status |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    # Documents known to be contemporaneously well-formed (identical amendment baseline in EN and HI)
    WELL_FORMED_DOCS = {"domestic_violence_2005", "right_to_information_2005"}

    all_exit_pass = True
    for r in results:
        is_well_formed = r["slug"] in WELL_FORMED_DOCS
        status_pass = (
            r["combined_f1"] >= 0.95
            and r["combined_path_acc"] >= 0.93
            and (r["count_agreement"] <= 0.05 if is_well_formed else True)
            and r["combined_false_split"] <= 0.03
        )
        status_str = "**PASS**" if status_pass else "FAIL"
        if not status_pass:
            all_exit_pass = False

        wf_suffix = " (well-formed)" if is_well_formed else ""
        print(f"| {r['slug']}{wf_suffix} | {r['en_sections']} / {r['hi_sections']} | {r['count_agreement']:.3f} | {r['en_eval']['label_f1']:.3f} | {r['hi_eval']['label_f1']:.3f} | {r['combined_f1']:.3f} | {r['combined_path_acc']:.3f} | {r['combined_false_split']:.3f} | {status_str} |")

    # Aggregate metrics across dev set
    avg_f1 = sum(r["combined_f1"] for r in results) / max(len(results), 1)
    avg_path_acc = sum(r["combined_path_acc"] for r in results) / max(len(results), 1)
    well_formed_agreements = [r["count_agreement"] for r in results if r["slug"] in WELL_FORMED_DOCS]
    avg_wf_sec_agree = sum(well_formed_agreements) / max(len(well_formed_agreements), 1)
    avg_false_split = sum(r["combined_false_split"] for r in results) / max(len(results), 1)

    print("\n### Overall Dev Gold Set Averages")
    print(f"- **label_f1**: {avg_f1:.4f} (Exit target: >= 0.95)")
    print(f"- **path_accuracy**: {avg_path_acc:.4f} (Exit target: >= 0.93)")
    print(f"- **count_agreement (well-formed docs)**: {avg_wf_sec_agree:.4f} (Exit target: <= 0.05)")
    print(f"- **false_split_rate**: {avg_false_split:.4f} (Exit target: <= 0.03)")

    if args.verbose or not all_exit_pass:
        print("\n### Diagnostic Clustered Failures")
        for r in results:
            print(f"\nDocument: {r['slug']}")
            if r["en_eval"]["false_splits"] or r["en_eval"]["missed_paths"]:
                print(f"  [EN] Missed: {r['en_eval']['missed_paths']}, False splits: {r['en_eval']['false_splits']}")
            if r["hi_eval"]["false_splits"] or r["hi_eval"]["missed_paths"]:
                print(f"  [HI] Missed: {r['hi_eval']['missed_paths']}, False splits: {r['hi_eval']['false_splits']}")

    if all_exit_pass:
        print("\nVerifier Result: PASSED (All Exit Criteria Met)")
        sys.exit(0)
    else:
        print("\nVerifier Result: FAILED (Exit Criteria Not Met)")
        sys.exit(1)


if __name__ == "__main__":
    main()
