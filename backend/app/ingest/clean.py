"""
clean.py - Text cleaning, Unicode NFC normalization, header/footer stripping,
and hyphenated line break repair for legal texts.
"""

import re
import unicodedata
from typing import List, Dict, Any, Set, Tuple
from collections import Counter

PAGE_NUM_RE = re.compile(r'^\s*(?:\[\s*\d+\s*\]|\d+|[\u0966-\u096F]+|\b[Pp]age\s+\d+(?:\s+of\s+\d+)?)\s*$')
CLAUSE_HEADING_RE = re.compile(r'^\s*(?:[Ss]ection\s+\d+|धारा\s+[\d\u0966-\u096F]+|\d+[A-Z]?\.\s+[A-Z]|[\d\u0966-\u096F]+[क-ह]?\.\s+[\u0900-\u097F])')


def normalize_unicode(text: str) -> str:
    """
    Normalizes text to Unicode NFC and cleans zero-width artifacts.
    """
    if not text:
        return ""
    # NFC normalization
    norm = unicodedata.normalize('NFC', text)
    # Remove zero-width spaces, soft hyphens, and BOM
    norm = norm.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '').replace('\xad', '')
    return norm


def repair_hyphenation(text: str) -> str:
    """
    Repairs words broken across lines with hyphens.
    e.g. 'infor-\nmation' -> 'information'
    e.g. 'अधि-\nनियम' -> 'अधिनियम'
    """
    # English word breaks across line
    text = re.sub(r'([a-zA-Z]+)-\s*\n\s*([a-zA-Z]+)', r'\1\2', text)
    # Devanagari word breaks across line
    text = re.sub(r'([\u0900-\u097F]+)-\s*\n\s*([\u0900-\u097F]+)', r'\1\2', text)
    return text


def detect_repeated_headers_footers(raw_pages: List[str], threshold: float = 0.20) -> Set[str]:
    """
    Identifies lines in top 4 or bottom 4 lines that repeat across more than
    threshold fraction of pages (min 2 occurrences).
    Never marks clause headings or section labels as headers/footers.
    """
    if len(raw_pages) <= 1:
        return set()

    top_bottom_lines = []
    min_repeats = max(2, int(len(raw_pages) * threshold))

    for p in raw_pages:
        lines = [l.strip() for l in p.splitlines() if l.strip()]
        if not lines:
            continue
        # Check first 4 and last 4 lines
        candidates = lines[:4] + lines[-4:] if len(lines) > 8 else lines
        seen_in_page = set()
        for l in candidates:
            # Don't consider single characters or clause headings
            if len(l) < 3 or CLAUSE_HEADING_RE.match(l):
                continue
            # Strip trailing/leading digits or punctuation variations for grouping
            norm_l = " ".join(l.split())
            if norm_l not in seen_in_page:
                seen_in_page.add(norm_l)
                top_bottom_lines.append(norm_l)

    counts = Counter(top_bottom_lines)
    repeated = {line for line, count in counts.items() if count >= min_repeats}
    return repeated


def clean_page_text(raw_text: str, repeated_lines: Set[str]) -> str:
    """
    Cleans a single page of text:
    - Normalizes Unicode NFC
    - Removes repeated headers/footers
    - Removes isolated page numbers
    - Repairs hyphenation
    - Normalizes inline whitespace while preserving paragraph lines
    """
    text = normalize_unicode(raw_text)
    raw_lines = text.splitlines()
    cleaned_lines = []

    total_lines = len(raw_lines)
    for idx, line in enumerate(raw_lines):
        line_s = " ".join(line.strip().split())

        # Check if line matches repeated header/footer in top 4 or bottom 4
        is_edge_line = (idx < 4 or idx >= total_lines - 4)
        if is_edge_line and line_s in repeated_lines:
            continue

        # Check for isolated page number
        if is_edge_line and PAGE_NUM_RE.match(line_s):
            continue

        # Filter out standalone website watermark stamps on first/last lines
        if is_edge_line and line_s.lower() in {"indiacode", "www.indiacode.nic.in", "extraordinary", "असाधारण"}:
            continue

        if line_s:
            cleaned_lines.append(line_s)

    joined = "\n".join(cleaned_lines)
    # Repair hyphenation across lines
    repaired = repair_hyphenation(joined)
    return repaired


def clean_stream(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes a list of page dicts [{'page_no': int, 'raw_text': str}]
    Detects repeated headers/footers and cleans each page.
    Returns cleaned page dicts.
    """
    raw_page_texts = [p.get("raw_text", "") for p in pages]
    repeated_lines = detect_repeated_headers_footers(raw_page_texts)

    cleaned_pages = []
    for p in pages:
        page_no = p.get("page_no", 1)
        raw_text = p.get("raw_text", "")
        cleaned_text = clean_page_text(raw_text, repeated_lines)

        cleaned_pages.append({
            "page_no": page_no,
            "text": cleaned_text,
            "raw_text": raw_text,
            "method": p.get("method", "PyMuPDF"),
            "lines_count": len(cleaned_text.splitlines()) if cleaned_text else 0
        })

    return cleaned_pages
