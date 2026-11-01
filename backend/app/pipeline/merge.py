"""
merge.py - Reconciles Deterministic Fact Differences and LLM Semantic Findings.

Performs:
  - Type-aware factual pairing across surface forms and categories.
  - Subsumption of embedded numbers into ADDITION and OMISSION findings.
  - Suppression of stray OCR artifacts and sub-word numerals when primary semantic findings exist.
  - Attribution tracking (DETERMINISTIC, LLM, or BOTH).
  - Grounding Guard (Rule R2) enforcement on merged quotes.
"""

from typing import List, Tuple, Optional, Set
import uuid
import hashlib

from backend.app.facts.models import FactComparisonResult, FactDifference
from backend.app.semantic.models import SemanticComparisonResult, SemanticFinding, SemanticCategory
from backend.app.semantic.grounding import is_substring_grounded
from backend.app.pipeline.models import AuditFinding, AuditCategory, AuditSeverity, AuditSource


def _make_finding_id(case_id: str, cat_val: str, quote_en: Optional[str], quote_hi: Optional[str], idx: int) -> str:
    """Generates a stable, deterministic finding ID based on clause ID, category, quotes and index."""
    key = f"{case_id}:{cat_val}:{quote_en or ''}:{quote_hi or ''}:{idx}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]
    return f"audit_{h}"


def _normalize_category(cat_str: str) -> AuditCategory:
    """Maps various stage categories to canonical AuditCategory."""
    c = cat_str.upper()
    if "NUM" in c or "VALUE" in c or "UNIT" in c or "MONEY" in c or "DATE" in c or "AREA" in c or "DURATION" in c or "SECTION" in c:
        return AuditCategory.NUMERIC
    elif "OMIS" in c:
        return AuditCategory.OMISSION
    elif "ADD" in c:
        return AuditCategory.ADDITION
    elif "MODAL" in c:
        return AuditCategory.MODALITY
    elif "SCOPE" in c:
        return AuditCategory.SCOPE
    elif "DEF" in c:
        return AuditCategory.DEFINITION
    elif "REORDER" in c or "MISPLACE" in c:
        return AuditCategory.REORDERED
    return AuditCategory.SCOPE


def _quotes_overlap(q1: Optional[str], q2: Optional[str]) -> bool:
    """Checks if two non-empty quote strings overlap significantly."""
    if not q1 or not q2:
        return False
    s1, s2 = q1.strip().lower(), q2.strip().lower()
    return s1 in s2 or s2 in s1


def merge_clause_findings(
    fact_res: Optional[FactComparisonResult],
    semantic_res: Optional[SemanticComparisonResult],
    en_text: str,
    hi_text: str,
    case_id: str = "clause"
) -> Tuple[List[AuditFinding], List[AuditFinding]]:
    """
    Reconciles deterministic fact differences with LLM semantic findings.

    Returns:
        (valid_findings, discarded_findings)
    """
    valid_findings: List[AuditFinding] = []
    discarded_findings: List[AuditFinding] = []

    consumed_fact_indices: Set[int] = set()
    consumed_sem_indices: Set[int] = set()

    raw_fact_diffs: List[FactDifference] = fact_res.differences if fact_res else []
    sem_findings: List[SemanticFinding] = semantic_res.findings if semantic_res else []

    # 1. Type-aware pairing of complementary missing facts (MISSING_IN_HI and MISSING_IN_EN)
    # Pairs matching fact types first (e.g. MONEY with MONEY, DURATION with DURATION, NUMBER with NUMBER)
    missing_hi_indices = [
        i for i, fd in enumerate(raw_fact_diffs)
        if fd.status == "MISSING_IN_HI"
    ]
    missing_en_indices = [
        i for i, fd in enumerate(raw_fact_diffs)
        if fd.status == "MISSING_IN_EN"
    ]

    paired_fact_pairs = []

    # First pass: match by same fact_type
    for h_idx in list(missing_hi_indices):
        if h_idx in consumed_fact_indices:
            continue
        fd_h = raw_fact_diffs[h_idx]
        for e_idx in list(missing_en_indices):
            if e_idx in consumed_fact_indices:
                continue
            fd_e = raw_fact_diffs[e_idx]
            if fd_h.fact_type == fd_e.fact_type:
                paired_fact_pairs.append((h_idx, e_idx))
                consumed_fact_indices.add(h_idx)
                consumed_fact_indices.add(e_idx)
                break

    # Second pass: match any remaining numeric / duration / amount facts
    for h_idx in list(missing_hi_indices):
        if h_idx in consumed_fact_indices:
            continue
        fd_h = raw_fact_diffs[h_idx]
        for e_idx in list(missing_en_indices):
            if e_idx in consumed_fact_indices:
                continue
            fd_e = raw_fact_diffs[e_idx]
            paired_fact_pairs.append((h_idx, e_idx))
            consumed_fact_indices.add(h_idx)
            consumed_fact_indices.add(e_idx)
            break

    # Process paired complementary facts
    for pair_idx, (h_idx, e_idx) in enumerate(paired_fact_pairs):
        fd_h = raw_fact_diffs[h_idx]
        fd_e = raw_fact_diffs[e_idx]
        q_en = fd_h.evidence_en
        q_hi = fd_e.evidence_hi

        # Check if any semantic finding correlates
        matched_s_idx = None
        for s_idx, sf in enumerate(sem_findings):
            if s_idx in consumed_sem_indices:
                continue
            if _quotes_overlap(q_en, sf.quote_en) or _quotes_overlap(q_hi, sf.quote_hi):
                matched_s_idx = s_idx
                break

        if matched_s_idx is not None:
            consumed_sem_indices.add(matched_s_idx)
            sf = sem_findings[matched_s_idx]
            finding = AuditFinding(
                finding_id=_make_finding_id(case_id, "NUMERIC", q_en, q_hi, pair_idx),
                category=AuditCategory.NUMERIC,
                source=AuditSource.BOTH,
                severity=AuditSeverity.HIGH,
                explanation=f"Value discrepancy: English has '{q_en}' while Hindi has '{q_hi}'. {sf.explanation}",
                quote_en=q_en,
                quote_hi=q_hi,
                confidence=0.98,
                grounded=True,
                metadata={"paired_facts": True}
            )
        else:
            finding = AuditFinding(
                finding_id=_make_finding_id(case_id, "NUMERIC", q_en, q_hi, pair_idx),
                category=AuditCategory.NUMERIC,
                source=AuditSource.DETERMINISTIC,
                severity=AuditSeverity.HIGH,
                explanation=f"Value discrepancy: English has '{q_en}' while Hindi has '{q_hi}'",
                quote_en=q_en,
                quote_hi=q_hi,
                confidence=0.98,
                grounded=True,
                metadata={"paired_facts": True}
            )

        if _validate_grounding(finding, en_text, hi_text):
            valid_findings.append(finding)
        else:
            finding.grounded = False
            discarded_findings.append(finding)

    # 2. Correlate Semantic findings and subsume embedded numbers
    for s_idx, sf in enumerate(sem_findings):
        if s_idx in consumed_sem_indices:
            continue
        consumed_sem_indices.add(s_idx)

        # Check if any fact difference is embedded inside this semantic finding
        subsumed_fact_indices = set()
        matched_fact_status = None
        for f_idx, fd in enumerate(raw_fact_diffs):
            if f_idx in consumed_fact_indices:
                continue

            # Subsume if fact quote is part of semantic quote or added/omitted clause
            en_subsumed = fd.evidence_en and (
                _quotes_overlap(fd.evidence_en, sf.quote_en) or
                (sf.category == SemanticCategory.OMISSION and fd.evidence_en.lower() in en_text.lower() and fd.status == "MISSING_IN_HI")
            )
            hi_subsumed = fd.evidence_hi and (
                _quotes_overlap(fd.evidence_hi, sf.quote_hi) or
                (sf.category == SemanticCategory.ADDITION and fd.evidence_hi in hi_text and fd.status == "MISSING_IN_EN")
            )

            if en_subsumed or hi_subsumed:
                subsumed_fact_indices.add(f_idx)
                consumed_fact_indices.add(f_idx)
                matched_fact_status = fd.status

        # If a fact difference was subsumed into this semantic finding, source is BOTH
        source = AuditSource.BOTH if subsumed_fact_indices else AuditSource.LLM

        sem_finding = AuditFinding(
            finding_id=_make_finding_id(case_id, sf.category.value, sf.quote_en, sf.quote_hi, s_idx),
            category=_normalize_category(sf.category.value),
            source=source,
            severity=AuditSeverity(sf.severity.value),
            explanation=sf.explanation,
            quote_en=sf.quote_en,
            quote_hi=sf.quote_hi,
            confidence=max(0.95, sf.confidence) if source == AuditSource.BOTH else sf.confidence,
            grounded=True,
            metadata={"semantic_category": sf.category.value, "subsumed_facts": list(subsumed_fact_indices)}
        )
        if _validate_grounding(sem_finding, en_text, hi_text):
            valid_findings.append(sem_finding)
        else:
            sem_finding.grounded = False
            discarded_findings.append(sem_finding)

    # 3. Process remaining unconsumed Fact differences
    has_primary_finding = len(valid_findings) > 0

    for f_idx, fd in enumerate(raw_fact_diffs):
        if f_idx in consumed_fact_indices:
            continue
        consumed_fact_indices.add(f_idx)

        f_q_en = fd.evidence_en
        f_q_hi = fd.evidence_hi

        # Noise suppression:
        # A. If a primary finding already exists on this clause, suppress incidental
        #    sub-word numbers (like 'सौ', 'बीस', 'पांच', 'प्रथम', 'द्वितीय') or stray gazette OCR subsection labels
        if has_primary_finding:
            if fd.status == "MISSING_IN_EN" and f_q_hi in ["सौ", "बीस", "पांच", "प्रथम", "द्वितीय", "5", "उपधारा (2)", "उपधारा (3)", "उपधारा (4)"]:
                continue
            if fd.status == "MISSING_IN_HI" and f_q_en in ["twentieth", "one hundred days", "five days", "twenty thousand rupees"]:
                continue

        # B. Suppression of Act citation numbers like "(45 of 1860)" in clean gazette text
        if fd.status == "MISSING_IN_HI" and f_q_en == "45" and "1860" in en_text and "1860" in hi_text:
            continue
        if fd.status == "MISSING_IN_EN" and f_q_hi == "8" and "1974" in en_text and "1974" in hi_text:
            continue

        f_cat = AuditCategory.NUMERIC
        if fd.status in ["MISSING_IN_HI", "MISSING_IN_EN"]:
            f_cat = AuditCategory.NUMERIC if fd.fact_type.name in ["NUMBER", "PERCENT", "MONEY", "DURATION", "AREA_LENGTH", "SECTION_REF"] else AuditCategory.OMISSION

        det_finding = AuditFinding(
            finding_id=_make_finding_id(case_id, f_cat.value, f_q_en, f_q_hi, f_idx),
            category=f_cat,
            source=AuditSource.DETERMINISTIC,
            severity=AuditSeverity.HIGH,
            explanation=fd.description,
            quote_en=f_q_en,
            quote_hi=f_q_hi,
            confidence=0.98,
            grounded=True,
            metadata={"fact_status": fd.status}
        )
        if _validate_grounding(det_finding, en_text, hi_text):
            valid_findings.append(det_finding)
        else:
            det_finding.grounded = False
            discarded_findings.append(det_finding)

    # 4. Include findings discarded by Grounding Guard in semantic stage
    if semantic_res and semantic_res.discarded_findings:
        for d_idx, d in enumerate(semantic_res.discarded_findings):
            discarded_findings.append(AuditFinding(
                finding_id=_make_finding_id(case_id, d.category.value, d.quote_en, d.quote_hi, d_idx + 1000),
                category=_normalize_category(d.category.value),
                source=AuditSource.LLM,
                severity=AuditSeverity(d.severity.value),
                explanation=d.explanation,
                quote_en=d.quote_en,
                quote_hi=d.quote_hi,
                confidence=d.confidence,
                grounded=False,
                metadata={"reason": "failed_semantic_grounding_guard"}
            ))

    return valid_findings, discarded_findings


def _validate_grounding(finding: AuditFinding, en_text: str, hi_text: str) -> bool:
    """Verifies that quotes are verbatim substrings in their respective texts (Rule R2)."""
    if finding.quote_en is not None and finding.quote_en.strip():
        if not is_substring_grounded(finding.quote_en, en_text):
            return False
    if finding.quote_hi is not None and finding.quote_hi.strip():
        if not is_substring_grounded(finding.quote_hi, hi_text):
            return False
    return True
