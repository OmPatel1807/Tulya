"""
split_language.py - Handles language stream splitting for separate files
(_en.pdf / _hi.pdf) and single bilingual PDFs (_bi.pdf).
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from backend.app.ingest.pdf_loader import extract_text
from backend.app.ingest.script_check import check_script, devanagari_fraction, LegacyFontError
from backend.app.ingest.clean import clean_stream


def split_bilingual_pages(raw_pages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """
    Splits a bilingual PDF stream into English and Hindi page streams.
    Handles both page-by-page alternation and two-column / mixed layout blocks.
    """
    en_pages: List[Dict[str, Any]] = []
    hi_pages: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for p in raw_pages:
        page_no = p.get("page_no", 1)
        raw_text = p.get("raw_text", "")
        method = p.get("method", "PyMuPDF")

        if not raw_text.strip():
            continue

        frac = devanagari_fraction(raw_text)

        if frac >= 0.70:
            # Full Hindi page
            hi_pages.append(p)
        elif frac <= 0.15:
            # Full English page
            en_pages.append(p)
        else:
            # Mixed page: split by lines/blocks
            lines = raw_text.splitlines()
            en_lines = []
            hi_lines = []
            for line in lines:
                l_frac = devanagari_fraction(line)
                if l_frac >= 0.40:
                    hi_lines.append(line)
                elif l_frac <= 0.20:
                    en_lines.append(line)
                else:
                    # Ambiguous line (e.g. mixed words)
                    if l_frac >= 0.30:
                        hi_lines.append(line)
                    else:
                        en_lines.append(line)

            if en_lines:
                en_pages.append({
                    "page_no": page_no,
                    "raw_text": "\n".join(en_lines),
                    "method": method
                })
            if hi_lines:
                hi_pages.append({
                    "page_no": page_no,
                    "raw_text": "\n".join(hi_lines),
                    "method": method
                })
            warnings.append(f"Page {page_no} was partitioned into bilingual streams (dev_fraction={frac:.2f})")

    return en_pages, hi_pages, warnings


def process_document_pair(
    act_slug: str,
    en_path: Optional[str] = None,
    hi_path: Optional[str] = None,
    bi_path: Optional[str] = None,
    strict_script: bool = True
) -> Dict[str, Any]:
    """
    Processes an Act document into clean English and Hindi text streams with metadata.
    """
    warnings: List[str] = []

    if bi_path and os.path.exists(bi_path):
        # Bilingual single PDF
        raw_pages = extract_text(bi_path)
        en_raw_pages, hi_raw_pages, split_warns = split_bilingual_pages(raw_pages)
        warnings.extend(split_warns)
    elif en_path and hi_path and os.path.exists(en_path) and os.path.exists(hi_path):
        # Separate English and Hindi files
        en_raw_pages = extract_text(en_path)
        hi_raw_pages = extract_text(hi_path)
    else:
        raise ValueError(f"Must provide either existing bi_path or both en_path and hi_path for '{act_slug}'")

    # Script check on Hindi text to detect legacy font before downstream processing
    hi_sample = "\n".join(p.get("raw_text", "") for p in hi_raw_pages[:5])
    script_eval = check_script(hi_sample, expected_lang="hi", strict=strict_script)
    if script_eval["verdict"] == "LEGACY_FONT_SUSPECTED":
        raise LegacyFontError(f"Document '{act_slug}' failed script check: {script_eval['message']}")

    # Clean streams
    en_cleaned = clean_stream(en_raw_pages)
    hi_cleaned = clean_stream(hi_raw_pages)

    total_en_chars = sum(len(p["text"]) for p in en_cleaned)
    total_hi_chars = sum(len(p["text"]) for p in hi_cleaned)

    result = {
        "act_slug": act_slug,
        "english": en_cleaned,
        "hindi": hi_cleaned,
        "warnings": warnings,
        "stats": {
            "en_pages": len(en_cleaned),
            "hi_pages": len(hi_cleaned),
            "en_chars": total_en_chars,
            "hi_chars": total_hi_chars,
            "hi_script_verdict": script_eval["verdict"],
            "hi_devanagari_fraction": script_eval["devanagari_fraction"]
        }
    }
    return result
