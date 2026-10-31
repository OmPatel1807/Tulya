"""
comparator.py - Compares Factual Spans Between English and Hindi Clauses.
Recognizes equivalence across surface forms (e.g. '10', 'ten', 'दस', '१०'),
flags value and unit discrepancies with exact evidence spans, and identifies
known syntactic limit cases ('needs semantic stage').
"""

import re
from typing import List, Tuple, Set, Optional

from backend.app.facts.models import (
    FactType,
    FactSpan,
    FactDifference,
    FactComparisonResult
)
from backend.app.facts.extractor import extract_facts


# Additive formula patterns (known limit detection: "tax plus ten times" vs "ten times")
ADDITIVE_PATTERNS_EN = re.compile(
    r'\b(?:plus|in\s+addition\s+to|together\s+with|as\s+well\s+as|along\s+with)\b',
    re.IGNORECASE
)
ADDITIVE_PATTERNS_HI = re.compile(
    r'(?:के\s+अतिरिक्त|के\s+अलावा|सहित|तथा\s+साथ\s+ही|जोड़कर)',
    re.UNICODE
)


def compare_clause_facts(
    en_text: str,
    hi_text: str,
    en_path: Optional[str] = None,
    hi_path: Optional[str] = None
) -> FactComparisonResult:
    """
    Extracts and compares all facts between English and Hindi text spans.
    Returns FactComparisonResult containing matched pairs and flagged differences.
    """
    en_facts = extract_facts(en_text)
    hi_facts = extract_facts(hi_text)

    matched_pairs: List[Tuple[FactSpan, FactSpan]] = []
    differences: List[FactDifference] = []

    unmatched_en: List[FactSpan] = []
    unmatched_hi: List[FactSpan] = list(hi_facts)

    # 1. First pass: find exact factual equivalents across surface forms
    for e_fact in en_facts:
        found_match = False
        for i, h_fact in enumerate(unmatched_hi):
            if e_fact.is_equivalent(h_fact):
                matched_pairs.append((e_fact, h_fact))
                unmatched_hi.pop(i)
                found_match = True
                break
        if not found_match:
            unmatched_en.append(e_fact)

    # 2. Second pass: pair unmatched facts of the same type to detect VALUE or UNIT mismatches
    remaining_en: List[FactSpan] = []
    for e_fact in unmatched_en:
        paired = False
        for i, h_fact in enumerate(unmatched_hi):
            if e_fact.fact_type == h_fact.fact_type:
                # Same fact type, but different value or unit!
                status = "UNIT_MISMATCH" if e_fact.unit != h_fact.unit else "VALUE_MISMATCH"
                diff = FactDifference(
                    fact_type=e_fact.fact_type,
                    status=status,
                    en_fact=e_fact,
                    hi_fact=h_fact,
                    description=f"{status} in {e_fact.fact_type.value}: English has '{e_fact.raw_text}' ({e_fact.normalized_value} {e_fact.unit or ''}), Hindi has '{h_fact.raw_text}' ({h_fact.normalized_value} {h_fact.unit or ''})".strip(),
                    evidence_en=e_fact.raw_text,
                    evidence_hi=h_fact.raw_text,
                    needs_semantic_stage=False
                )
                differences.append(diff)
                unmatched_hi.pop(i)
                paired = True
                break
        if not paired:
            remaining_en.append(e_fact)

    # 3. Third pass: unpaired English facts are MISSING_IN_HI
    for e_fact in remaining_en:
        differences.append(
            FactDifference(
                fact_type=e_fact.fact_type,
                status="MISSING_IN_HI",
                en_fact=e_fact,
                hi_fact=None,
                description=f"Fact present in English ('{e_fact.raw_text}') is absent in Hindi",
                evidence_en=e_fact.raw_text,
                evidence_hi="",
                needs_semantic_stage=False
            )
        )

    # 4. Fourth pass: unpaired Hindi facts are MISSING_IN_EN
    for h_fact in unmatched_hi:
        differences.append(
            FactDifference(
                fact_type=h_fact.fact_type,
                status="MISSING_IN_EN",
                en_fact=None,
                hi_fact=h_fact,
                description=f"Fact present in Hindi ('{h_fact.raw_text}') is absent in English",
                evidence_en="",
                evidence_hi=h_fact.raw_text,
                needs_semantic_stage=False
            )
        )

    # 5. Check for known syntactic limit: "tax plus penalty of ten times tax" vs "ten times the tax"
    # When multiplier or numbers match, but one stream has an additive clause while other does not
    has_additive_en = bool(ADDITIVE_PATTERNS_EN.search(en_text))
    has_additive_hi = bool(ADDITIVE_PATTERNS_HI.search(hi_text))

    if has_additive_en != has_additive_hi:
        # Check if both have matching multiplier or penalty facts
        mult_matches = [
            (ef, hf) for ef, hf in matched_pairs
            if ef.fact_type in (FactType.MULTIPLIER, FactType.PERCENT, FactType.MONEY)
        ]
        if mult_matches:
            differences.append(
                FactDifference(
                    fact_type=mult_matches[0][0].fact_type,
                    status="POTENTIAL_STRUCTURAL_DIFF",
                    en_fact=mult_matches[0][0],
                    hi_fact=mult_matches[0][1],
                    description="Additive syntax discrepancy ('plus / in addition to' vs pure multiplier): numbers alone cannot verify full liability. Recorded as: needs semantic stage",
                    evidence_en=en_text[:120],
                    evidence_hi=hi_text[:120],
                    needs_semantic_stage=True
                )
            )

    return FactComparisonResult(
        clause_path_en=en_path,
        clause_path_hi=hi_path,
        en_facts=en_facts,
        hi_facts=hi_facts,
        matched_pairs=matched_pairs,
        differences=differences
    )
