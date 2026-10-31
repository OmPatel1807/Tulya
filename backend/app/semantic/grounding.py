"""
grounding.py - Grounding Guard (Rule R2) for Semantic Findings.

Rule R2:
  Every finding quotes evidence from BOTH versions (or null when content is genuinely missing).
  A quote returned by the LLM that is not a substring of the source clause (after Unicode
  and whitespace normalization) is discarded and counted in ungrounded_discard_rate.
"""

import re
import unicodedata
from typing import List, Tuple, Optional
from backend.app.semantic.models import SemanticFinding


def normalize_quote_text(text: Optional[str]) -> str:
    """
    Normalizes whitespace, punctuation, quotes, and Unicode for robust substring matching.
    """
    if not text:
        return ""
    # Unicode NFKC normalization
    s = unicodedata.normalize("NFKC", text)
    # Normalize fancy quotes and dashes
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.replace("—", "-").replace("–", "-")
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def is_substring_grounded(quote: Optional[str], source_text: str) -> bool:
    """
    Verifies that quote (if present and non-empty) is an exact substring of source_text
    after Unicode and whitespace normalization.
    If quote is None or empty (allowed when content is missing), returns True.
    """
    if quote is None:
        return True
    norm_quote = normalize_quote_text(quote)
    if not norm_quote:
        return True

    norm_source = normalize_quote_text(source_text)
    # Check substring (case-insensitive for Latin, direct for Devanagari)
    return norm_quote.lower() in norm_source.lower()


def validate_grounding(
    finding: SemanticFinding,
    en_source: str,
    hi_source: str
) -> Tuple[bool, str]:
    """
    Validates a SemanticFinding against English and Hindi source texts under Rule R2.
    Returns (is_valid, failure_reason).
    """
    q_en = finding.quote_en
    q_hi = finding.quote_hi

    # At least one quote must be present (a finding cannot have no evidence at all)
    if (not q_en or not q_en.strip()) and (not q_hi or not q_hi.strip()):
        return False, "Finding contains neither English nor Hindi evidence quotes"

    # If quote_en is present, it must be grounded in en_source
    if q_en and q_en.strip():
        if not is_substring_grounded(q_en, en_source):
            return False, f"English quote '{q_en[:60]}...' not found in English clause"

    # If quote_hi is present, it must be grounded in hi_source
    if q_hi and q_hi.strip():
        if not is_substring_grounded(q_hi, hi_source):
            return False, f"Hindi quote '{q_hi[:60]}...' not found in Hindi clause"

    return True, ""


def filter_findings_by_grounding(
    findings: List[SemanticFinding],
    en_source: str,
    hi_source: str
) -> Tuple[List[SemanticFinding], List[SemanticFinding]]:
    """
    Filters a list of semantic findings against the source clauses.
    Returns (grounded_findings, discarded_findings).
    """
    grounded: List[SemanticFinding] = []
    discarded: List[SemanticFinding] = []

    for f in findings:
        valid, _ = validate_grounding(f, en_source, hi_source)
        if valid:
            grounded.append(f)
        else:
            discarded.append(f)

    return grounded, discarded
