"""
cli.py - Command Line Interface for Tulya Ingestion Module.
Usage:
  python -m app.ingest.cli <act_slug_or_pair> --out data/processed/<name>.json
  python -m backend.app.ingest.cli <act_slug_or_pair> --out data/processed/<name>.json
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add project root and backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.ingest.split_language import process_document_pair


def main():
    parser = argparse.ArgumentParser(description="Tulya Ingestion CLI - Extract, clean, and split legal text")
    parser.add_argument("target", help="Act slug (e.g. right_to_information_2005) or path to PDF")
    parser.add_argument("--en", dest="en_path", help="Path to English PDF")
    parser.add_argument("--hi", dest="hi_path", help="Path to Hindi PDF")
    parser.add_argument("--bi", dest="bi_path", help="Path to Bilingual PDF")
    parser.add_argument("--data-dir", default="data/raw", help="Directory containing raw PDFs")
    parser.add_argument("--out", dest="out_path", help="Path to output JSON file")
    args = parser.parse_args()

    slug = args.target
    en_path = args.en_path
    hi_path = args.hi_path
    bi_path = args.bi_path

    # If slug is provided without paths, check data-dir
    if not en_path and not hi_path and not bi_path:
        base = Path(args.data_dir)
        # Check if slug is a filename
        if slug.endswith(".pdf"):
            target_path = Path(slug)
            slug = target_path.stem.replace("_en", "").replace("_hi", "").replace("_bi", "")
        cand_bi = base / f"{slug}_bi.pdf"
        cand_en = base / f"{slug}_en.pdf"
        cand_hi = base / f"{slug}_hi.pdf"

        if cand_bi.exists():
            bi_path = str(cand_bi)
        else:
            if cand_en.exists():
                en_path = str(cand_en)
            if cand_hi.exists():
                hi_path = str(cand_hi)

    if not bi_path and (not en_path or not hi_path):
        print(f"ERROR: Could not locate PDFs for '{slug}'. Check paths or supply --en and --hi.")
        sys.exit(1)

    print(f"Ingesting '{slug}'...")
    res = process_document_pair(
        act_slug=slug,
        en_path=en_path,
        hi_path=hi_path,
        bi_path=bi_path
    )

    out_file = args.out_path
    if not out_file:
        out_dir = Path("data/processed")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{slug}.json"
    else:
        out_file = Path(out_file)
        out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    print(f"Successfully processed {slug} -> {out_file}")
    print(f"  English: {res['stats']['en_pages']} pages, {res['stats']['en_chars']} chars")
    print(f"  Hindi:   {res['stats']['hi_pages']} pages, {res['stats']['hi_chars']} chars")


if __name__ == "__main__":
    main()
