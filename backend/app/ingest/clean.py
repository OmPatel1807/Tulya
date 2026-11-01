"""
clean.py - Text cleaning, Unicode NFC normalization, header/footer stripping,
amendment footnote separation (annotations), and hyphenated line break repair for legal texts.
"""

import re
import unicodedata
from typing import List, Dict, Any, Set, Tuple, Union
from collections import Counter

PAGE_NUM_RE = re.compile(r'^\s*(?:\[\s*\d+\s*\]|\d+|[\u0966-\u096F]+|\b[Pp]age\s+\d+(?:\s+of\s+\d+)?)\s*$')
CLAUSE_HEADING_RE = re.compile(r'^\s*(?:[Ss]ection\s+\d+|धारा\s+[\d\u0966-\u096F]+|\d+[A-Z]?\.\s+[A-Z]|[\d\u0966-\u096F]+[क-ह]?\.\s+[\u0900-\u097F])')

FOOTNOTE_HI_RE = re.compile(
    r'^\s*([0-9\u0966-\u096F]+)\s*(?:[0-9\u0966-\u096F]{4}\s+के\s+.*?(?:अधिनियम|अिधिनयम|सं०|धारा|लोप|प्रतिस्थापित|अंतःस्थापित)|(?:अधिनियम|अिधिनयम)\s+सं०|द्वारा\s*\([0-9\u0966-\u096F\.\-]+|\([0-9\u0966-\u096F\.\-]+\s*से\)|लोप\s*किया\s*गया|प्रतिस्थापित|अंतःस्थापित|शब्दों\s*का\s*लोप)'
)
FOOTNOTE_EN_RE = re.compile(
    r'^\s*([0-9]+)\.?\s*(?:The\s+words?|Subs\.|Ins\.|Omitted\s+by|Act\s+\d+\s+of\s+\d+|\(w\.e\.f\.)',
    re.IGNORECASE
)
FOOTNOTE_DIVIDER_RE = re.compile(r'^\s*_{3,}\s*$')


def normalize_unicode(text: str) -> str:
    """
    Normalizes text to Unicode NFC and cleans zero-width artifacts.
    """
    if not text:
        return ""
    norm = unicodedata.normalize('NFC', text)
    norm = norm.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '').replace('\xad', '').replace('\u25cc', '')
    return norm


def repair_hyphenation(text: str) -> str:
    """
    Repairs words broken across lines with hyphens.
    e.g. 'infor-\nmation' -> 'information'
    e.g. 'अधि-\nनियम' -> 'अधिनियम'
    """
    text = re.sub(r'([a-zA-Z]+)-\s*\n\s*([a-zA-Z]+)', r'\1\2', text)
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
        candidates = lines[:4] + lines[-4:] if len(lines) > 8 else lines
        seen_in_page = set()
        for l in candidates:
            if len(l) < 3 or CLAUSE_HEADING_RE.match(l):
                continue
            norm_l = " ".join(l.split())
            if norm_l not in seen_in_page:
                seen_in_page.add(norm_l)
                top_bottom_lines.append(norm_l)

    counts = Counter(top_bottom_lines)
    repeated = {line for line, count in counts.items() if count >= min_repeats}
    return repeated


def clean_page_text(
    raw_text: str,
    repeated_lines: Set[str],
    return_annotations: bool = False
) -> Union[str, Tuple[str, List[str]]]:
    """
    Cleans a single page of text:
    - Normalizes Unicode NFC
    - Strips repeated headers/footers and page numbers
    - Separates amendment footnotes into annotations so they do not pollute clause text
    - Normalizes inline whitespace and repairs hyphenation
    """
    text = normalize_unicode(raw_text)
    raw_lines = text.splitlines()
    cleaned_lines: List[str] = []
    annotations: List[str] = []

    total_lines = len(raw_lines)
    in_footnote_block = False

    for idx, line in enumerate(raw_lines):
        line_s = " ".join(line.strip().split())
        if not line_s:
            continue

        # Check edge lines for repeated headers/footers or page numbers
        is_edge_line = (idx < 4 or idx >= total_lines - 4)
        if is_edge_line and line_s in repeated_lines:
            continue

        if is_edge_line and PAGE_NUM_RE.match(line_s):
            continue

        if is_edge_line and line_s.lower() in {"indiacode", "www.indiacode.nic.in", "extraordinary", "असाधारण"}:
            continue

        # Check for footnote divider or amendment footnote
        if idx >= max(0, total_lines - 12):
            if FOOTNOTE_DIVIDER_RE.match(line_s):
                in_footnote_block = True
                continue

            if FOOTNOTE_HI_RE.match(line_s) or FOOTNOTE_EN_RE.match(line_s):
                in_footnote_block = True
                annotations.append(line_s)
                continue

            if in_footnote_block:
                # Continuation of footnote
                annotations.append(line_s)
                continue

        cleaned_lines.append(line_s)

    joined = "\n".join(cleaned_lines)
    repaired = repair_hyphenation(joined)

    if return_annotations:
        return repaired, annotations
    return repaired


def clean_stream(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes a list of page dicts [{'page_no': int, 'raw_text': str}]
    Detects repeated headers/footers, cleans each page, and extracts annotations.
    Returns cleaned page dicts.
    """
    raw_page_texts = [p.get("raw_text", "") for p in pages]
    repeated_lines = detect_repeated_headers_footers(raw_page_texts)

    cleaned_pages = []
    for p in pages:
        page_no = p.get("page_no", 1)
        raw_text = p.get("raw_text", "")
        cleaned_text, annotations = clean_page_text(raw_text, repeated_lines, return_annotations=True)

        cleaned_pages.append({
            "page_no": page_no,
            "text": cleaned_text,
            "raw_text": raw_text,
            "annotations": annotations,
            "method": p.get("method", "PyMuPDF"),
            "lines_count": len(cleaned_text.splitlines()) if cleaned_text else 0
        })

    return cleaned_pages
