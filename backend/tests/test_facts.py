"""
test_facts.py - Unit test suite for Phase Loop 4 (Fact Extraction and Comparison).

Tests:
  - English and Hindi number words, ordinals, scales, and Devanagari digits.
  - Money normalization (₹, Rs., rupees, lakh, crore).
  - Percentages.
  - Duration extraction across units (days, months, years, hours, minutes).
  - Area and length extraction (acres, hectares, sq m, km, meters).
  - Famous 0.3 vs 3 acres difference detection.
  - Multipliers ("ten times", "दस गुना", "twice", "दोगुना").
  - Date normalization (Gregorian and Saka months).
  - Section references (sections, sub-sections, clauses, and comma-separated lists).
  - Equivalence matching across surface forms ("10", "ten", "दस", "१०").
  - Difference detection with evidence spans and statuses.
  - Syntactic limit detection ("needs semantic stage" flag).
  - Exclusion of clause enumeration prefixes and structural chapter labels.
"""

import pytest
from backend.app.facts.models import FactType, FactSpan, FactDifference, FactComparisonResult
from backend.app.facts.number_words import (
    devanagari_digits_to_arabic,
    parse_number_token,
    HI_NUMBERS,
    EN_UNITS,
    EN_SCALES
)
from backend.app.facts.extractor import (
    extract_facts,
    extract_dates,
    extract_money,
    extract_percentages,
    extract_durations,
    extract_area_length,
    extract_multipliers,
    extract_section_references,
    extract_standalone_numbers,
    IntervalMask
)
from backend.app.facts.comparator import compare_clause_facts


# ==============================================================================
# 1. Number & Digit Parsing Tests
# ==============================================================================

def test_devanagari_digit_conversion():
    assert devanagari_digits_to_arabic("१२३४५") == "12345"
    assert devanagari_digits_to_arabic("०.३") == "0.3"
    assert devanagari_digits_to_arabic("५०,०००") == "50,000"


def test_parse_number_tokens():
    assert parse_number_token("100") == 100.0
    assert parse_number_token("१००") == 100.0
    assert parse_number_token("1,00,000") == 100000.0
    assert parse_number_token("१,००,०००") == 100000.0
    assert parse_number_token("0.3") == 0.3
    assert parse_number_token("०.३") == 0.3


def test_standalone_numbers_equivalence():
    res = compare_clause_facts(
        "The committee shall consist of 10 members.",
        "समिति में १० सदस्य होंगे।"
    )
    assert len(res.differences) == 0
    assert len(res.matched_pairs) == 1
    assert res.matched_pairs[0][0].normalized_value == 10.0


def test_standalone_words_equivalence():
    res = compare_clause_facts(
        "There shall be twenty-five members.",
        "पच्चीस सदस्य होंगे।"
    )
    assert len(res.differences) == 0
    assert len(res.matched_pairs) == 1
    assert res.matched_pairs[0][0].normalized_value == 25.0


def test_ordinals_equivalence():
    res = compare_clause_facts(
        "The first meeting shall be held in Delhi.",
        "पहली बैठक दिल्ली में आयोजित होगी।"
    )
    assert len(res.differences) == 0
    assert len(res.matched_pairs) == 1
    assert res.matched_pairs[0][0].normalized_value == 1.0


def test_number_value_mismatch():
    res = compare_clause_facts(
        "The committee shall consist of 5 members.",
        "समिति में 7 सदस्य होंगे।"
    )
    assert len(res.differences) == 1
    diff = res.differences[0]
    assert diff.status == "VALUE_MISMATCH"
    assert diff.evidence_en == "5"
    assert diff.evidence_hi == "7"


# ==============================================================================
# 2. Money Normalization Tests
# ==============================================================================

def test_money_rupees_normalization():
    res = compare_clause_facts(
        "Liable to a fine of Rs. 50,000.",
        "५०,००० रुपये के जुर्माने का दायी होगा।"
    )
    assert len(res.differences) == 0
    assert len(res.matched_pairs) == 1
    assert res.matched_pairs[0][0].fact_type == FactType.MONEY
    assert res.matched_pairs[0][0].normalized_value == 50000.0
    assert res.matched_pairs[0][0].unit == "INR"


def test_money_lakh_crore_normalization():
    # 5 lakh rupees vs ₹ 5,00,000
    res1 = compare_clause_facts(
        "Liable to pay a penalty of 5 lakh rupees.",
        "५,००,००० रुपये की शास्ति संदाय करने के लिए दायी।"
    )
    assert len(res1.differences) == 0
    assert res1.matched_pairs[0][0].normalized_value == 500000.0

    # 1 crore rupees vs 10 million rupees
    res2 = compare_clause_facts(
        "Not exceeding one crore rupees.",
        "एक करोड़ रुपये से अनधिक।"
    )
    assert len(res2.differences) == 0
    assert res2.matched_pairs[0][0].normalized_value == 10000000.0


def test_money_difference_flagged():
    res = compare_clause_facts(
        "Liable to a fine of Rs. 10,000.",
        "बीस हजार रुपये के जुर्माने का दायी होगा।"
    )
    assert len(res.differences) == 1
    diff = res.differences[0]
    assert diff.status == "VALUE_MISMATCH"
    assert diff.fact_type == FactType.MONEY
    assert diff.en_fact.normalized_value == 10000.0
    assert diff.hi_fact.normalized_value == 20000.0


# ==============================================================================
# 3. Percentage Tests
# ==============================================================================

def test_percentage_equivalence():
    res = compare_clause_facts(
        "Interest at the rate of 12% per annum.",
        "प्रति वर्ष १२ प्रतिशत की दर से ब्याज।"
    )
    assert len(res.differences) == 0
    assert len(res.matched_pairs) == 1
    assert res.matched_pairs[0][0].fact_type == FactType.PERCENT
    assert res.matched_pairs[0][0].normalized_value == 12.0


def test_percentage_difference():
    res = compare_clause_facts(
        "Rate of 10 percent.",
        "पंद्रह प्रतिशत की दर।"
    )
    assert len(res.differences) == 1
    assert res.differences[0].status == "VALUE_MISMATCH"
    assert res.differences[0].fact_type == FactType.PERCENT


# ==============================================================================
# 4. Duration Tests
# ==============================================================================

def test_duration_equivalence():
    res1 = compare_clause_facts(
        "Within a period of 30 days from the date.",
        "तारीख से तीस दिन की अवधि के भीतर।"
    )
    assert len(res1.differences) == 0
    assert res1.matched_pairs[0][0].fact_type == FactType.DURATION
    assert res1.matched_pairs[0][0].normalized_value == 30.0
    assert res1.matched_pairs[0][0].unit == "day"

    res2 = compare_clause_facts(
        "Imprisonment for a term of 2 years.",
        "दो वर्ष की अवधि का कारावास।"
    )
    assert len(res2.differences) == 0
    assert res2.matched_pairs[0][0].normalized_value == 2.0
    assert res2.matched_pairs[0][0].unit == "year"


def test_duration_unit_mismatch():
    res = compare_clause_facts(
        "Within a period of 30 days.",
        "३० मास के भीतर।"
    )
    assert len(res.differences) == 1
    diff = res.differences[0]
    assert diff.status == "UNIT_MISMATCH"
    assert diff.fact_type == FactType.DURATION


# ==============================================================================
# 5. Area / Length Tests (including 0.3 vs 3 acres)
# ==============================================================================

def test_famous_land_case_03_vs_3_acres():
    # 0.3 acres in English vs 3 acres in Hindi MUST BE FLAGGED!
    res = compare_clause_facts(
        "Total land acquired shall not exceed 0.3 acres.",
        "अधिग्रहित कुल क्षेत्र 3 एकड़ से अधिक नहीं होगा।"
    )
    assert len(res.differences) == 1
    diff = res.differences[0]
    assert diff.status == "VALUE_MISMATCH"
    assert diff.fact_type == FactType.AREA_LENGTH
    assert diff.en_fact.normalized_value == 0.3
    assert diff.hi_fact.normalized_value == 3.0
    assert diff.evidence_en == "0.3 acres"
    assert diff.evidence_hi == "3 एकड़"


def test_area_equivalence_with_devanagari_digits():
    res = compare_clause_facts(
        "Measuring 0.3 acres of land.",
        "०.३ एकड़ भूमि।"
    )
    assert len(res.differences) == 0
    assert len(res.matched_pairs) == 1
    assert res.matched_pairs[0][0].normalized_value == 0.3
    assert res.matched_pairs[0][0].unit == "acre"


def test_length_units():
    res = compare_clause_facts(
        "Within a distance of 5 km.",
        "५ किमी की दूरी के भीतर।"
    )
    assert len(res.differences) == 0
    assert res.matched_pairs[0][0].unit == "km"
    assert res.matched_pairs[0][0].normalized_value == 5.0


# ==============================================================================
# 6. Multiplier Tests
# ==============================================================================

def test_multiplier_equivalence():
    res1 = compare_clause_facts(
        "Liable to pay ten times the amount.",
        "रकम के दस गुना संदाय करने के लिए दायी।"
    )
    assert len(res1.differences) == 0
    assert res1.matched_pairs[0][0].fact_type == FactType.MULTIPLIER
    assert res1.matched_pairs[0][0].normalized_value == 10.0

    res2 = compare_clause_facts(
        "Penalty equal to twice the value.",
        "मूल्य के दो गुना के बराबर शास्ति।"
    )
    assert len(res2.differences) == 0
    assert res2.matched_pairs[0][0].normalized_value == 2.0


def test_multiplier_mismatch():
    res = compare_clause_facts(
        "Penalty of 5 times the duty.",
        "शुल्क के दस गुना की शास्ति।"
    )
    assert len(res.differences) == 1
    assert res.differences[0].status == "VALUE_MISMATCH"
    assert res.differences[0].fact_type == FactType.MULTIPLIER


# ==============================================================================
# 7. Date Tests (including Hindi month names)
# ==============================================================================

def test_date_equivalence_english_hindi():
    res = compare_clause_facts(
        "This Act shall come into force on 15 August 1947.",
        "यह अधिनियम १५ अगस्त १९४७ को प्रवृत्त होगा।"
    )
    assert len(res.differences) == 0
    assert len(res.matched_pairs) == 1
    f = res.matched_pairs[0][0]
    assert f.fact_type == FactType.DATE
    assert f.normalized_value == "1947-08-15"


def test_date_mismatch():
    res = compare_clause_facts(
        "Published on 1 January 2020.",
        "१ फरवरी २०२० को प्रकाशित।"
    )
    assert len(res.differences) == 1
    assert res.differences[0].status == "VALUE_MISMATCH"
    assert res.differences[0].fact_type == FactType.DATE


# ==============================================================================
# 8. Section References & Clause Enumeration Tests
# ==============================================================================

def test_section_references_equivalence():
    res = compare_clause_facts(
        "Subject to the provisions of section 12.",
        "धारा 12 के उपबंधों के अधीन रहते हुए।"
    )
    assert len(res.differences) == 0
    assert len(res.matched_pairs) == 1
    assert res.matched_pairs[0][0].fact_type == FactType.SECTION_REF
    assert res.matched_pairs[0][0].normalized_value == {"target_type": "section", "target_id": "12"}


def test_sub_section_and_clause_references():
    res = compare_clause_facts(
        "As referred to in sub-section (2) of section 4.",
        "धारा 4 की उपधारा (2) में निर्दिष्ट अनुसार।"
    )
    assert len(res.differences) == 0
    assert len(res.matched_pairs) == 2


def test_section_list_references():
    res = compare_clause_facts(
        "Any relief under sections 18, 19, 20, 21 and 22 may be sought.",
        "धारा 18, धारा 19, धारा 20, धारा 21 या धारा 22 के अधीन कोई अनुतोष।"
    )
    assert len(res.differences) == 0
    assert len(res.matched_pairs) == 5


def test_clause_enumeration_not_extracted():
    # "(2) The Magistrate shall dispose..." -> "(2)" must NOT be extracted as a factual NUMBER!
    facts = extract_facts("(2) The Magistrate shall dispose of the application.")
    for f in facts:
        assert f.normalized_value != 2.0 or f.fact_type != FactType.NUMBER


def test_chapter_structural_heading_not_extracted():
    facts_en = extract_facts("CHAPTER IV PROCEDURE FOR OBTAINING ORDERS")
    facts_hi = extract_facts("अध्याय 4 अनुतोषों के आदेश अभिप्राप्त करने के लिए प्रक्रिया")
    assert len(facts_en) == 0
    assert len(facts_hi) == 0


# ==============================================================================
# 9. Known Syntactic Limit ("needs semantic stage")
# ==============================================================================

def test_known_syntactic_limit_ten_times_vs_tax_plus():
    # "shall be liable to a penalty of ten times the tax" vs
    # "shall be liable to tax plus a penalty of ten times the tax"
    res = compare_clause_facts(
        "shall be liable to a penalty of ten times the tax",
        "कर के अतिरिक्त कर के दस गुना की शास्ति का दायी होगा"
    )
    assert len(res.differences) == 1
    diff = res.differences[0]
    assert diff.needs_semantic_stage is True
    assert "needs semantic stage" in diff.description
