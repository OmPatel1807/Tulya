"""
build_regression_cases.py - Generates Synthetic Reproductions of Real-World Reported Patterns.

Constructs:
  data/eval/dev/real_inspired_synthetic/cases.jsonl:
    (a) 'ten times the tax' vs 'penalty ten times in addition to tax' (additive penalty discrepancy)
    (b) qualification present in English and absent in Hindi (dropped statutory qualification/safeguard)
    (c) an area figure differing by an order of magnitude (0.3 acres vs 3 acres / 10 hectares vs 100 hectares)

Guardrail R5:
  All cases are explicitly labeled is_synthetic=True and documented as synthetic reproductions of reported patterns.
"""

import os
import json
from typing import List, Dict, Any


def get_regression_cases() -> List[Dict[str, Any]]:
    return [
        # Pattern (a): Additive tax penalty ("ten times" vs "in addition to ten times")
        {
            "case_id": "reg_synth_01_ten_times_tax",
            "pattern_type": "pattern_a_ten_times_tax",
            "is_synthetic": True,
            "reproduction_note": "Synthetic reproduction of reported statutory divergence: 'ten times the tax' vs 'penalty ten times in addition to tax'",
            "en_paths": ["penalty_clause_1"],
            "hi_paths": ["penalty_clause_1"],
            "en_text": "Any person who defaults in payment of tax shall be liable to pay a penalty of ten times the tax.",
            "hi_text": "कोई व्यक्ति जो कर के संदाय में व्यतिक्रम करता है, कर के अतिरिक्त दस गुना शास्ति के दायित्व के अधीन होगा।",
            "expected_diff": True,
            "ground_truth": {
                "category": "ADDITION",
                "severity": "HIGH",
                "explanation": "Hindi version specifies 'कर के अतिरिक्त' (in addition to tax) altering the legal penalty liability from ten times payable to tax plus ten times penalty.",
                "quote_en": "ten times the tax",
                "quote_hi": "कर के अतिरिक्त"
            }
        },
        {
            "case_id": "reg_synth_01b_tax_plus_penalty",
            "pattern_type": "pattern_a_ten_times_tax",
            "is_synthetic": True,
            "reproduction_note": "Synthetic reproduction of reported statutory divergence: tax plus penalty vs penalty alone",
            "en_paths": ["penalty_clause_2"],
            "hi_paths": ["penalty_clause_2"],
            "en_text": "Every defaulter shall be liable to pay the assessed tax plus a penalty of ten times the tax.",
            "hi_text": "प्रत्येक व्यतिक्रमी कर की रकम का दस गुना शास्ति के रूप में संदाय करने का दायी होगा।",
            "expected_diff": True,
            "ground_truth": {
                "category": "OMISSION",
                "severity": "HIGH",
                "explanation": "English requires payment of assessed tax plus penalty of ten times, whereas Hindi only requires payment of ten times penalty.",
                "quote_en": "tax plus a penalty",
                "quote_hi": "दस गुना शास्ति"
            }
        },

        # Pattern (b): Qualification present in English and absent in Hindi
        {
            "case_id": "reg_synth_02_missing_qualification_notice",
            "pattern_type": "pattern_b_missing_qualification",
            "is_synthetic": True,
            "reproduction_note": "Synthetic reproduction of reported statutory divergence: qualification present in English and absent in Hindi",
            "en_paths": ["qualification_clause_1"],
            "hi_paths": ["qualification_clause_1"],
            "en_text": "The competent authority may cancel the license, provided that no order shall be passed without giving prior notice in writing of not less than thirty days.",
            "hi_text": "सक्षम प्राधिकारी अनुज्ञप्ति को रद्द कर सकेगा, परंतु कोई आदेश सुनवाई का अवसर दिए बिना नहीं किया जाएगा।",
            "expected_diff": True,
            "ground_truth": {
                "category": "OMISSION",
                "severity": "HIGH",
                "explanation": "English requires prior notice in writing of not less than thirty days, which is completely absent in Hindi.",
                "quote_en": "prior notice in writing",
                "quote_hi": None
            }
        },
        {
            "case_id": "reg_synth_02b_missing_qualification_approval",
            "pattern_type": "pattern_b_missing_qualification",
            "is_synthetic": True,
            "reproduction_note": "Synthetic reproduction of reported statutory divergence: statutory approval qualification absent in Hindi",
            "en_paths": ["qualification_clause_2"],
            "hi_paths": ["qualification_clause_2"],
            "en_text": "The Board may, with the prior approval of the Central Government, frame regulations for the recruitment of officers.",
            "hi_text": "बोर्ड अधिकारियों की भर्ती के लिए विनियम बना सकेगा।",
            "expected_diff": True,
            "ground_truth": {
                "category": "OMISSION",
                "severity": "HIGH",
                "explanation": "English requires mandatory prior approval of the Central Government, which is omitted in Hindi.",
                "quote_en": "prior approval of the Central Government",
                "quote_hi": None
            }
        },

        # Pattern (c): Area figure differing by an order of magnitude
        {
            "case_id": "reg_synth_03_area_03_vs_3_acres",
            "pattern_type": "pattern_c_area_order_of_magnitude",
            "is_synthetic": True,
            "reproduction_note": "Synthetic reproduction of reported statutory divergence: area figure differing by an order of magnitude (0.3 acres vs 3 acres)",
            "en_paths": ["land_acquisition_1"],
            "hi_paths": ["land_acquisition_1"],
            "en_text": "The total area of land acquired for residential development shall not exceed 0.3 acres in any urban local area.",
            "hi_text": "आवासीय विकास के लिए अर्जित भूमि का कुल क्षेत्रफल किसी नगरीय स्थानीय क्षेत्र में 3 एकड़ से अधिक नहीं होगा।",
            "expected_diff": True,
            "ground_truth": {
                "category": "NUMERIC",
                "severity": "HIGH",
                "explanation": "Area differs by tenfold: English specifies 0.3 acres while Hindi specifies 3 एकड़ (3.0 acres).",
                "quote_en": "0.3 acres",
                "quote_hi": "3 एकड़"
            }
        },
        {
            "case_id": "reg_synth_03b_area_10_vs_100_hectares",
            "pattern_type": "pattern_c_area_order_of_magnitude",
            "is_synthetic": True,
            "reproduction_note": "Synthetic reproduction of reported statutory divergence: area figure differing by an order of magnitude (10 vs 100 hectares)",
            "en_paths": ["land_acquisition_2"],
            "hi_paths": ["land_acquisition_2"],
            "en_text": "Exemption from environmental audit shall apply only to industrial zones measuring less than 10 hectares.",
            "hi_text": "पर्यावरणीय संपरीक्षा से छूट केवल 100 हेक्टेयर से कम माप वाले औद्योगिक क्षेत्रों पर ही लागू होगी।",
            "expected_diff": True,
            "ground_truth": {
                "category": "NUMERIC",
                "severity": "HIGH",
                "explanation": "Area threshold differs by tenfold: English specifies 10 hectares while Hindi specifies 100 हेक्टेयर (100 hectares).",
                "quote_en": "10 hectares",
                "quote_hi": "100 हेक्टेयर"
            }
        }
    ]


def build_regression_dataset(output_path: str = "data/eval/dev/real_inspired_synthetic/cases.jsonl") -> int:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cases = get_regression_cases()
    with open(output_path, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Saved {len(cases)} regression reproduction cases to {output_path}")
    return len(cases)


if __name__ == "__main__":
    n = build_regression_dataset()
    print(f"Regression dataset generation complete: {n} cases verified.")
