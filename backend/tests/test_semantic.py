"""
test_semantic.py - Unit tests for Phase Loop 5 (Semantic Stage).
Tests:
1. Grounding Guard (Rule R2): exact substring verification in English and Hindi, rejection of hallucinations.
2. JSON Validation and Retry: single retry on malformed JSON output, fallback handling.
3. Modality Lexicon Hints: deontic marker extraction and modal shift detection.
4. Semantic Response Cache: persistent SQLite caching and deterministic cache key construction.
5. Misplaced Content Lookup: distinguishing cross-section reordering from genuine omission.
6. End-to-End Semantic Comparator Client: integration with mock provider and grounding filter.
"""

import json
import pytest
from pathlib import Path

from backend.app.semantic.models import (
    SemanticCategory,
    SemanticSeverity,
    SemanticFinding,
    SemanticComparisonResult
)
from backend.app.semantic.grounding import (
    normalize_quote_text,
    is_substring_grounded,
    validate_grounding,
    filter_findings_by_grounding
)
from backend.app.semantic.modality import (
    detect_modality_hints,
    EN_MANDATORY_REGEX,
    EN_PERMISSIVE_REGEX,
    HI_MANDATORY_REGEX,
    HI_PERMISSIVE_REGEX
)
from backend.app.semantic.cache import SemanticCache
from backend.app.semantic.reorder_lookup import find_misplaced_content
from backend.app.semantic.client import (
    BaseLLMProvider,
    MockSemanticProvider,
    SemanticComparatorClient
)


# =====================================================================
# 1. Grounding Guard Tests (Rule R2)
# =====================================================================

class TestGroundingGuard:
    """Tests for Rule R2: exact verbatim substring grounding."""

    def test_normalize_quote_text(self):
        text = "Section 28(1)   shall   be “enforced” in ‘full’."
        norm = normalize_quote_text(text)
        assert norm == "Section 28(1) shall be \"enforced\" in 'full'."

    def test_is_substring_grounded_exact_and_normalized(self):
        source = "The court shall record reasons in writing before passing an order."
        assert is_substring_grounded("shall record reasons", source) is True
        assert is_substring_grounded("shall   record  reasons", source) is True
        assert is_substring_grounded("shall not record reasons", source) is False
        assert is_substring_grounded("hallucinated phrase", source) is False

    def test_validate_grounding_both_present(self):
        en_source = "The Magistrate shall direct the respondent to pay monetary relief."
        hi_source = "मजिस्ट्रेट प्रत्यर्थी को धनीय अनुतोष संदत्त करने का निर्देश देगा ।"

        finding = SemanticFinding(
            category=SemanticCategory.MODALITY,
            severity=SemanticSeverity.HIGH,
            explanation="Mandatory instruction changed.",
            quote_en="shall direct",
            quote_hi="निर्देश देगा",
            confidence=0.95
        )
        is_valid, _ = validate_grounding(finding, en_source, hi_source)
        assert is_valid is True

    def test_validate_grounding_rejects_hallucinated_en_quote(self):
        en_source = "The Magistrate shall direct the respondent to pay monetary relief."
        hi_source = "मजिस्ट्रेट प्रत्यर्थी को धनीय अनुतोष संदत्त करने का निर्देश देगा ।"

        finding = SemanticFinding(
            category=SemanticCategory.MODALITY,
            severity=SemanticSeverity.HIGH,
            explanation="Hallucinated English quote.",
            quote_en="the authority must compel",  # Not in en_source
            quote_hi="निर्देश देगा",
            confidence=0.90
        )
        is_valid, reason = validate_grounding(finding, en_source, hi_source)
        assert is_valid is False
        assert "English quote" in reason

    def test_validate_grounding_rejects_hallucinated_hi_quote(self):
        en_source = "The Magistrate shall direct the respondent to pay monetary relief."
        hi_source = "मजिस्ट्रेट प्रत्यर्थी को धनीय अनुतोष संदत्त करने का निर्देश देगा ।"

        finding = SemanticFinding(
            category=SemanticCategory.MODALITY,
            severity=SemanticSeverity.HIGH,
            explanation="Hallucinated Hindi quote.",
            quote_en="shall direct",
            quote_hi="आदेश जारी कर सकेगा",  # Not in hi_source
            confidence=0.90
        )
        is_valid, reason = validate_grounding(finding, en_source, hi_source)
        assert is_valid is False
        assert "Hindi quote" in reason

    def test_validate_grounding_omission_valid(self):
        en_source = "Provided that reasons shall be recorded in writing."
        hi_source = "परन्तु यह कि आदेश पारित किया जाएगा ।"

        finding = SemanticFinding(
            category=SemanticCategory.OMISSION,
            severity=SemanticSeverity.HIGH,
            explanation="Writing requirement missing.",
            quote_en="reasons shall be recorded in writing",
            quote_hi=None,
            confidence=0.94
        )
        is_valid, _ = validate_grounding(finding, en_source, hi_source)
        assert is_valid is True

    def test_validate_grounding_addition_valid(self):
        en_source = "An appeal shall lie to the Court of Session."
        hi_source = "अपील सेशन न्यायालय में अतिरिक्त शास्ति शुल्क संदाय करने पर ही होगी ।"

        finding = SemanticFinding(
            category=SemanticCategory.ADDITION,
            severity=SemanticSeverity.HIGH,
            explanation="Extra penalty fee introduced.",
            quote_en=None,
            quote_hi="अतिरिक्त शास्ति शुल्क संदाय करने पर ही",
            confidence=0.93
        )
        is_valid, _ = validate_grounding(finding, en_source, hi_source)
        assert is_valid is True

    def test_filter_findings_by_grounding(self):
        en_source = "The officer shall give notice within seven days."
        hi_source = "अधिकारी सात दिन के भीतर सूचना देगा ।"

        valid_f = SemanticFinding(
            category=SemanticCategory.MODALITY,
            severity=SemanticSeverity.MEDIUM,
            explanation="Valid finding",
            quote_en="shall give notice",
            quote_hi="सूचना देगा",
            confidence=0.9
        )
        hallucinated_f = SemanticFinding(
            category=SemanticCategory.SCOPE,
            severity=SemanticSeverity.HIGH,
            explanation="Fabricated finding",
            quote_en="all persons in the district",
            quote_hi="समस्त नागरिकों",
            confidence=0.8
        )

        valid_list, discarded_list = filter_findings_by_grounding(
            [valid_f, hallucinated_f], en_source, hi_source
        )
        assert len(valid_list) == 1
        assert len(discarded_list) == 1
        assert valid_list[0].quote_en == "shall give notice"
        assert discarded_list[0].quote_en == "all persons in the district"


# =====================================================================
# 2. Modality Lexicon Tests
# =====================================================================

class TestModalityLexicon:
    """Tests for modality hint detection in English and Hindi legal texts."""

    def test_detect_modal_shift_mandatory_to_permissive(self):
        en = "The Central Government shall appoint an auditor."
        hi = "केन्द्रीय सरकार लेखापरीक्षक नियुक्त कर सकेगी ।"
        hint = detect_modality_hints(en, hi)
        assert hint is not None
        assert hint["candidate"] is True
        assert hint["type"] == "MANDATORY_TO_PERMISSIVE"
        assert "shall" in hint["en_indicator"]
        assert "सकेगा" in hint["hi_indicator"] or "सकेगी" in hint["hi_indicator"]

    def test_detect_modal_shift_permissive_to_mandatory(self):
        en = "The Commission may issue guidelines from time to time."
        hi = "आयोग समय-समय पर मार्गनिर्देश जारी करेगा ।"
        hint = detect_modality_hints(en, hi)
        assert hint is not None
        assert hint["candidate"] is True
        assert hint["type"] == "PERMISSIVE_TO_MANDATORY"
        assert "may" in hint["en_indicator"]
        assert "करेगा" in hint["hi_indicator"]

    def test_concordant_modality_no_shift(self):
        en = "The court shall dismiss the application."
        hi = "न्यायालय आवेदन खारिज करेगा ।"
        hint = detect_modality_hints(en, hi)
        assert hint is None


# =====================================================================
# 3. Persistent Cache Tests
# =====================================================================

class TestSemanticCache:
    """Tests for SQLite caching of LLM semantic responses."""

    def test_cache_put_get_hit(self, tmp_path):
        db_path = tmp_path / "test_semantic_cache.sqlite"
        cache = SemanticCache(db_path=str(db_path))

        key = cache.compute_key(
            provider="gemini",
            model="gemini-3.8-flash",
            prompt_version="v1",
            en_text="Clause 1 text",
            hi_text="खण्ड 1 पाठ"
        )
        assert cache.get(key) is None

        test_payload = {
            "findings": [
                {
                    "category": "MODALITY",
                    "severity": "HIGH",
                    "explanation": "Test modal discrepancy.",
                    "quote_en": "shall",
                    "quote_hi": "सकेगा",
                    "confidence": 0.95
                }
            ]
        }
        cache.put(
            cache_key=key,
            provider="gemini",
            model="gemini-3.8-flash",
            prompt_version="v1",
            response_dict=test_payload,
            tokens_prompt=150,
            tokens_completion=45
        )

        retrieved = cache.get(key)
        assert retrieved is not None
        assert retrieved["tokens_prompt"] == 150
        assert retrieved["tokens_completion"] == 45
        res_dict = retrieved["response"]
        assert len(res_dict["findings"]) == 1
        assert res_dict["findings"][0]["category"] == "MODALITY"

    def test_cache_isolation_by_version(self, tmp_path):
        db_path = tmp_path / "test_semantic_cache.sqlite"
        cache = SemanticCache(db_path=str(db_path))

        k1 = cache.compute_key("gemini", "flash", "v1", "text", "पाठ")
        k2 = cache.compute_key("gemini", "flash", "v2", "text", "पाठ")
        assert k1 != k2


# =====================================================================
# 4. Misplaced Clause Lookup Tests
# =====================================================================

class TestMisplacedClauseLookup:
    """Tests cross-section lookup for reordered content vs true omission."""

    def test_find_misplaced_content_success(self):
        missing_text = "The applicant shall pay such fee as may be prescribed by the rules."
        candidate_clauses = [
            ("12.1", "An application may be presented to the Magistrate."),
            ("12.5", "Every applicant shall pay such fee as may be prescribed by the applicable rules."),
            ("13.1", "Notice shall be served upon the respondent.")
        ]
        res = find_misplaced_content(
            clause_text=missing_text,
            target_clauses=candidate_clauses,
            min_similarity=0.75
        )
        assert res is not None
        matched_path, sim = res
        assert matched_path == "12.5"
        assert sim >= 0.75

    def test_find_misplaced_content_true_omission(self):
        missing_text = "Special provisions relating to environmental compensation and restoration."
        candidate_clauses = [
            ("1.1", "This Act may be called the Consumer Protection Act."),
            ("2.1", "In this Act, unless the context otherwise requires...")
        ]
        res = find_misplaced_content(
            clause_text=missing_text,
            target_clauses=candidate_clauses,
            min_similarity=0.75
        )
        assert res is None


# =====================================================================
# 5. Client JSON Validation, Retry & Grounding Integration Tests
# =====================================================================

class MockRetryProvider(BaseLLMProvider):
    """Mock provider to test single JSON retry behavior."""

    def __init__(self, fail_first_only: bool = True):
        self.call_count = 0
        self.fail_first_only = fail_first_only

    def generate(self, prompt: str, system_prompt: str):
        self.call_count += 1
        if self.call_count == 1:
            # Malformed JSON (unclosed syntax)
            return "{'findings': [INVALID JSON", 50, 10
        elif self.call_count == 2 and self.fail_first_only:
            # Valid JSON on retry
            payload = {
                "findings": [
                    {
                        "category": "OMISSION",
                        "severity": "HIGH",
                        "explanation": "Valid finding returned on retry.",
                        "quote_en": "prior notice in writing",
                        "quote_hi": None,
                        "confidence": 0.95
                    }
                ]
            }
            return json.dumps(payload), 50, 25
        else:
            return "STILL BROKEN", 50, 5


class TestSemanticComparatorClient:
    """Tests for SemanticComparatorClient error recovery, retries, and grounding."""

    def test_json_validation_retry_succeeds(self, tmp_path):
        db_path = tmp_path / "cache.sqlite"
        provider = MockRetryProvider(fail_first_only=True)
        client = SemanticComparatorClient(
            provider_name="mock",
            model_name="mock",
            prompt_version="v1",
            cache_db_path=str(db_path),
            provider=provider
        )

        en_text = "The Magistrate shall give prior notice in writing to both parties."
        hi_text = "मजिस्ट्रेट दोनों पक्षों को सूचना देगा ।"

        res = client.compare_clause_pair(en_text, hi_text)
        assert res.json_retry_performed is True
        assert len(res.findings) == 1
        assert res.findings[0].category == SemanticCategory.OMISSION
        assert res.findings[0].quote_en == "prior notice in writing"

    def test_json_validation_double_failure_graceful(self, tmp_path):
        db_path = tmp_path / "cache.sqlite"
        provider = MockRetryProvider(fail_first_only=False)
        client = SemanticComparatorClient(
            provider_name="mock",
            model_name="mock",
            prompt_version="v1",
            cache_db_path=str(db_path),
            provider=provider
        )

        en_text = "Some text."
        hi_text = "कुछ पाठ ।"

        res = client.compare_clause_pair(en_text, hi_text)
        assert res.json_retry_performed is True
        assert len(res.findings) == 0
        assert len(res.discarded_findings) == 0

    def test_mock_semantic_provider_end_to_end(self, tmp_path):
        db_path = tmp_path / "cache.sqlite"
        client = SemanticComparatorClient(
            provider_name="mock",
            model_name="mock-semantic",
            prompt_version="v1",
            cache_db_path=str(db_path),
            provider=MockSemanticProvider()
        )

        # 1. Clean pair
        clean_en = "The Protection Officer shall assist the Magistrate in the discharge of his functions."
        clean_hi = "संरक्षण अधिकारी मजिस्ट्रेट को उसके कृत्यों के निर्वहन में सहायता करेगा ।"
        res_clean = client.compare_clause_pair(clean_en, clean_hi)
        assert len(res_clean.findings) == 0

        # 2. Modality discrepancy
        mod_en = "The court shall Endeavour to dispose of the matter within 60 days."
        mod_hi = "न्यायालय 60 दिन के भीतर मामले का निपटारा करने का प्रयास कर सकेगा ।"
        res_mod = client.compare_clause_pair(mod_en, mod_hi)
        assert len(res_mod.findings) == 1
        assert res_mod.findings[0].category == SemanticCategory.MODALITY
        assert res_mod.findings[0].quote_en == "shall Endeavour"
        assert res_mod.findings[0].quote_hi == "प्रयास कर सकेगा"

        # 3. Cache verification: second call must be a cache hit
        res_mod_cached = client.compare_clause_pair(mod_en, mod_hi)
        assert len(res_mod_cached.findings) == 1
        assert res_mod_cached.findings[0].quote_en == "shall Endeavour"
