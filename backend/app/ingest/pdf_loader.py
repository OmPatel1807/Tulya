"""
pdf_loader.py - Extracts text from PDF files with PyMuPDF and pdfplumber fallback.
Returns a list of page dicts: [{'page_no': int, 'raw_text': str, 'method': str}]
"""

import os
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
    Attempts PyMuPDF first. If a page yields fewer than 30 characters and has no images
    or if PyMuPDF fails, falls back to pdfplumber for that page.
    """
    path_obj = Path(pdf_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    pages: List[Dict[str, Any]] = []

    if fitz is None and pdfplumber is None:
        raise ImportError("Neither PyMuPDF nor pdfplumber is installed.")

    # 1. Primary extraction with PyMuPDF
    if fitz is not None:
        try:
            doc = fitz.open(pdf_path)
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

                pages.append({
                    "page_no": page_no,
                    "raw_text": text,
                    "method": method
                })
            doc.close()
            return pages
        except Exception as e:
            # If PyMuPDF crashes completely on the document, try full pdfplumber
            if pdfplumber is None:
                raise RuntimeError(f"PyMuPDF failed and pdfplumber is not available: {e}")

    # 2. Complete fallback to pdfplumber
    if pdfplumber is not None:
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages):
                page_no = page_index + 1
                text = page.extract_text(layout=True) or page.extract_text() or ""
                pages.append({
                    "page_no": page_no,
                    "raw_text": text,
                    "method": "pdfplumber"
                })
        return pages

    return pages
