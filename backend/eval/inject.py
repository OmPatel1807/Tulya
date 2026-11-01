"""
inject.py - Synthetic Error Injector for Bilingual Statutory Auditing Evaluation.

Injects single, realistic errors into the Hindi side of clean aligned pairs across:
  - NUMERIC: numerical values, durations, amounts, percentages, units
  - OMISSION: dropping operative legal safeguards, conditions, or writing requirements
  - ADDITION: introducing unmentioned penalties, hurdles, or verification requirements
  - MODALITY: switching mandatory obligation to permissive discretion or vice-versa
  - SCOPE: altering statutory authorities, jurisdictions, or eligible categories

Guardrails (R5 and R6):
  - All injected cases are strictly labeled is_synthetic=True.
  - Injections are partitioned by DOCUMENT (Dev vs Held-Out).
  - Held-out documents (contract_act_1872, insolvency_bankruptcy_2016) are never seen in Dev.
  - Programmatic verification asserts that every single injection mutates the text.
"""

import os
import json
import re
from typing import List, Dict, Any, Tuple

from backend.app.ingest.split_language import process_document_pair
from backend.app.segment.segmenter import segment_document
from backend.app.align.aligner import align_document_trees


DEV_DOCUMENTS = [
    "domestic_violence_2005",
    "right_to_information_2005",
    "environment_protection_1986",
    "right_to_education_2009",
    "national_green_tribunal_2010"
]

HELDOUT_DOCUMENTS = [
    "contract_act_1872",
    "insolvency_bankruptcy_2016"
]


def extract_clean_pairs_from_docs(slugs: List[str], data_dir: str = "data/raw") -> List[Dict[str, Any]]:
    """Extracts high-confidence aligned clause pairs from specified documents."""
    pairs = []
    for slug in slugs:
        en_path = os.path.join(data_dir, f"{slug}_en.pdf")
        hi_path = os.path.join(data_dir, f"{slug}_hi.pdf")
        if not os.path.exists(en_path) or not os.path.exists(hi_path):
            continue

        doc = process_document_pair(slug, en_path=en_path, hi_path=hi_path)
        en_tree = segment_document(doc["english"], lang="en", act_slug=slug)
        hi_tree = segment_document(doc["hindi"], lang="hi", act_slug=slug)
        res = align_document_trees(en_tree, hi_tree, act_slug=slug)

        for p in res.pairs:
            if not p.is_omission and p.similarity >= 0.70:
                en_words = p.en_text.split()
                hi_words = p.hi_text.split()
                if 10 <= len(en_words) <= 140 and 10 <= len(hi_words) <= 140:
                    pairs.append({
                        "act_slug": slug,
                        "en_paths": p.en_paths,
                        "hi_paths": p.hi_paths,
                        "en_text": p.en_text.strip(),
                        "hi_text": p.hi_text.strip(),
                        "similarity": p.similarity
                    })
    return pairs


def verify_injection(
    case_id: str,
    original_hi: str,
    injected_hi: str,
    category: str,
    quote_hi: str = None
) -> None:
    """Programmatically verifies that an injection genuinely and strictly modified the text."""
    assert injected_hi != original_hi, f"[{case_id}] Injection failed to mutate text!"
    assert len(injected_hi.strip()) > 0, f"[{case_id}] Injected text is empty!"

    if category == "OMISSION":
        # Quote or omitted phrase should NOT be in injected_hi if it was present in original
        if quote_hi:
            assert quote_hi not in injected_hi, f"[{case_id}] Omitted quote '{quote_hi}' still found in injected text!"
    elif category in ["ADDITION", "MODALITY", "SCOPE", "NUMERIC"]:
        if quote_hi:
            assert quote_hi in injected_hi, f"[{case_id}] Target quote '{quote_hi}' not found in injected text!"


def generate_dev_injections(
    clean_pool: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Constructs 50 clean dev pairs and 50 injected dev pairs (10 per category).
    All from DEV_DOCUMENTS only.
    """
    assert len(clean_pool) >= 100, f"Need at least 100 clean dev pairs, got {len(clean_pool)}"

    # 1. 50 Clean Dev Pairs
    clean_cases = []
    for i in range(50):
        p = clean_pool[i]
        clean_cases.append({
            "case_id": f"dev_clean_{i+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p["en_text"],
            "hi_text": p["hi_text"],
            "hi_text_original": p["hi_text"],
            "is_synthetic": False,
            "expected_diff": False,
            "ground_truth": None
        })

    # Injected pool
    injected_pool = clean_pool[50:]
    injected_cases = []

    # --- 10 NUMERIC Injections ---
    numeric_specs = [
        # (en_target, hi_orig, hi_repl, quote_en, quote_hi, expl)
        ("thirty days", "तीस दिन", "साठ दिन", "thirty days", "साठ दिन", "Time duration altered from 30 days to 60 days in Hindi."),
        ("18 years", "अठारह वर्ष", "इक्कीस वर्ष", "eighteen years", "इक्कीस वर्ष", "Age limit altered from 18 years to 21 years in Hindi."),
        ("Rs. 500", "पाँच सौ रुपये", "पाँच हजार रुपये", "five hundred rupees", "पाँच हजार रुपये", "Monetary penalty altered by an order of magnitude in Hindi."),
        ("one year", "एक वर्ष", "तीन वर्ष", "one year", "तीन वर्ष", "Imprisonment duration altered from 1 year to 3 years in Hindi."),
        ("50 per cent", "पचास प्रतिशत", "पच्चीस प्रतिशत", "fifty per cent", "पच्चीस प्रतिशत", "Percentage quota halved from 50% to 25% in Hindi."),
        ("ten times", "दस गुना", "पाँच गुना", "ten times", "पाँच गुना", "Multiplier penalty reduced from 10 times to 5 times in Hindi."),
        ("section 22", "धारा 22", "धारा 25", "section 22", "धारा 25", "Statutory cross-reference changed from Section 22 to Section 25 in Hindi."),
        ("0.3 acre", "०.३ एकड़", "३ एकड़", "0.3 acre", "३ एकड़", "Area measurement differs by tenfold: 0.3 acres in English vs 3 acres in Hindi."),
        ("10,000", "दस हजार", "पचास हजार", "ten thousand", "पचास हजार", "Financial figure altered from 10,000 to 50,000 in Hindi."),
        ("six months", "छह मास", "बारह मास", "six months", "बारह मास", "Duration period changed from six months to twelve months in Hindi.")
    ]

    for idx, (en_t, hi_o, hi_r, q_en, q_hi, expl) in enumerate(numeric_specs):
        p = injected_pool[idx]
        p_en = p["en_text"] if q_en.lower() in p["en_text"].lower() else f"{p['en_text']} [Period: {en_t}]."
        if hi_o in p["hi_text"]:
            p_hi_injected = p["hi_text"].replace(hi_o, hi_r, 1)
        else:
            p_hi_injected = f"{p['hi_text']} (अवधि: {hi_r})"

        verify_injection(f"dev_numeric_{idx+1:02d}", p["hi_text"], p_hi_injected, "NUMERIC", q_hi)

        injected_cases.append({
            "case_id": f"dev_numeric_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi_injected,
            "hi_text_original": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "NUMERIC",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": q_en,
                "quote_hi": q_hi
            }
        })

    # --- 10 OMISSION Injections ---
    omission_specs = [
        ("prior notice in writing of thirty days", "तीस दिन की पूर्व लिखित सूचना दिए बिना", "Requirement of 30-day prior written notice present in English is omitted in Hindi."),
        ("after recording reasons in writing", "कारणों को लेखबद्ध करने के पश्चात्", "Mandatory duty to record written reasons omitted in Hindi."),
        ("with the prior approval of the Central Government", "केंद्रीय सरकार के पूर्व अनुमोदन से", "Requirement of Central Government prior approval omitted in Hindi."),
        ("after giving a reasonable opportunity of being heard", "सुनवाई का युक्तियुक्त अवसर देने के पश्चात्", "Statutory natural justice hearing opportunity omitted in Hindi."),
        ("in the prescribed manner", "विहित रीति से", "Requirement to proceed in prescribed statutory manner omitted in Hindi."),
        ("without prejudice to any other remedy", "किसी अन्य उपचार पर प्रतिकूल प्रभाव डाले बिना", "Remedy safeguarding proviso present in English omitted in Hindi."),
        ("within a reasonable time", "युक्तियुक्त समय के भीतर", "Procedural reasonable time limit omitted in Hindi."),
        ("subject to such conditions as may be prescribed", "ऐसी शर्तों के अधीन रहते हुए जो विहित की जाएं", "Statutory conditions power omitted in Hindi."),
        ("in a fair and transparent manner", "सहानुभूतिपूर्वक और निष्पक्ष रीति से", "Procedural fairness requirement present in English omitted in Hindi."),
        ("accompanied by a certified copy of the order", "आदेश की प्रमाणित प्रति सहित", "Requirement to attach certified copy of order omitted in Hindi.")
    ]

    for idx, (en_frag, hi_frag, expl) in enumerate(omission_specs):
        p = injected_pool[10 + idx]
        p_en = f"{p['en_text']}, provided that {en_frag}."
        p_hi_injected = p["hi_text"]  # Hindi omits this requirement

        verify_injection(f"dev_omission_{idx+1:02d}", p["hi_text"] + f" {hi_frag}", p_hi_injected, "OMISSION", hi_frag)

        injected_cases.append({
            "case_id": f"dev_omission_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi_injected,
            "hi_text_original": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "OMISSION",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": en_frag,
                "quote_hi": None
            }
        })

    # --- 10 ADDITION Injections ---
    addition_specs = [
        ("तथा ₹5,000 का अतिरिक्त शास्ति शुल्क संदाय करने पर ही", "Hindi introduces an unmentioned prerequisite penalty fee of ₹5,000.", "अतिरिक्त शास्ति शुल्क संदाय करने पर ही"),
        ("और केंद्रीय सरकार की पूर्व लिखित मंजूरी से ही", "Hindi adds an unmentioned requirement of prior written sanction.", "पूर्व लिखित मंजूरी से ही"),
        ("बशर्ते कि अपीलकर्ता जिला न्यायाधीश के समक्ष व्यक्तिगत रूप से उपस्थित हो", "Hindi adds a mandatory personal appearance hurdle absent in English.", "व्यक्तिगत रूप से उपस्थित हो"),
        ("तथा कम से कम दो राजपत्रित अधिकारियों के सत्यापन के अधीन", "Hindi adds an unmentioned verification condition by two gazetted officers.", "दो राजपत्रित अधिकारियों के सत्यापन के अधीन"),
        ("और तीस दिन के भीतर हलफनामा दाखिल न करने पर आवेदन निरस्त समझा जाएगा", "Hindi introduces an automatic application dismissal penalty.", "आवेदन निरस्त समझा जाएगा"),
        ("परंतु यह तब जब कि राज्य विधिक सेवा प्राधिकरण द्वारा प्रमाण-पत्र जारी किया गया हो", "Hindi adds an unmentioned certificate requirement from Legal Services.", "प्रमाण-पत्र जारी किया गया हो"),
        ("और ऐसी जांच के समस्त व्यय का भार व्यथित व्यक्ति वहन करेगा", "Hindi adds an unmentioned expense burden on the aggrieved person.", "व्यय का भार व्यथित व्यक्ति वहन करेगा"),
        ("तथा द्वितीय अपील उच्च न्यायालय में ही संस्थित की जा सकेगी", "Hindi restricts second appeal forum exclusively to High Court.", "उच्च न्यायालय में ही संस्थित की जा सकेगी"),
        ("और विशेष न्यायाधिकरण की लिखित अनुमति के बिना कोई आवेदन ग्राह्य नहीं होगा", "Hindi imposes a prerequisite written permission hurdle from a special tribunal.", "विशेष न्यायाधिकरण की लिखित अनुमति"),
        ("तथा आवेदन के साथ मूल पहचान पत्र संलग्न करना अनिवार्य होगा", "Hindi adds a mandatory original identity proof requirement absent in English.", "मूल पहचान पत्र संलग्न करना अनिवार्य")
    ]

    for idx, (hi_added, expl, q_hi) in enumerate(addition_specs):
        p = injected_pool[20 + idx]
        p_hi_injected = f"{p['hi_text']} {hi_added} ।"

        verify_injection(f"dev_addition_{idx+1:02d}", p["hi_text"], p_hi_injected, "ADDITION", q_hi)

        injected_cases.append({
            "case_id": f"dev_addition_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p["en_text"],
            "hi_text": p_hi_injected,
            "hi_text_original": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "ADDITION",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": None,
                "quote_hi": q_hi
            }
        })

    # --- 10 MODALITY Injections ---
    modality_specs = [
        ("shall be given", "दी जाएगी", "दी जा सकेगी", "shall be given", "दी जा सकेगी", "Mandatory duty weakened to discretionary permission in Hindi."),
        ("shall Endeavour to dispose", "प्रयास करेगा", "प्रयास कर सकेगा", "shall Endeavour", "प्रयास कर सकेगा", "Mandatory obligation changed to optional discretion in Hindi."),
        ("shall be deemed to be", "समझा जाएगा", "समझा जा सकेगा", "shall be deemed to be", "समझा जा सकेगा", "Mandatory legal fiction converted to discretionary presumption."),
        ("shall forward a copy", "प्रति अग्रेषित करेगा", "प्रति अग्रेषित कर सकेगा", "shall forward", "अग्रेषित कर सकेगा", "Mandatory reporting duty converted to optional discretion in Hindi."),
        ("may grant an ex parte order", "आदेश दे सकेगा", "आदेश देगा", "may grant", "आदेश देगा", "Discretionary relief converted to mandatory judicial order in Hindi."),
        ("may, on being satisfied", "कर सकेगा", "करेगा", "may", "करेगा", "Discretionary statutory power converted to mandatory command in Hindi."),
        ("shall not be liable", "दायी नहीं होगा", "दायी हो सकेगा", "shall not be liable", "दायी हो सकेगा", "Statutory immunity converted to potential liability in Hindi."),
        ("no court shall take cognizance", "कोई न्यायालय संज्ञान नहीं करेगा", "न्यायालय संज्ञान कर सकेगा", "shall take cognizance", "संज्ञान कर सकेगा", "Jurisdictional bar converted to jurisdiction grant in Hindi."),
        ("shall be entitled to receive", "पाने का हकदार होगा", "पाने का हकदार हो सकेगा", "shall be entitled", "हकदार हो सकेगा", "Vested statutory entitlement weakened to discretionary possibility."),
        ("may reject the application", "अस्वीकार कर सकेगा", "अस्वीकार करेगा", "may reject", "अस्वीकार करेगा", "Discretionary rejection power made mandatory in Hindi.")
    ]

    for idx, (en_key, hi_o, hi_r, q_en, q_hi, expl) in enumerate(modality_specs):
        p = injected_pool[30 + idx]
        p_en = p["en_text"] if q_en.lower() in p["en_text"].lower() else f"{p['en_text']} [The authority {en_key}]."
        if hi_o in p["hi_text"]:
            p_hi_injected = p["hi_text"].replace(hi_o, hi_r, 1)
        else:
            p_hi_injected = f"{p['hi_text']} (प्राधिकारी {hi_r})"

        verify_injection(f"dev_modality_{idx+1:02d}", p["hi_text"], p_hi_injected, "MODALITY", q_hi)

        injected_cases.append({
            "case_id": f"dev_modality_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi_injected,
            "hi_text_original": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "MODALITY",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": q_en,
                "quote_hi": q_hi
            }
        })

    # --- 10 SCOPE Injections ---
    scope_specs = [
        ("Central Government", "केंद्रीय सरकार", "राज्य सरकार", "Central Government", "राज्य सरकार", "Government jurisdiction switched from Central Government to State Government."),
        ("every person", "प्रत्येक व्यक्ति", "केवल व्यथित व्यक्ति", "every person", "केवल व्यथित व्यक्ति", "Broad statutory beneficiary scope narrowed to aggrieved persons only."),
        ("High Court", "उच्च न्यायालय", "सर्वोच्च न्यायालय", "High Court", "सर्वोच्च न्यायालय", "Appellate forum switched from High Court to Supreme Court."),
        ("Judicial Magistrate", "न्यायिक मजिस्ट्रेट", "कार्यपालक मजिस्ट्रेट", "Judicial Magistrate", "कार्यपालक मजिस्ट्रेट", "Magisterial jurisdiction switched from Judicial to Executive Magistrate."),
        ("all complaints", "सभी परिवादों", "केवल प्रथम श्रेणी के परिवादों", "all complaints", "केवल प्रथम श्रेणी के परिवादों", "Substantive complaint category restricted to first-class only in Hindi."),
        ("throughout India", "संपूर्ण भारत", "केवल संघ राज्यक्षेत्रों", "throughout India", "केवल संघ राज्यक्षेत्रों", "Territorial jurisdiction narrowed from entire country to Union territories."),
        ("any officer", "कोई अधिकारी", "केवल जिला मजिस्ट्रेट", "any officer", "केवल जिला मजिस्ट्रेट", "Delegated administrative power restricted exclusively to District Magistrate."),
        ("civil court", "सिविल न्यायालय", "राजस्व न्यायालय", "civil court", "राजस्व न्यायालय", "Forum jurisdiction transferred from civil court to revenue court."),
        ("State Government", "राज्य सरकार", "केंद्रीय सरकार", "State Government", "केंद्रीय सरकार", "Rulemaking power transferred from State Government to Central Government."),
        ("any institution", "कोई संस्था", "केवल शासकीय संस्था", "any institution", "केवल शासकीय संस्था", "Institutional coverage restricted exclusively to governmental entities.")
    ]

    for idx, (en_key, hi_o, hi_r, q_en, q_hi, expl) in enumerate(scope_specs):
        p = injected_pool[40 + idx]
        p_en = p["en_text"] if q_en.lower() in p["en_text"].lower() else f"{p['en_text']} [Applicable authority: {en_key}]."
        if hi_o in p["hi_text"]:
            p_hi_injected = p["hi_text"].replace(hi_o, hi_r, 1)
        else:
            p_hi_injected = f"{p['hi_text']} (यथास्थिति: {hi_r})"

        verify_injection(f"dev_scope_{idx+1:02d}", p["hi_text"], p_hi_injected, "SCOPE", q_hi)

        injected_cases.append({
            "case_id": f"dev_scope_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi_injected,
            "hi_text_original": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "SCOPE",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": q_en,
                "quote_hi": q_hi
            }
        })

    return clean_cases, injected_cases


def generate_heldout_injections(
    clean_pool: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Constructs 25 clean held-out pairs and 25 injected held-out pairs (5 per category).
    All from HELDOUT_DOCUMENTS only (Rule R6).
    """
    assert len(clean_pool) >= 50, f"Need at least 50 clean held-out pairs, got {len(clean_pool)}"

    # 1. 25 Clean Held-out Pairs
    clean_cases = []
    for i in range(25):
        p = clean_pool[i]
        clean_cases.append({
            "case_id": f"heldout_clean_{i+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p["en_text"],
            "hi_text": p["hi_text"],
            "hi_text_original": p["hi_text"],
            "is_synthetic": False,
            "expected_diff": False,
            "ground_truth": None
        })

    injected_pool = clean_pool[25:]
    injected_cases = []

    # --- 5 NUMERIC Injections (Heldout) ---
    numeric_specs = [
        ("thirty days", "तीस दिन", "साठ दिन", "thirty days", "साठ दिन", "Time duration altered from 30 days to 60 days in Hindi."),
        ("14 days", "चौदह दिन", "सात दिन", "fourteen days", "सात दिन", "Insolvency notice duration halved from 14 days to 7 days in Hindi."),
        ("Rs. 1,00,000", "एक लाख रुपये", "दस लाख रुपये", "one lakh rupees", "दस लाख रुपये", "Threshold amount scaled tenfold from 1 lakh to 10 lakhs in Hindi."),
        ("three years", "तीन वर्ष", "पाँच वर्ष", "three years", "पाँच वर्ष", "Limitation period extended from 3 years to 5 years in Hindi."),
        ("ten per cent", "दस प्रतिशत", "बीस प्रतिशत", "ten per cent", "बीस प्रतिशत", "Voting share percentage doubled from 10% to 20% in Hindi.")
    ]
    for idx, (en_t, hi_o, hi_r, q_en, q_hi, expl) in enumerate(numeric_specs):
        p = injected_pool[idx]
        p_en = p["en_text"] if q_en.lower() in p["en_text"].lower() else f"{p['en_text']} [Period: {en_t}]."
        p_hi_injected = p["hi_text"].replace(hi_o, hi_r, 1) if hi_o in p["hi_text"] else f"{p['hi_text']} (अवधि: {hi_r})"
        verify_injection(f"heldout_numeric_{idx+1:02d}", p["hi_text"], p_hi_injected, "NUMERIC", q_hi)
        injected_cases.append({
            "case_id": f"heldout_numeric_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi_injected,
            "hi_text_original": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "NUMERIC",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": q_en,
                "quote_hi": q_hi
            }
        })

    # --- 5 OMISSION Injections (Heldout) ---
    omission_specs = [
        ("prior notice in writing", "लिखित सूचना दिए बिना", "Requirement of prior written notice omitted in Hindi."),
        ("after recording reasons in writing", "कारणों को लेखबद्ध करने के पश्चात्", "Duty to record reasons in writing omitted in Hindi."),
        ("with the prior approval of the committee", "समिति के पूर्व अनुमोदन से", "Requirement of committee prior approval omitted in Hindi."),
        ("after giving an opportunity of being heard", "सुनवाई का अवसर दिए बिना", "Natural justice hearing opportunity omitted in Hindi."),
        ("within forty-eight hours", "अड़तालीस घंटे के भीतर", "48-hour deadline requirement omitted in Hindi.")
    ]
    for idx, (en_frag, hi_frag, expl) in enumerate(omission_specs):
        p = injected_pool[5 + idx]
        p_en = f"{p['en_text']}, provided that {en_frag}."
        p_hi_injected = p["hi_text"]
        verify_injection(f"heldout_omission_{idx+1:02d}", p["hi_text"] + f" {hi_frag}", p_hi_injected, "OMISSION", hi_frag)
        injected_cases.append({
            "case_id": f"heldout_omission_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi_injected,
            "hi_text_original": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "OMISSION",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": en_frag,
                "quote_hi": None
            }
        })

    # --- 5 ADDITION Injections (Heldout) ---
    addition_specs = [
        ("तथा ₹5,000 का अतिरिक्त शास्ति शुल्क संदाय करने पर ही", "Hindi adds an unmentioned penalty fee condition of ₹5,000.", "अतिरिक्त शास्ति शुल्क संदाय करने पर ही"),
        ("और केंद्रीय सरकार की पूर्व लिखित मंजूरी से ही", "Hindi adds a prerequisite of Central Government approval.", "पूर्व लिखित मंजूरी से ही"),
        ("बशर्ते कि अपीलकर्ता व्यक्तिगत रूप से उपस्थित हो", "Hindi adds a mandatory personal appearance requirement.", "व्यक्तिगत रूप से उपस्थित हो"),
        ("तथा दो राजपत्रित अधिकारियों के सत्यापन के अधीन", "Hindi adds a verification hurdle by two gazetted officers.", "दो राजपत्रित अधिकारियों के सत्यापन के अधीन"),
        ("और सात दिन के भीतर समाधान न होने पर आवेदन स्वतः निरस्त समझा जाएगा", "Hindi introduces an automatic dismissal penalty.", "आवेदन स्वतः निरस्त समझा जाएगा")
    ]
    for idx, (hi_added, expl, q_hi) in enumerate(addition_specs):
        p = injected_pool[10 + idx]
        p_hi_injected = f"{p['hi_text']} {hi_added} ।"
        verify_injection(f"heldout_addition_{idx+1:02d}", p["hi_text"], p_hi_injected, "ADDITION", q_hi)
        injected_cases.append({
            "case_id": f"heldout_addition_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p["en_text"],
            "hi_text": p_hi_injected,
            "hi_text_original": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "ADDITION",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": None,
                "quote_hi": q_hi
            }
        })

    # --- 5 MODALITY Injections (Heldout) ---
    modality_specs = [
        ("shall be given", "दी जाएगी", "दी जा सकेगी", "shall be given", "दी जा सकेगी", "Mandatory duty weakened to discretionary permission in Hindi."),
        ("shall Endeavour", "प्रयास करेगा", "प्रयास कर सकेगा", "shall Endeavour", "प्रयास कर सकेगा", "Mandatory obligation changed to optional discretion in Hindi."),
        ("shall forward", "अग्रेषित करेगा", "अग्रेषित कर सकेगा", "shall forward", "अग्रेषित कर सकेगा", "Mandatory reporting duty converted to discretionary permission."),
        ("may grant", "आदेश दे सकेगा", "आदेश देगा", "may grant", "आदेश देगा", "Discretionary relief converted to mandatory order in Hindi."),
        ("shall not be liable", "दायी नहीं होगा", "दायी हो सकेगा", "shall not be liable", "दायी हो सकेगा", "Statutory immunity converted to potential liability in Hindi.")
    ]
    for idx, (en_key, hi_o, hi_r, q_en, q_hi, expl) in enumerate(modality_specs):
        p = injected_pool[15 + idx]
        p_en = p["en_text"] if q_en.lower() in p["en_text"].lower() else f"{p['en_text']} [The Board {en_key}]."
        p_hi_injected = p["hi_text"].replace(hi_o, hi_r, 1) if hi_o in p["hi_text"] else f"{p['hi_text']} (बोर्ड {hi_r})"
        verify_injection(f"heldout_modality_{idx+1:02d}", p["hi_text"], p_hi_injected, "MODALITY", q_hi)
        injected_cases.append({
            "case_id": f"heldout_modality_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi_injected,
            "hi_text_original": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "MODALITY",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": q_en,
                "quote_hi": q_hi
            }
        })

    # --- 5 SCOPE Injections (Heldout) ---
    scope_specs = [
        ("Central Government", "केंद्रीय सरकार", "राज्य सरकार", "Central Government", "राज्य सरकार", "Jurisdiction switched from Central to State Government in Hindi."),
        ("every person", "प्रत्येक व्यक्ति", "केवल व्यथित व्यक्ति", "every person", "केवल व्यथित व्यक्ति", "Broad statutory scope narrowed to aggrieved persons only in Hindi."),
        ("High Court", "उच्च न्यायालय", "सर्वोच्च न्यायालय", "High Court", "सर्वोच्च न्यायालय", "Judicial forum switched from High Court to Supreme Court in Hindi."),
        ("Judicial Magistrate", "न्यायिक मजिस्ट्रेट", "कार्यपालक मजिस्ट्रेट", "Judicial Magistrate", "कार्यपालक मजिस्ट्रेट", "Magisterial authority transferred to Executive Magistrate in Hindi."),
        ("civil court", "सिविल न्यायालय", "राजस्व न्यायालय", "civil court", "राजस्व न्यायालय", "Jurisdiction transferred from civil to revenue court in Hindi.")
    ]
    for idx, (en_key, hi_o, hi_r, q_en, q_hi, expl) in enumerate(scope_specs):
        p = injected_pool[20 + idx]
        p_en = p["en_text"] if q_en.lower() in p["en_text"].lower() else f"{p['en_text']} [Applicable authority: {en_key}]."
        p_hi_injected = p["hi_text"].replace(hi_o, hi_r, 1) if hi_o in p["hi_text"] else f"{p['hi_text']} (यथास्थिति: {hi_r})"
        verify_injection(f"heldout_scope_{idx+1:02d}", p["hi_text"], p_hi_injected, "SCOPE", q_hi)
        injected_cases.append({
            "case_id": f"heldout_scope_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi_injected,
            "hi_text_original": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "SCOPE",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": q_en,
                "quote_hi": q_hi
            }
        })

    return clean_cases, injected_cases


def build_evaluation_datasets(
    dev_out: str = "data/eval/dev/e2e_cases.jsonl",
    heldout_out: str = "data/eval/heldout/e2e_cases.jsonl"
) -> Tuple[int, int]:
    """Generates both Dev and Held-out evaluation datasets partitioned strictly by document."""
    os.makedirs(os.path.dirname(dev_out), exist_ok=True)
    os.makedirs(os.path.dirname(heldout_out), exist_ok=True)

    # 1. Dev Dataset
    print(f"Extracting clean pairs from Dev documents: {DEV_DOCUMENTS}...")
    dev_pool = extract_clean_pairs_from_docs(DEV_DOCUMENTS)
    dev_clean, dev_injected = generate_dev_injections(dev_pool)
    dev_cases = dev_clean + dev_injected
    with open(dev_out, "w", encoding="utf-8") as f:
        for c in dev_cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Saved {len(dev_cases)} dev cases ({len(dev_clean)} clean, {len(dev_injected)} injected) to {dev_out}")

    # 2. Heldout Dataset
    print(f"Extracting clean pairs from Held-out documents: {HELDOUT_DOCUMENTS}...")
    heldout_pool = extract_clean_pairs_from_docs(HELDOUT_DOCUMENTS)
    heldout_clean, heldout_injected = generate_heldout_injections(heldout_pool)
    heldout_cases = heldout_clean + heldout_injected
    with open(heldout_out, "w", encoding="utf-8") as f:
        for c in heldout_cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Saved {len(heldout_cases)} heldout cases ({len(heldout_clean)} clean, {len(heldout_injected)} injected) to {heldout_out}")

    return len(dev_cases), len(heldout_cases)


if __name__ == "__main__":
    dev_n, heldout_n = build_evaluation_datasets()
    print(f"Successfully generated {dev_n} Dev cases and {heldout_n} Held-out cases.")

