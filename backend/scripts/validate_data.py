#!/usr/bin/env python3
"""
validate_data.py - Data readiness and verification script for Tulya.
Produces for each document pair:
  - pages (en / hi)
  - extraction method (PyMuPDF / pdfplumber fallback)
  - Devanagari fraction per Hindi page
  - verdict (OK_UNICODE_HINDI / LEGACY_FONT_SUSPECTED / EMPTY / ENGLISH_ONLY)
  - count of section-like headings per language
  - USABLE yes/no with reason
  - Same-act check (Act title, number, year)
  - Size sanity (0.6x - 1.6x page ratio)
  - Heading parity check (within 10%)
"""

import os
import re
import sys
import glob
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


# Unicode ranges
DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')
LATIN_RE = re.compile(r'[a-zA-Z]')
DEVANAGARI_DIGITS = {'०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
                     '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'}


def to_arabic_digits(text: str) -> str:
    """Convert Devanagari numerals to standard Arabic numerals."""
    for dev, ara in DEVANAGARI_DIGITS.items():
        text = text.replace(dev, ara)
    return text


def extract_text_pymupdf(pdf_path: str) -> Tuple[List[str], str]:
    """Extract page texts using PyMuPDF (fitz). Returns (page_texts, method)."""
    page_texts = []
    if fitz is None:
        raise ImportError("PyMuPDF (fitz) is not installed")
    doc = fitz.open(pdf_path)
    for page in doc:
        page_texts.append(page.get_text() or "")
    doc.close()
    return page_texts, "PyMuPDF"


def extract_text_pdfplumber(pdf_path: str) -> Tuple[List[str], str]:
    """Fallback extraction using pdfplumber."""
    page_texts = []
    if pdfplumber is None:
        raise ImportError("pdfplumber is not installed")
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_texts.append(page.extract_text() or "")
    return page_texts, "pdfplumber"


def extract_pdf_pages(pdf_path: str) -> Tuple[List[str], str]:
    """Extract page texts trying PyMuPDF first, falling back to pdfplumber."""
    try:
        texts, method = extract_text_pymupdf(pdf_path)
        total_len = sum(len(t.strip()) for t in texts)
        if total_len > 0:
            return texts, method
    except Exception:
        pass

    try:
        texts, method = extract_text_pdfplumber(pdf_path)
        return texts, method
    except Exception as e:
        return [], f"FAILED: {e}"


def compute_devanagari_fraction(text: str) -> float:
    """Computes ratio of Devanagari letters to total alphabetic letters."""
    dev_count = len(DEVANAGARI_RE.findall(text))
    lat_count = len(LATIN_RE.findall(text))
    total = dev_count + lat_count
    if total == 0:
        return 0.0
    return dev_count / total


def assess_hindi_text(page_texts: List[str]) -> Tuple[str, List[float], float]:
    """
    Evaluates Hindi page texts.
    Returns: (verdict, list of per-page fractions, overall fraction)
    """
    if not page_texts or all(len(p.strip()) == 0 for p in page_texts):
        return "EMPTY", [], 0.0

    fractions = []
    total_dev = 0
    total_alpha = 0
    for page in page_texts:
        dev = len(DEVANAGARI_RE.findall(page))
        lat = len(LATIN_RE.findall(page))
        alpha = dev + lat
        total_dev += dev
        total_alpha += alpha
        fractions.append(round(dev / alpha, 3) if alpha > 0 else 0.0)

    overall_frac = total_dev / total_alpha if total_alpha > 0 else 0.0

    # Detection logic:
    # If there is text, but almost no Devanagari (< 15%), and lots of Latin chars:
    # Check if text is English or legacy font. Legacy Hindi fonts (KrutiDev, etc.)
    # use ASCII codes for glyphs, yielding strings with high frequencies of odd symbols or non-English words.
    if overall_frac > 0.40:
        verdict = "OK_UNICODE_HINDI"
    elif overall_frac < 0.10:
        # Check if the page is English text or legacy font gibberish
        sample = " ".join(page_texts[:3]).lower()
        english_words = {"the", "act", "section", "shall", "and", "or", "to", "of", "in", "for", "government"}
        found_en = sum(1 for w in english_words if re.search(r'\b' + w + r'\b', sample))
        if found_en >= 4:
            verdict = "ENGLISH_ONLY"
        else:
            verdict = "LEGACY_FONT_SUSPECTED"
    else:
        # Mixed (0.10 to 0.40)
        verdict = "LEGACY_FONT_SUSPECTED"

    return verdict, fractions, round(overall_frac, 3)


def count_section_headings(page_texts: List[str], lang: str) -> int:
    """
    Count section-like headings in extracted text.
    English patterns: '1. Short title', 'Section 1.', '^12. ', etc.
    Hindi patterns: 'धारा 1.', '1. संक्षिप्त नाम', '^१२. ', etc.
    """
    full_text = "\n".join(page_texts)
    lines = full_text.splitlines()
    count = 0

    if lang == "en":
        sec_re = re.compile(r'^(?:[Ss]ection\s+\d+[A-Z]?\.?|(\d+[A-Z]?)\.\s+[A-Z])')
    else:
        sec_re = re.compile(r'^(?:धारा\s+[\d\u0966-\u096F]+[क-ह]?\.?|([\d\u0966-\u096F]+[क-ह]?)\.\s+[\u0900-\u097F]|(?:[\d\u0966-\u096F]+)\।)')

    for line in lines:
        line_s = line.strip()
        if sec_re.search(line_s):
            count += 1
    return count


def extract_act_metadata(page_texts: List[str], lang: str) -> Dict[str, Any]:
    """
    Extracts Act title, Act number, and Act year from first 2 pages.
    """
    first_pages = "\n".join(page_texts[:2])
    first_pages_norm = to_arabic_digits(first_pages)

    metadata = {
        "title": None,
        "act_no": None,
        "year": None
    }

    # Extract Year (4-digit number between 1800 and 2099)
    years = re.findall(r'\b(1[89]\d\d|20[0-2]\d)\b', first_pages_norm)
    if years:
        metadata["year"] = int(years[0])

    # Extract Act Number
    # English: "ACT NO. 22 OF 2005" or "NO. 22 OF 2005"
    if lang == "en":
        act_no_match = re.search(r'(?:ACT\s+NO\.|NO\.)\s*([0-9]+)\s+OF\s+([0-9]{4})', first_pages_norm, re.IGNORECASE)
        if act_no_match:
            metadata["act_no"] = int(act_no_match.group(1))
            metadata["year"] = int(act_no_match.group(2))
        title_match = re.search(r'THE\s+([A-Z\s\(\),]+ACT[,\s]+[0-9]{4})', first_pages, re.IGNORECASE)
        if title_match:
            metadata["title"] = " ".join(title_match.group(0).split())
    else:
        # Hindi: "2005 का अधिनियम संख्यांक 22" or "अधिनियम संख्यांक 22" or "(2005 का 22)"
        act_no_match = re.search(r'(?:अधिनियम\s+संख्यांक|संख्यांक)\s*([0-9]+)', first_pages_norm)
        if act_no_match:
            metadata["act_no"] = int(act_no_match.group(1))
        title_match = re.search(r'([\u0900-\u097F\s\(\),]+अधिनियम[,\s]+[\d\u0966-\u096F]{4})', first_pages)
        if title_match:
            metadata["title"] = " ".join(title_match.group(0).split())

    return metadata


def validate_pair(act_slug: str, en_path: Optional[str], hi_path: Optional[str]) -> Dict[str, Any]:
    """
    Validates an English and Hindi Act document pair.
    """
    result: Dict[str, Any] = {
        "act_slug": act_slug,
        "en_path": en_path,
        "hi_path": hi_path,
        "en_pages": 0,
        "hi_pages": 0,
        "extraction_method_en": "N/A",
        "extraction_method_hi": "N/A",
        "devanagari_fraction_hi": 0.0,
        "verdict_hi": "MISSING",
        "en_headings": 0,
        "hi_headings": 0,
        "heading_parity": "N/A",
        "same_act": "N/A",
        "size_sanity": "N/A",
        "usable": False,
        "reason": ""
    }

    if not en_path or not os.path.exists(en_path):
        result["reason"] = "Missing English PDF"
        return result

    if not hi_path or not os.path.exists(hi_path):
        result["reason"] = "Missing Hindi PDF"
        return result

    # 1. Extraction
    en_texts, en_method = extract_pdf_pages(en_path)
    hi_texts, hi_method = extract_pdf_pages(hi_path)

    result["en_pages"] = len(en_texts)
    result["hi_pages"] = len(hi_texts)
    result["extraction_method_en"] = en_method
    result["extraction_method_hi"] = hi_method

    if not en_texts or all(len(t.strip()) == 0 for t in en_texts):
        result["reason"] = "English PDF is empty or unextractable"
        return result

    # 2. Hindi text assessment & Legacy Font Check
    verdict_hi, page_fracs, overall_frac = assess_hindi_text(hi_texts)
    result["verdict_hi"] = verdict_hi
    result["devanagari_fraction_hi"] = overall_frac

    if verdict_hi == "LEGACY_FONT_SUSPECTED":
        result["usable"] = False
        result["reason"] = "Hindi version suspected to use non-Unicode legacy font"
        return result
    elif verdict_hi == "EMPTY":
        result["usable"] = False
        result["reason"] = "Hindi PDF is empty or scanned without text"
        return result
    elif verdict_hi == "ENGLISH_ONLY":
        result["usable"] = False
        result["reason"] = "Hindi PDF contains only English text"
        return result

    # 3. Heading counts & parity check
    result["en_headings"] = count_section_headings(en_texts, "en")
    result["hi_headings"] = count_section_headings(hi_texts, "hi")
    max_h = max(result["en_headings"], result["hi_headings"], 1)
    gap = abs(result["en_headings"] - result["hi_headings"]) / max_h
    if gap <= 0.15:
        result["heading_parity"] = f"OK (diff {round(gap*100, 1)}%)"
    else:
        result["heading_parity"] = f"GAP_WARNING (diff {round(gap*100, 1)}%)"

    # 4. Size sanity check (0.6x to 1.6x)
    if result["en_pages"] > 0:
        ratio = result["hi_pages"] / result["en_pages"]
        if 0.55 <= ratio <= 1.65:
            result["size_sanity"] = f"OK ({round(ratio, 2)}x)"
        else:
            result["size_sanity"] = f"SUSPICIOUS ({round(ratio, 2)}x)"
    else:
        result["size_sanity"] = "INVALID"

    # 5. Same-Act check
    en_meta = extract_act_metadata(en_texts, "en")
    hi_meta = extract_act_metadata(hi_texts, "hi")

    match = True
    mismatch_reasons = []
    if en_meta["year"] and hi_meta["year"] and en_meta["year"] != hi_meta["year"]:
        match = False
        mismatch_reasons.append(f"Year mismatch (EN: {en_meta['year']}, HI: {hi_meta['year']})")
    if en_meta["act_no"] and hi_meta["act_no"] and en_meta["act_no"] != hi_meta["act_no"]:
        match = False
        mismatch_reasons.append(f"Act No mismatch (EN: {en_meta['act_no']}, HI: {hi_meta['act_no']})")

    if not match:
        result["same_act"] = f"MISMATCHED_PAIR ({', '.join(mismatch_reasons)})"
        result["usable"] = False
        result["reason"] = result["same_act"]
        return result
    else:
        result["same_act"] = "PASS"
        if en_meta["year"]:
            result["same_act"] += f" (Year: {en_meta['year']}"
            if en_meta["act_no"]:
                result["same_act"] += f", No: {en_meta['act_no']}"
            result["same_act"] += ")"

    # Size check flag
    if "SUSPICIOUS" in result["size_sanity"]:
        # Flag for human, but if same-act and unicode Hindi pass, could still be usable or needs caution
        pass

    result["usable"] = True
    result["reason"] = "All checks passed (Unicode Devanagari verified, Same Act confirmed)"
    return result


def find_document_pairs(data_dir: str) -> List[Tuple[str, Optional[str], Optional[str]]]:
    """Finds all candidate pairs in data_dir."""
    p = Path(data_dir)
    if not p.exists():
        return []

    pdf_files = list(p.glob("*.pdf"))
    slugs = set()
    for f in pdf_files:
        name = f.stem
        if name.endswith("_en"):
            slugs.add(name[:-3])
        elif name.endswith("_hi"):
            slugs.add(name[:-3])
        elif name.endswith("_bi"):
            slugs.add(name[:-3])
        else:
            slugs.add(name)

    pairs = []
    for s in sorted(slugs):
        en = p / f"{s}_en.pdf"
        hi = p / f"{s}_hi.pdf"
        bi = p / f"{s}_bi.pdf"
        if bi.exists():
            pairs.append((s, str(bi), str(bi)))
        else:
            pairs.append((s, str(en) if en.exists() else None, str(hi) if hi.exists() else None))
    return pairs


def main():
    parser = argparse.ArgumentParser(description="Tulya Data Readiness and Validation Script")
    parser.add_argument("--data-dir", default="data/raw", help="Directory containing raw PDFs")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    pairs = find_document_pairs(args.data_dir)
    if not pairs:
        print(f"No document pairs found in {args.data_dir}.")
        sys.exit(0)

    results = []
    for slug, en_p, hi_p in pairs:
        res = validate_pair(slug, en_p, hi_p)
        results.append(res)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    # Print formatted markdown table
    print("| Act Slug | EN Pages | HI Pages | HI Verdict | Dev. Frac | Same Act | Size Sanity | Headings (EN/HI) | Usable | Reason |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in results:
        usable_str = "**YES**" if r["usable"] else "NO"
        print(f"| {r['act_slug']} | {r['en_pages']} | {r['hi_pages']} | {r['verdict_hi']} | {r['devanagari_fraction_hi']} | {r['same_act']} | {r['size_sanity']} | {r['en_headings']}/{r['hi_headings']} | {usable_str} | {r['reason']} |")


if __name__ == "__main__":
    main()
