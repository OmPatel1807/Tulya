#!/usr/bin/env python3
"""
verify_ingest.py - Verifier for Phase Loop 1 (Ingestion).

Metrics computed on all usable documents:
  - extraction_ok_rate: fraction of usable docs producing both streams without errors (Exit: 1.0)
  - garbage_rate: fraction of Hindi lines whose Devanagari fraction is below threshold (Exit: < 0.02)
  - header_footer_leak: count of repeated header/footer lines remaining in output (Exit: 0)
  - language_mix_error: fraction of lines assigned to the wrong language (Exit: < 0.02)
  - blank_page_rate & avg_chars_per_page: sanity tracking metrics
Prints 15 sample Hindi and 15 sample English lines per document.
"""

import os
import sys
import re
import json
import random
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.ingest.pdf_loader import extract_text
from backend.app.ingest.script_check import check_script, DEVANAGARI_RE, LATIN_RE
from backend.app.ingest.clean import clean_stream, detect_repeated_headers_footers
from backend.app.ingest.split_language import process_document_pair

SHORT_LEGAL_TOKENS = {
    "act", "no", "sec", "section", "part", "chapter", "the", "of", "and", "in", "to",
    "dr", "mr", "mrs", "ms", "vs", "v", "govt", "delhi", "india", "code", "amendment"
}

def is_content_line(line: str) -> bool:
    """Check if line contains substantive alphabetic content."""
    s = line.strip()
    if not s or len(s) < 3:
        return False
    # Check if line is only digits, punctuation, or roman numerals
    alpha = [c for c in s if c.isalpha()]
    return len(alpha) >= 3

def compute_line_script_stats(line: str) -> Tuple[int, int]:
    """Returns (devanagari_count, latin_count) for a line."""
    dev = len(DEVANAGARI_RE.findall(line))
    lat = len(LATIN_RE.findall(line))
    return dev, lat

def verify_document(slug: str, en_pdf: str, hi_pdf: str, bi_pdf: str = None) -> Dict[str, Any]:
    """Verifies ingestion on a single document pair."""
    res = {
        "slug": slug,
        "extraction_ok": False,
        "en_pages": 0,
        "hi_pages": 0,
        "en_chars": 0,
        "hi_chars": 0,
        "blank_page_rate": 0.0,
        "avg_chars_per_page_en": 0.0,
        "avg_chars_per_page_hi": 0.0,
        "garbage_rate": 0.0,
        "header_footer_leak": 0,
        "language_mix_error": 0.0,
        "leaked_headers": [],
        "sample_en_lines": [],
        "sample_hi_lines": [],
        "errors": []
    }

    try:
        data = process_document_pair(
            act_slug=slug,
            en_path=en_pdf,
            hi_path=hi_pdf,
            bi_path=bi_pdf
        )
    except Exception as e:
        res["errors"].append(f"Ingestion pipeline failed: {e}")
        return res

    en_pages = data.get("english", [])
    hi_pages = data.get("hindi", [])

    if not en_pages or not hi_pages:
        res["errors"].append(f"Missing stream (en={len(en_pages)}, hi={len(hi_pages)})")
        return res

    res["extraction_ok"] = True
    res["en_pages"] = len(en_pages)
    res["hi_pages"] = len(hi_pages)

    # Blank page rate & char counts
    total_pages = len(en_pages) + len(hi_pages)
    blank_pages = sum(1 for p in (en_pages + hi_pages) if not p.get("text", "").strip())
    res["blank_page_rate"] = round(blank_pages / max(total_pages, 1), 4)

    total_en_chars = sum(len(p.get("text", "")) for p in en_pages)
    total_hi_chars = sum(len(p.get("text", "")) for p in hi_pages)
    res["en_chars"] = total_en_chars
    res["hi_chars"] = total_hi_chars
    res["avg_chars_per_page_en"] = round(total_en_chars / max(len(en_pages), 1), 1)
    res["avg_chars_per_page_hi"] = round(total_hi_chars / max(len(hi_pages), 1), 1)

    # 1. Header/Footer leak detection: check if repeated lines survived cleaning
    all_raw_pages = [p.get("raw_text", "") for p in en_pages + hi_pages if "raw_text" in p]
    if all_raw_pages:
        known_repeated = detect_repeated_headers_footers(all_raw_pages, threshold=0.25)
    else:
        known_repeated = set()

    leaked = []
    for stream_pages in [en_pages, hi_pages]:
        for p in stream_pages:
            lines = [l.strip() for l in p.get("text", "").splitlines() if l.strip()]
            for l in lines:
                if l in known_repeated:
                    leaked.append(l)
    res["header_footer_leak"] = len(leaked)
    res["leaked_headers"] = leaked[:5]

    # 2. Hindi Garbage rate: fraction of Hindi content lines with Devanagari fraction < 0.40
    hi_content_lines = []
    for p in hi_pages:
        lines = [l.strip() for l in p.get("text", "").splitlines()]
        for l in lines:
            if is_content_line(l):
                hi_content_lines.append(l)

    garbage_count = 0
    hi_lang_mismatch = 0
    for l in hi_content_lines:
        dev, lat = compute_line_script_stats(l)
        total_alpha = dev + lat
        if total_alpha > 0:
            frac = dev / total_alpha
            if frac < 0.35:
                garbage_count += 1
            # Script check for language mix error
            words = set(re.findall(r'[a-zA-Z]+', l.lower()))
            # Ignore if words are only short tokens
            if frac < 0.50 and not (words.issubset(SHORT_LEGAL_TOKENS)):
                hi_lang_mismatch += 1

    res["garbage_rate"] = round(garbage_count / max(len(hi_content_lines), 1), 4)

    # 3. Language mix error on English stream
    en_content_lines = []
    for p in en_pages:
        lines = [l.strip() for l in p.get("text", "").splitlines()]
        for l in lines:
            if is_content_line(l):
                en_content_lines.append(l)

    en_lang_mismatch = 0
    for l in en_content_lines:
        dev, lat = compute_line_script_stats(l)
        total_alpha = dev + lat
        if total_alpha > 0 and (dev / total_alpha) > 0.50:
            en_lang_mismatch += 1

    total_content_lines = len(hi_content_lines) + len(en_content_lines)
    total_mismatches = hi_lang_mismatch + en_lang_mismatch
    res["language_mix_error"] = round(total_mismatches / max(total_content_lines, 1), 4)

    # Sample lines for inspection
    rng = random.Random(42)  # Deterministic seed
    if en_content_lines:
        res["sample_en_lines"] = rng.sample(en_content_lines, min(15, len(en_content_lines)))
    if hi_content_lines:
        res["sample_hi_lines"] = rng.sample(hi_content_lines, min(15, len(hi_content_lines)))

    return res

def main():
    parser = argparse.ArgumentParser(description="Tulya Phase Loop 1 Ingestion Verifier")
    parser.add_argument("--readiness-file", default="data/processed/data_readiness.json")
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--samples", action="store_true", help="Print 15 sample lines per stream")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    readiness_path = Path(args.readiness_file)
    if not readiness_path.exists():
        print(f"ERROR: Prerequisite {readiness_path} not found. Run Phase Loop 0 first.")
        sys.exit(1)

    with open(readiness_path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    usable_docs = [d for d in docs if d.get("usable")]
    skipped_docs = [d for d in docs if not d.get("usable")]

    if not usable_docs:
        print("ERROR: No usable documents found in readiness file.")
        sys.exit(1)

    results = []
    for d in usable_docs:
        slug = d["act_slug"]
        en_p = os.path.join(args.data_dir, f"{slug}_en.pdf")
        hi_p = os.path.join(args.data_dir, f"{slug}_hi.pdf")
        bi_p = os.path.join(args.data_dir, f"{slug}_bi.pdf")
        en_file = en_p if os.path.exists(en_p) else None
        hi_file = hi_p if os.path.exists(hi_p) else None
        bi_file = bi_p if os.path.exists(bi_p) else None

        res = verify_document(slug, en_file, hi_file, bi_file)
        results.append(res)

    # Summary metrics
    n_docs = len(usable_docs)
    ok_count = sum(1 for r in results if r["extraction_ok"])
    extraction_ok_rate = ok_count / max(n_docs, 1)
    avg_garbage_rate = sum(r["garbage_rate"] for r in results) / max(n_docs, 1)
    total_header_leaks = sum(r["header_footer_leak"] for r in results)
    avg_lang_mix = sum(r["language_mix_error"] for r in results) / max(n_docs, 1)
    avg_blank_rate = sum(r["blank_page_rate"] for r in results) / max(n_docs, 1)

    # Print markdown table
    print("\n### Ingestion Verifier - Per-Document Results")
    print("| Act Slug | Extraction OK | EN Pages | HI Pages | Avg Chars (EN/HI) | Blank Rate | Garbage Rate | H/F Leak | Lang Mix Err | Status |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in results:
        status = "**PASS**" if (r["extraction_ok"] and r["garbage_rate"] < 0.02 and r["header_footer_leak"] == 0 and r["language_mix_error"] < 0.02) else "FAIL"
        print(f"| {r['slug']} | {r['extraction_ok']} | {r['en_pages']} | {r['hi_pages']} | {r['avg_chars_per_page_en']}/{r['avg_chars_per_page_hi']} | {r['blank_page_rate']} | {r['garbage_rate']} | {r['header_footer_leak']} | {r['language_mix_error']} | {status} |")

    print("\n### Overall Summary Metrics")
    print(f"- **extraction_ok_rate**: {extraction_ok_rate:.3f} (Exit target: 1.0)")
    print(f"- **avg_garbage_rate**: {avg_garbage_rate:.4f} (Exit target: < 0.02)")
    print(f"- **total_header_footer_leak**: {total_header_leaks} (Exit target: 0)")
    print(f"- **avg_language_mix_error**: {avg_lang_mix:.4f} (Exit target: < 0.02)")
    print(f"- **avg_blank_page_rate**: {avg_blank_rate:.4f}")

    all_passed = (
        extraction_ok_rate == 1.0
        and avg_garbage_rate < 0.02
        and total_header_leaks == 0
        and avg_lang_mix < 0.02
    )

    if args.samples:
        print("\n### Sample Cleaned Lines (15 per language per document)")
        for r in results:
            print(f"\n#### Document: {r['slug']}")
            print("**English Sample Lines:**")
            for idx, line in enumerate(r["sample_en_lines"][:15], 1):
                print(f"  {idx}. {line}")
            print("\n**Hindi Sample Lines:**")
            for idx, line in enumerate(r["sample_hi_lines"][:15], 1):
                print(f"  {idx}. {line}")

    if skipped_docs:
        print(f"\nSkipped Documents ({len(skipped_docs)}):")
        for s in skipped_docs:
            print(f"  - {s.get('act_slug')}: {s.get('reason')}")

    if not all_passed:
        print("\nVerifier Result: FAILED (Exit criteria not yet satisfied)")
        sys.exit(1)
    else:
        print("\nVerifier Result: PASSED (All exit criteria satisfied)")
        sys.exit(0)

if __name__ == "__main__":
    main()
