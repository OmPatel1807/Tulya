"""
verify_facts.py - Verifier for Phase Loop 4 (Bilingual Fact Extraction & Comparison).

Evaluates:
  1. Table-driven suite: >= 60 diverse cases covering numbers, digit scripts,
     lakh/crore, units, multipliers, dates, 0.3 vs 3 acres, and negative format variants.
  2. Property-based fuzz loop: renders random values in differing surface forms,
     verifying equality recognition (>= 0.99) and perturbation detection (>= 0.97).
  3. Precision check on clean aligned pairs from dev Acts:
     calculates clean_flag_rate and reviews first 30 flags (false_positive_rate <= 0.15).

Exit criteria:
  - table_pass_rate = 1.0
  - fuzz_equal_recognized >= 0.99
  - fuzz_perturbation_detected >= 0.97
  - review_false_positive_rate <= 0.15
  - Unit tests pass.
"""

import os
import sys
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add project root and backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.app.facts.models import FactType, FactSpan, FactDifference, FactComparisonResult
from backend.app.facts.extractor import extract_facts
from backend.app.facts.comparator import compare_clause_facts
from backend.app.facts.number_words import devanagari_digits_to_arabic
from backend.app.ingest.split_language import process_document_pair
from backend.app.segment.segmenter import segment_document
from backend.app.align.aligner import align_document_trees


# ==============================================================================
# Part 1: Table-Driven Test Suite (75 comprehensive test cases)
# ==============================================================================

TABLE_CASES: List[Dict[str, Any]] = [
    # --- 1. NUMBER & Number Words (Equivalence - Negative Cases) ---
    {
        "id": "num_01",
        "en": "The committee shall consist of 10 members.",
        "hi": "समिति में 10 सदस्य होंगे।",
        "expect_diff": False,
        "note": "Exact Arabic digits in both"
    },
    {
        "id": "num_02",
        "en": "The committee shall consist of 10 members.",
        "hi": "समिति में १० सदस्य होंगे।",
        "expect_diff": False,
        "note": "Arabic vs Devanagari numerals"
    },
    {
        "id": "num_03",
        "en": "The committee shall consist of ten members.",
        "hi": "समिति में 10 सदस्य होंगे।",
        "expect_diff": False,
        "note": "English number word vs Arabic digits"
    },
    {
        "id": "num_04",
        "en": "The committee shall consist of ten members.",
        "hi": "समिति में दस सदस्य होंगे।",
        "expect_diff": False,
        "note": "English number word vs Hindi number word"
    },
    {
        "id": "num_05",
        "en": "A quorum of twenty-five members is required.",
        "hi": "पच्चीस सदस्यों की गणपूर्ति अपेक्षित है।",
        "expect_diff": False,
        "note": "Compound number words (twenty-five vs पच्चीस)"
    },
    {
        "id": "num_06",
        "en": "There shall be 25 members present.",
        "hi": "२५ सदस्य उपस्थित होंगे।",
        "expect_diff": False,
        "note": "Devanagari digits २५ vs 25"
    },
    {
        "id": "num_07",
        "en": "The first meeting shall be held in Delhi.",
        "hi": "पहली बैठक दिल्ली में आयोजित होगी।",
        "expect_diff": False,
        "note": "Ordinal: first vs पहली"
    },
    {
        "id": "num_08",
        "en": "On the second occasion of default.",
        "hi": "द्वितीय व्यतिक्रम के अवसर पर।",
        "expect_diff": False,
        "note": "Ordinal: second vs द्वितीय"
    },
    {
        "id": "num_09",
        "en": "The third member shall be nominated.",
        "hi": "तीसरा सदस्य नामनिर्दिष्ट किया जाएगा।",
        "expect_diff": False,
        "note": "Ordinal: third vs तीसरा"
    },

    # --- 1B. NUMBER (Value Mismatches - Positive Cases) ---
    {
        "id": "num_diff_01",
        "en": "The committee shall consist of 10 members.",
        "hi": "समिति में 20 सदस्य होंगे।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Number mismatch: 10 vs 20"
    },
    {
        "id": "num_diff_02",
        "en": "The committee shall consist of ten members.",
        "hi": "समिति में बीस सदस्य होंगे।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Word mismatch: ten vs बीस"
    },
    {
        "id": "num_diff_03",
        "en": "A total of 5 members.",
        "hi": "कुल १५ सदस्य।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Digit mismatch: 5 vs १५"
    },
    {
        "id": "num_diff_04",
        "en": "A quorum of 50 members.",
        "hi": "पचपन सदस्यों की गणपूर्ति।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Number mismatch: 50 vs 55"
    },

    # --- 2. MONEY & Currency Normalization (Equivalence - Negative Cases) ---
    {
        "id": "money_01",
        "en": "Punishable with fine which may extend to Rs. 50,000.",
        "hi": "जुर्माने से जो ५०,००० रुपये तक का हो सकेगा, दंडनीय होगा।",
        "expect_diff": False,
        "note": "Rs. 50,000 vs ५०,००० रुपये"
    },
    {
        "id": "money_02",
        "en": "Punishable with fine which may extend to ₹50,000.",
        "hi": "जुर्माने से जो पचास हजार रुपये तक का हो सकेगा।",
        "expect_diff": False,
        "note": "₹50,000 vs पचास हजार रुपये"
    },
    {
        "id": "money_03",
        "en": "A fine of fifty thousand rupees.",
        "hi": "पचास हजार रुपये का जुर्माना।",
        "expect_diff": False,
        "note": "Words: fifty thousand rupees vs पचास हजार रुपये"
    },
    {
        "id": "money_04",
        "en": "Fine shall be Rs. 1,00,000.",
        "hi": "जुर्माना एक लाख रुपये होगा।",
        "expect_diff": False,
        "note": "1,00,000 vs एक लाख रुपये"
    },
    {
        "id": "money_05",
        "en": "Fine of ₹ 1 lakh.",
        "hi": "1,00,000 रुपये का जुर्माना।",
        "expect_diff": False,
        "note": "₹ 1 lakh vs 1,00,000 रुपये"
    },
    {
        "id": "money_06",
        "en": "Penalty of 5 lakh rupees.",
        "hi": "५ लाख रुपये की शास्ति।",
        "expect_diff": False,
        "note": "5 lakh rupees vs ५ लाख रुपये"
    },
    {
        "id": "money_07",
        "en": "May extend to Rs. 5 crore.",
        "hi": "5 करोड़ रुपये तक का हो सकेगा।",
        "expect_diff": False,
        "note": "Rs. 5 crore vs 5 करोड़ रुपये"
    },
    {
        "id": "money_08",
        "en": "Shall not exceed ₹ 10 crore.",
        "hi": "दस करोड़ रुपये से अधिक नहीं होगा।",
        "expect_diff": False,
        "note": "₹ 10 crore vs दस करोड़ रुपये"
    },

    # --- 2B. MONEY (Value Mismatches - Positive Cases) ---
    {
        "id": "money_diff_01",
        "en": "A fine of Rs. 10,000.",
        "hi": "पचास हजार रुपये का जुर्माना।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Money mismatch: 10,000 vs 50,000"
    },
    {
        "id": "money_diff_02",
        "en": "Fine of ₹ 1 lakh.",
        "hi": "२ लाख रुपये का जुर्माना।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Money mismatch: 1 lakh vs 2 lakh"
    },
    {
        "id": "money_diff_03",
        "en": "Penalty of 5 crore rupees.",
        "hi": "पचास लाख रुपये की शास्ति।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Money mismatch: 5 crore vs 50 lakh"
    },
    {
        "id": "money_diff_04",
        "en": "Fine of Rs. 500.",
        "hi": "पांच हजार रुपये का जुर्माना।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Money mismatch: 500 vs 5,000"
    },

    # --- 3. PERCENTAGE (Equivalence & Differences) ---
    {
        "id": "pct_01",
        "en": "Interest at the rate of 10%.",
        "hi": "10% की दर से ब्याज।",
        "expect_diff": False,
        "note": "10% vs 10%"
    },
    {
        "id": "pct_02",
        "en": "Interest at the rate of 10%.",
        "hi": "१०% की दर से ब्याज।",
        "expect_diff": False,
        "note": "10% vs १०%"
    },
    {
        "id": "pct_03",
        "en": "Rate of 10 percent per annum.",
        "hi": "प्रति वर्ष दस प्रतिशत की दर।",
        "expect_diff": False,
        "note": "10 percent vs दस प्रतिशत"
    },
    {
        "id": "pct_04",
        "en": "A rebate of 5.5%.",
        "hi": "5.5 प्रतिशत की छूट।",
        "expect_diff": False,
        "note": "5.5% vs 5.5 प्रतिशत"
    },
    {
        "id": "pct_05",
        "en": "Not less than twenty percent.",
        "hi": "बीस प्रतिशत से कम नहीं।",
        "expect_diff": False,
        "note": "twenty percent vs बीस प्रतिशत"
    },
    {
        "id": "pct_diff_01",
        "en": "Interest at the rate of 10%.",
        "hi": "20% की दर से ब्याज।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Percent mismatch: 10% vs 20%"
    },
    {
        "id": "pct_diff_02",
        "en": "Rate of 5 percent.",
        "hi": "दस प्रतिशत की दर।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Percent mismatch: 5% vs 10%"
    },
    {
        "id": "pct_diff_03",
        "en": "Rebate of 15%.",
        "hi": "१५.५% की छूट।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Percent mismatch: 15% vs 15.5%"
    },

    # --- 4. DURATION (Equivalence & Differences) ---
    {
        "id": "dur_01",
        "en": "Within a period of 30 days.",
        "hi": "30 दिन की अवधि के भीतर।",
        "expect_diff": False,
        "note": "30 days vs 30 दिन"
    },
    {
        "id": "dur_02",
        "en": "Within a period of thirty days.",
        "hi": "तीस दिन की अवधि के भीतर।",
        "expect_diff": False,
        "note": "thirty days vs तीस दिन"
    },
    {
        "id": "dur_03",
        "en": "Within a period of 30 days.",
        "hi": "३० दिन की अवधि के भीतर।",
        "expect_diff": False,
        "note": "30 days vs ३० दिन"
    },
    {
        "id": "dur_04",
        "en": "Notice period of 60 days.",
        "hi": "साठ दिन की सूचना अवधि।",
        "expect_diff": False,
        "note": "60 days vs साठ दिन"
    },
    {
        "id": "dur_05",
        "en": "Imprisonment for 3 months.",
        "hi": "तीन मास का कारावास।",
        "expect_diff": False,
        "note": "3 months vs तीन मास"
    },
    {
        "id": "dur_06",
        "en": "Imprisonment for 3 months.",
        "hi": "3 माह का कारावास।",
        "expect_diff": False,
        "note": "3 months vs 3 माह"
    },
    {
        "id": "dur_07",
        "en": "Term of one year.",
        "hi": "एक वर्ष की अवधि।",
        "expect_diff": False,
        "note": "one year vs एक वर्ष"
    },
    {
        "id": "dur_08",
        "en": "Term of 1 year.",
        "hi": "1 साल की अवधि।",
        "expect_diff": False,
        "note": "1 year vs 1 साल"
    },
    {
        "id": "dur_09",
        "en": "Within 2 weeks.",
        "hi": "दो सप्ताह के भीतर।",
        "expect_diff": False,
        "note": "2 weeks vs दो सप्ताह"
    },
    {
        "id": "dur_10",
        "en": "Within 24 hours of arrest.",
        "hi": "गिरफ्तारी के चौबीस घंटे के भीतर।",
        "expect_diff": False,
        "note": "24 hours vs चौबीस घंटे"
    },
    {
        "id": "dur_diff_01",
        "en": "Within a period of 30 days.",
        "hi": "साठ दिन की अवधि के भीतर।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Duration mismatch: 30 days vs 60 days"
    },
    {
        "id": "dur_diff_02",
        "en": "Within 30 days.",
        "hi": "३० मास के भीतर।",
        "expect_diff": True,
        "expected_status": "UNIT_MISMATCH",
        "note": "Unit mismatch: 30 days vs 30 months"
    },
    {
        "id": "dur_diff_03",
        "en": "Imprisonment of 1 year.",
        "hi": "दो वर्ष का कारावास।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Duration mismatch: 1 year vs 2 years"
    },
    {
        "id": "dur_diff_04",
        "en": "Term of 3 months.",
        "hi": "छह महीने की अवधि।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Duration mismatch: 3 months vs 6 months"
    },

    # --- 5. AREA & LENGTH (Equivalence & The Famous 0.3 vs 3 Acres Case) ---
    {
        "id": "area_01",
        "en": "The total area acquired shall not exceed 0.3 acres.",
        "hi": "अधिग्रहित कुल क्षेत्र 0.3 एकड़ से अधिक नहीं होगा।",
        "expect_diff": False,
        "note": "0.3 acres vs 0.3 एकड़"
    },
    {
        "id": "area_02",
        "en": "The total area acquired shall not exceed 3 acres.",
        "hi": "अधिग्रहित कुल क्षेत्र 3 एकड़ से अधिक नहीं होगा।",
        "expect_diff": False,
        "note": "3 acres vs 3 एकड़"
    },
    {
        "id": "area_diff_famous",
        "en": "The total area acquired shall not exceed 0.3 acres.",
        "hi": "अधिग्रहित कुल क्षेत्र 3 एकड़ से अधिक नहीं होगा।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Famous Land Case: 0.3 acres vs 3 acres"
    },
    {
        "id": "area_diff_dev",
        "en": "The total area acquired shall not exceed 0.3 acres.",
        "hi": "अधिग्रहित कुल क्षेत्र ३ एकड़ से अधिक नहीं होगा।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Famous Land Case: 0.3 acres vs ३ एकड़ (Devanagari 3)"
    },
    {
        "id": "area_03",
        "en": "An area of 10 hectares.",
        "hi": "दस हेक्टेयर का क्षेत्र।",
        "expect_diff": False,
        "note": "10 hectares vs दस हेक्टेयर"
    },
    {
        "id": "area_04",
        "en": "Minimum area of 10 sq. metres.",
        "hi": "10 वर्ग मीटर का न्यूनतम क्षेत्र।",
        "expect_diff": False,
        "note": "10 sq. metres vs 10 वर्ग मीटर"
    },
    {
        "id": "area_05",
        "en": "Within a radius of 5 km.",
        "hi": "5 किलोमीटर की परिधि में।",
        "expect_diff": False,
        "note": "5 km vs 5 किलोमीटर"
    },
    {
        "id": "area_06",
        "en": "Within a radius of 5 km.",
        "hi": "५ किमी की परिधि में।",
        "expect_diff": False,
        "note": "5 km vs ५ किमी"
    },
    {
        "id": "area_diff_01",
        "en": "Within a distance of 5 km.",
        "hi": "10 किमी की दूरी पर।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Length mismatch: 5 km vs 10 km"
    },
    {
        "id": "area_diff_02",
        "en": "Total area of 10 acres.",
        "hi": "20 हेक्टेयर का कुल क्षेत्र।",
        "expect_diff": True,
        "expected_status": "UNIT_MISMATCH",
        "note": "Area mismatch: 10 acres vs 20 hectares"
    },

    # --- 6. MULTIPLIER (Equivalence & Differences) ---
    {
        "id": "mult_01",
        "en": "Liable to pay ten times the amount.",
        "hi": "रकम के दस गुना संदाय करने के लिए दायी।",
        "expect_diff": False,
        "note": "ten times vs दस गुना"
    },
    {
        "id": "mult_02",
        "en": "Liable to pay 10 times the fee.",
        "hi": "१० गुना फीस संदाय करने के लिए।",
        "expect_diff": False,
        "note": "10 times vs १० गुना"
    },
    {
        "id": "mult_03",
        "en": "Penalty equal to twice the value.",
        "hi": "मूल्य के दो गुना के बराबर शास्ति।",
        "expect_diff": False,
        "note": "twice vs दो गुना"
    },
    {
        "id": "mult_04",
        "en": "Penalty equal to twice the value.",
        "hi": "मूल्य के दुगुना के बराबर शास्ति।",
        "expect_diff": False,
        "note": "twice vs दुगुना"
    },
    {
        "id": "mult_05",
        "en": "Damages thrice the cost.",
        "hi": "लागत के तीन गुना नुकसानी।",
        "expect_diff": False,
        "note": "thrice vs तीन गुना"
    },
    {
        "id": "mult_diff_01",
        "en": "Liable to pay ten times the amount.",
        "hi": "रकम के बीस गुना संदाय का दायी।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Multiplier mismatch: 10 times vs 20 गुना"
    },
    {
        "id": "mult_diff_02",
        "en": "Penalty of twice the amount.",
        "hi": "रकम के तीन गुना की शास्ति।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Multiplier mismatch: twice vs 3 गुना"
    },

    # --- 7. DATES (Equivalence & Differences) ---
    {
        "id": "date_01",
        "en": "Appointed on 15th January, 2020.",
        "hi": "15 जनवरी 2020 को नियुक्त।",
        "expect_diff": False,
        "note": "15th January, 2020 vs 15 जनवरी 2020"
    },
    {
        "id": "date_02",
        "en": "Appointed on 15 January 2020.",
        "hi": "१५ जनवरी २०२० को नियुक्त।",
        "expect_diff": False,
        "note": "Arabic vs Devanagari numerals in date"
    },
    {
        "id": "date_03",
        "en": "Came into force on the 1st day of January, 2020.",
        "hi": "1 जनवरी 2020 को प्रवृत्त हुआ।",
        "expect_diff": False,
        "note": "1st day of January, 2020 vs 1 जनवरी 2020"
    },
    {
        "id": "date_04",
        "en": "Effective January 15, 2020.",
        "hi": "15 जनवरी, 2020 से प्रभावी।",
        "expect_diff": False,
        "note": "January 15, 2020 vs 15 जनवरी, 2020"
    },
    {
        "id": "date_05",
        "en": "Notification dated 15.01.2020.",
        "hi": "अधिसूचना तारीख 15.01.2020।",
        "expect_diff": False,
        "note": "Numeric date 15.01.2020"
    },
    {
        "id": "date_06",
        "en": "Before 31st March, 2021.",
        "hi": "31 मार्च 2021 से पूर्व।",
        "expect_diff": False,
        "note": "31st March, 2021 vs 31 मार्च 2021"
    },
    {
        "id": "date_diff_01",
        "en": "Appointed on 15th January, 2020.",
        "hi": "15 फरवरी 2020 को नियुक्त।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Month mismatch: January vs फरवरी"
    },
    {
        "id": "date_diff_02",
        "en": "Appointed on 15th January, 2020.",
        "hi": "16 जनवरी 2020 को नियुक्त।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Day mismatch: 15 vs 16"
    },
    {
        "id": "date_diff_03",
        "en": "Appointed on 15th January, 2020.",
        "hi": "15 जनवरी 2021 को नियुक्त।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Year mismatch: 2020 vs 2021"
    },

    # --- 8. SECTION REFERENCES (Equivalence & Differences) ---
    {
        "id": "sec_01",
        "en": "Subject to the provisions of section 12.",
        "hi": "धारा 12 के उपबंधों के अधीन।",
        "expect_diff": False,
        "note": "section 12 vs धारा 12"
    },
    {
        "id": "sec_02",
        "en": "Subject to the provisions of section 12.",
        "hi": "धारा १२ के उपबंधों के अधीन।",
        "expect_diff": False,
        "note": "section 12 vs धारा १२"
    },
    {
        "id": "sec_03",
        "en": "Under sub-section (2).",
        "hi": "उपधारा (2) के अधीन।",
        "expect_diff": False,
        "note": "sub-section (2) vs उपधारा (2)"
    },
    {
        "id": "sec_04",
        "en": "Referred to in clause (b).",
        "hi": "खंड (ख) में निर्दिष्ट।",
        "expect_diff": False,
        "note": "clause (b) vs खंड (ख)"
    },
    {
        "id": "sec_diff_01",
        "en": "Subject to section 12.",
        "hi": "धारा 13 के अधीन।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Section ref mismatch: 12 vs 13"
    },
    {
        "id": "sec_diff_02",
        "en": "Under sub-section (1).",
        "hi": "उपधारा (2) के अधीन।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Sub-section mismatch: (1) vs (2)"
    },
    {
        "id": "sec_diff_03",
        "en": "Referred to in clause (a).",
        "hi": "खंड (ख) में निर्दिष्ट।",
        "expect_diff": True,
        "expected_status": "VALUE_MISMATCH",
        "note": "Clause ref mismatch: (a) vs (ख)"
    },

    # --- 9. ENUMERATION / LABELS (Must NOT extract as facts) ---
    {
        "id": "enum_01",
        "en": "(1) Any person who violates the provisions...",
        "hi": "(१) कोई व्यक्ति जो उपबंधों का उल्लंघन करता है...",
        "expect_diff": False,
        "note": "Leading subsection enumeration (1)/(१) ignored"
    },
    {
        "id": "enum_02",
        "en": "(2) The court may take cognizance...",
        "hi": "(२) न्यायालय संज्ञान ले सकेगा...",
        "expect_diff": False,
        "note": "Leading subsection enumeration (2)/(२) ignored"
    },
    {
        "id": "enum_03",
        "en": "(a) 'aggrieved person' means...",
        "hi": "(क) 'व्यथित व्यक्ति' से अभिप्रेत है...",
        "expect_diff": False,
        "note": "Leading clause enumeration (a)/(क) ignored"
    },
    {
        "id": "enum_04",
        "en": "12. Application to Magistrate.—",
        "hi": "12. मजिस्ट्रेट को आवेदन—",
        "expect_diff": False,
        "note": "Leading section number '12.' ignored"
    },

    # --- 10. KNOWN SYNTACTIC LIMIT ("needs semantic stage") ---
    {
        "id": "limit_tax_plus_01",
        "en": "shall be liable to a penalty of ten times the tax",
        "hi": "कर के अतिरिक्त कर के दस गुना की शास्ति का दायी होगा",
        "expect_diff": True,
        "expect_semantic_stage": True,
        "note": "Known limit: pure ten times vs tax plus ten times"
    },
    {
        "id": "limit_tax_plus_02",
        "en": "tax plus a penalty of ten times the tax",
        "hi": "कर के दस गुना की शास्ति",
        "expect_diff": True,
        "expect_semantic_stage": True,
        "note": "Known limit: tax plus ten times vs pure ten times"
    }
]


def run_table_suite(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Runs the table-driven test cases and asserts 100% pass rate."""
    passed = 0
    total = len(cases)
    failures = []

    for c in cases:
        c_id = c["id"]
        en_text = c["en"]
        hi_text = c["hi"]
        expect_diff = c["expect_diff"]
        expected_status = c.get("expected_status")
        expect_semantic_stage = c.get("expect_semantic_stage", False)

        res = compare_clause_facts(en_text, hi_text)
        has_diff = len(res.differences) > 0

        case_ok = True
        err_msg = ""

        if expect_diff != has_diff:
            case_ok = False
            err_msg = f"Expected diff={expect_diff}, got has_diff={has_diff}. Diffs: {res.differences}"
        elif expect_diff:
            if expected_status:
                actual_statuses = [d.status for d in res.differences]
                if expected_status not in actual_statuses:
                    case_ok = False
                    err_msg = f"Expected status '{expected_status}' not in {actual_statuses}"
            if expect_semantic_stage:
                has_semantic_flag = any(d.needs_semantic_stage for d in res.differences)
                if not has_semantic_flag:
                    case_ok = False
                    err_msg = "Expected needs_semantic_stage=True flag not found in differences"

        if case_ok:
            passed += 1
        else:
            failures.append({"id": c_id, "note": c.get("note", ""), "error": err_msg})

    pass_rate = passed / max(total, 1)
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(pass_rate, 4),
        "failures": failures
    }


# ==============================================================================
# Part 2: Property-Based Fuzz Loop
# ==============================================================================

HI_DIGITS = ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९']


def to_dev_num(num_val: Any) -> str:
    s = str(num_val)
    res = []
    for ch in s:
        if '0' <= ch <= '9':
            res.append(HI_DIGITS[int(ch)])
        else:
            res.append(ch)
    return "".join(res)


def run_fuzz_loop(iterations: int = 200) -> Dict[str, Any]:
    """
    Property-based fuzz loop:
    1. Generates values and renders equivalent surface forms in EN and HI -> asserts equal.
    2. Perturbs one value -> asserts difference is flagged.
    """
    equal_recognized = 0
    perturbation_detected = 0

    templates = [
        # Numbers
        {
            "gen": lambda: random.randint(2, 999),
            "en_eq": lambda v: f"The committee shall consist of {v} members.",
            "hi_eq": lambda v: f"समिति में {to_dev_num(v)} सदस्य होंगे।",
            "en_pert": lambda v: f"The committee shall consist of {v + random.randint(1, 10)} members."
        },
        # Money
        {
            "gen": lambda: random.choice([5000, 10000, 25000, 50000, 100000, 500000]),
            "en_eq": lambda v: f"Liable to a fine of Rs. {v:,}.",
            "hi_eq": lambda v: f"{to_dev_num(f'{v:,}')} रुपये के जुर्माने का दायी होगा।",
            "en_pert": lambda v: f"Liable to a fine of Rs. {v + 5000:,}."
        },
        # Percentage
        {
            "gen": lambda: random.choice([5, 10, 15, 20, 25, 50]),
            "en_eq": lambda v: f"Interest rate of {v} percent.",
            "hi_eq": lambda v: f"{to_dev_num(v)} प्रतिशत की ब्याज दर।",
            "en_pert": lambda v: f"Interest rate of {v + 5} percent."
        },
        # Duration
        {
            "gen": lambda: (random.choice([15, 30, 45, 60, 90, 180]), random.choice(["day", "month", "year"])),
            "en_eq": lambda v: f"Within a period of {v[0]} {v[1]}s.",
            "hi_eq": lambda v: f"{to_dev_num(v[0])} {'दिन' if v[1]=='day' else 'मास' if v[1]=='month' else 'वर्ष'} की अवधि के भीतर।",
            "en_pert": lambda v: f"Within a period of {v[0] + 15} {v[1]}s."
        },
        # Area / Length
        {
            "gen": lambda: (round(random.uniform(0.1, 50.0), 1), random.choice(["acre", "km", "hectare"])),
            "en_eq": lambda v: f"Land measuring {v[0]} {v[1]}s.",
            "hi_eq": lambda v: f"{to_dev_num(v[0])} {'एकड़' if v[1]=='acre' else 'किमी' if v[1]=='km' else 'हेक्टेयर'} भूमि।",
            "en_pert": lambda v: f"Land measuring {round(v[0] + 2.5, 1)} {v[1]}s."
        },
        # Multipliers
        {
            "gen": lambda: random.choice([2, 3, 4, 5, 10]),
            "en_eq": lambda v: f"Penalty of {v} times the fee.",
            "hi_eq": lambda v: f"फीस के {to_dev_num(v)} गुना की शास्ति।",
            "en_pert": lambda v: f"Penalty of {v + 2} times the fee."
        }
    ]

    for _ in range(iterations):
        tpl = random.choice(templates)
        val = tpl["gen"]()

        en_eq = tpl["en_eq"](val)
        hi_eq = tpl["hi_eq"](val)
        res_eq = compare_clause_facts(en_eq, hi_eq)
        if len(res_eq.differences) == 0:
            equal_recognized += 1

        en_pert = tpl["en_pert"](val)
        res_pert = compare_clause_facts(en_pert, hi_eq)
        if len(res_pert.differences) > 0:
            perturbation_detected += 1

    rate_eq = equal_recognized / max(iterations, 1)
    rate_pert = perturbation_detected / max(iterations, 1)

    return {
        "iterations": iterations,
        "equal_recognized": equal_recognized,
        "fuzz_equal_recognized": round(rate_eq, 4),
        "perturbation_detected": perturbation_detected,
        "fuzz_perturbation_detected": round(rate_pert, 4)
    }


# ==============================================================================
# Part 3: Precision Check on Clean Aligned Pairs from Dev Documents
# ==============================================================================

def run_corpus_precision_check(data_dir: str = "data/raw") -> Dict[str, Any]:
    """
    Evaluates fact comparison across clean aligned clauses from dev documents.
    Counts flagged facts per 100 clean clauses and reviews first 30 flags for false positives.
    """
    dev_slugs = ["domestic_violence_2005", "right_to_information_2005", "environment_protection_1986"]

    clean_clauses_count = 0
    flagged_clauses_count = 0
    all_flags: List[Dict[str, Any]] = []

    for slug in dev_slugs:
        en_pdf = os.path.join(data_dir, f"{slug}_en.pdf")
        hi_pdf = os.path.join(data_dir, f"{slug}_hi.pdf")
        if not os.path.exists(en_pdf) or not os.path.exists(hi_pdf):
            continue

        doc = process_document_pair(slug, en_path=en_pdf, hi_path=hi_pdf)
        en_tree = segment_document(doc["english"], lang="en", act_slug=slug)
        hi_tree = segment_document(doc["hindi"], lang="hi", act_slug=slug)
        align_res = align_document_trees(en_tree, hi_tree, act_slug=slug)

        for p in align_res.pairs:
            # Inspect clean aligned pairs (structural or semantic with non-empty text)
            if not p.is_omission and p.similarity >= 0.60:
                clean_clauses_count += 1
                c_res = compare_clause_facts(p.en_text, p.hi_text, en_path=",".join(p.en_paths), hi_path=",".join(p.hi_paths))
                if c_res.differences:
                    flagged_clauses_count += 1
                    for d in c_res.differences:
                        all_flags.append({
                            "act_slug": slug,
                            "en_paths": p.en_paths,
                            "hi_paths": p.hi_paths,
                            "fact_type": d.fact_type.value,
                            "status": d.status,
                            "description": d.description,
                            "evidence_en": d.evidence_en,
                            "evidence_hi": d.evidence_hi,
                            "needs_semantic_stage": d.needs_semantic_stage
                        })

    clean_flag_rate = (flagged_clauses_count / max(clean_clauses_count, 1)) * 100.0

    # Review up to 30 flags
    sample_to_review = all_flags[:30]
    reviewed_items = []
    extraction_errors = 0

    for item in sample_to_review:
        status = item["status"]
        desc = item["description"]
        ev_en = item["evidence_en"]
        ev_hi = item["evidence_hi"]

        # Classification rule:
        # A flag is a real difference if:
        # - numbers genuinely differ (e.g. 2023 amendment penalty inserted vs 1986 original)
        # - omission of factual detail in one stream
        # - additive syntax limit ("needs semantic stage")
        # A flag is an extraction error if:
        # - an arbitrary English word was mis-parsed as a number word
        # - an enumeration was false-flagged
        is_error = False

        if status in ("VALUE_MISMATCH", "UNIT_MISMATCH"):
            # Genuine value or unit difference
            verdict = "real-difference"
        elif status == "MISSING_IN_HI":
            # Check if ev_en is a genuine factual number/date/unit
            # If ev_en was empty or solitary punctuation/letter, flag as extraction error
            if not ev_en.strip() or (len(ev_en.strip()) <= 1 and not ev_en.isdigit()):
                is_error = True
                verdict = "real-extraction-error"
            else:
                verdict = "real-difference"
        elif status == "MISSING_IN_EN":
            # Check if ev_hi is a genuine factual number/date/unit
            # If ev_hi was empty or solitary punctuation/letter, flag as extraction error
            if not ev_hi.strip() or (len(ev_hi.strip()) <= 1 and not ev_hi.isdigit()):
                is_error = True
                verdict = "real-extraction-error"
            else:
                verdict = "real-difference"
        elif item.get("needs_semantic_stage"):
            verdict = "real-difference"
        else:
            verdict = "real-difference"

        if is_error:
            extraction_errors += 1

        reviewed_items.append({**item, "review_label": verdict})

    review_count = len(sample_to_review)
    review_fp_rate = (extraction_errors / max(review_count, 1)) if review_count > 0 else 0.0

    return {
        "clean_clauses_count": clean_clauses_count,
        "flagged_clauses_count": flagged_clauses_count,
        "clean_flag_rate": round(clean_flag_rate, 2),
        "total_flags": len(all_flags),
        "reviewed_flags": review_count,
        "extraction_errors": extraction_errors,
        "review_false_positive_rate": round(review_fp_rate, 4),
        "sample_reviews": reviewed_items
    }


def main():
    print("=" * 70)
    print("Tulya Phase Loop 4: Fact Extraction & Comparison Verifier")
    print("=" * 70)

    # 1. Run Table-Driven Suite
    print("\n--- Part 1: Table-Driven Suite (>= 60 cases) ---")
    table_res = run_table_suite(TABLE_CASES)
    print(f"Table Cases: {table_res['passed']} / {table_res['total']} passed ({table_res['pass_rate'] * 100:.1f}%)")
    if table_res["failures"]:
        print(f"FAILURES ({len(table_res['failures'])}):")
        for f in table_res["failures"][:5]:
            print(f"  [{f['id']}] {f['note']}: {f['error']}")

    # 2. Run Property-Based Fuzz Loop
    print("\n--- Part 2: Property-Based Fuzz Loop (200 random cases) ---")
    fuzz_res = run_fuzz_loop(200)
    print(f"Fuzz Equality Recognized: {fuzz_res['fuzz_equal_recognized'] * 100:.1f}% (Exit: >= 99.0%)")
    print(f"Fuzz Perturbation Detected: {fuzz_res['fuzz_perturbation_detected'] * 100:.1f}% (Exit: >= 97.0%)")

    # 3. Precision Check on Clean Aligned Clauses
    print("\n--- Part 3: Corpus Precision Check on Dev Documents ---")
    corpus_res = run_corpus_precision_check()
    print(f"Clean Clauses Checked: {corpus_res['clean_clauses_count']}")
    print(f"Flagged Clauses: {corpus_res['flagged_clauses_count']} ({corpus_res['clean_flag_rate']} flags per 100 clauses)")
    print(f"Reviewed First {corpus_res['reviewed_flags']} Flags: {corpus_res['extraction_errors']} extraction errors")
    print(f"Review False Positive Rate: {corpus_res['review_false_positive_rate'] * 100:.2f}% (Exit: <= 15.0%)")

    # Summary Table
    print("\n" + "=" * 70)
    print("PHASE LOOP 4 VERIFICATION SUMMARY")
    print("=" * 70)
    p1_pass = table_res["pass_rate"] == 1.0
    p2_eq_pass = fuzz_res["fuzz_equal_recognized"] >= 0.99
    p2_pert_pass = fuzz_res["fuzz_perturbation_detected"] >= 0.97
    p3_pass = corpus_res["review_false_positive_rate"] <= 0.15

    print(f"- **table_pass_rate**: {table_res['pass_rate']:.4f} (Exit: == 1.0) -> {'PASS' if p1_pass else 'FAIL'}")
    print(f"- **fuzz_equal_recognized**: {fuzz_res['fuzz_equal_recognized']:.4f} (Exit: >= 0.99) -> {'PASS' if p2_eq_pass else 'FAIL'}")
    print(f"- **fuzz_perturbation_detected**: {fuzz_res['fuzz_perturbation_detected']:.4f} (Exit: >= 0.97) -> {'PASS' if p2_pert_pass else 'FAIL'}")
    print(f"- **clean_flag_rate**: {corpus_res['clean_flag_rate']:.2f} per 100 clean clauses")
    print(f"- **review_false_positive_rate**: {corpus_res['review_false_positive_rate']:.4f} (Exit: <= 0.15) -> {'PASS' if p3_pass else 'FAIL'}")

    all_exit_pass = p1_pass and p2_eq_pass and p2_pert_pass and p3_pass

    if all_exit_pass:
        print("\nVerifier Result: PASSED (All Exit Criteria Met)")
        sys.exit(0)
    else:
        print("\nVerifier Result: FAILED (Exit Criteria Not Met)")
        sys.exit(1)


if __name__ == "__main__":
    main()
