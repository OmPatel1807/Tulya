"""
pdf_loader.py - Extracts text from PDF files with PyMuPDF and pdfplumber fallback.
Applies automated TrueType CMap repair and Devanagari visual-to-logical reordering.
Returns a list of page dicts: [{'page_no': int, 'raw_text': str, 'method': str, 'hindi_quality': dict, 'is_reliable': bool}]
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from backend.app.ingest.hindi_repair import repair_pdf_cmaps, repair_hindi_text
from backend.app.ingest.script_check import hindi_word_validity

DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')


def extract_page_pdfplumber(pdf_path: str, page_index: int) -> str:
    """Fallback extraction of a single page using pdfplumber."""
    if pdfplumber is None:
        return ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_index < len(pdf.pages):
                page = pdf.pages[page_index]
                text = page.extract_text(layout=True) or page.extract_text() or ""
                return text
    except Exception:
        pass
    return ""


def extract_text(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text page by page from a PDF file.
    Applies in-memory TrueType CMap repair to fix glyph-to-Unicode mapping bugs,
    followed by Devanagari Unicode logical reordering.
    Evaluates lexical quality against the bundled Hindi dictionary.
    """
    path_obj = Path(pdf_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    pages: List[Dict[str, Any]] = []

    if fitz is None and pdfplumber is None:
        raise ImportError("Neither PyMuPDF nor pdfplumber is installed.")

    # 1. Primary extraction with PyMuPDF + CMap Repair
    if fitz is not None:
        try:
            doc = fitz.open(pdf_path)
            # Apply in-memory CMap repair for TrueType embedded fonts
            repair_pdf_cmaps(doc)

            for page_index, page in enumerate(doc):
                page_no = page_index + 1
                text = page.get_text("text") or ""

                # Check if page yielded very little text (< 30 chars), try pdfplumber fallback
                method = "PyMuPDF"
                if len(text.strip()) < 30 and pdfplumber is not None:
                    fallback_text = extract_page_pdfplumber(pdf_path, page_index)
                    if len(fallback_text.strip()) > len(text.strip()):
                        text = fallback_text
                        method = "pdfplumber_fallback"

                # If text contains Devanagari, apply Unicode logical reordering and repair
                hindi_q = None
                is_rel = True
                if DEVANAGARI_RE.search(text):
                    text = repair_hindi_text(text)
                    hindi_q = hindi_word_validity(text)
                    is_rel = (hindi_q.get("verdict") == "ok")

                pages.append({
                    "page_no": page_no,
                    "raw_text": text,
                    "method": method,
                    "hindi_quality": hindi_q,
                    "is_reliable": is_rel
                })
            doc.close()
            return pages
        except Exception as e:
            if pdfplumber is None:
                raise RuntimeError(f"PyMuPDF failed and pdfplumber is not available: {e}")

    # 2. Complete fallback to pdfplumber
    if pdfplumber is not None:
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages):
                page_no = page_index + 1
                text = page.extract_text(layout=True) or page.extract_text() or ""
                hindi_q = None
                is_rel = True
                if DEVANAGARI_RE.search(text):
                    text = repair_hindi_text(text)
                    hindi_q = hindi_word_validity(text)
                    is_rel = (hindi_q.get("verdict") == "ok")

                pages.append({
                    "page_no": page_no,
                    "raw_text": text,
                    "method": "pdfplumber",
                    "hindi_quality": hindi_q,
                    "is_reliable": is_rel
                })
        return pages

    return pages
