"""
build_semantic_cases.py - Generates Dev and Held-Out Semantic Evaluation Datasets.

Constructs:
  1. data/eval/dev/semantic_cases.jsonl:
     - 40 clean aligned pairs (no injected errors)
     - 40 injected pairs with meaning-level errors (labeled is_synthetic=True):
       * 8 MODALITY
       * 8 OMISSION
       * 8 ADDITION
       * 8 SCOPE
       * 8 DEFINITION
  2. data/eval/heldout/semantic_cases.jsonl:
     - 20 clean aligned pairs from held-out documents
     - 20 injected pairs (4 per category)
"""

import os
import json
import re
from typing import List, Dict, Any

from backend.app.ingest.split_language import process_document_pair
from backend.app.segment.segmenter import segment_document
from backend.app.align.aligner import align_document_trees


DEV_SLUGS = ["domestic_violence_2005", "right_to_information_2005", "environment_protection_1986"]
HELDOUT_SLUGS = ["contract_act_1872", "insolvency_bankruptcy_2016"]


def extract_aligned_pairs(slugs: List[str], data_dir: str = "data/raw") -> List[Dict[str, Any]]:
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
            # Must be structural or high similarity semantic match
            if not p.is_omission and p.similarity >= 0.72:
                en_len = len(p.en_text.split())
                hi_len = len(p.hi_text.split())
                if 10 <= en_len <= 120 and 10 <= hi_len <= 120:
                    pairs.append({
                        "act_slug": slug,
                        "en_paths": p.en_paths,
                        "hi_paths": p.hi_paths,
                        "en_text": p.en_text.strip(),
                        "hi_text": p.hi_text.strip(),
                        "similarity": p.similarity
                    })
    return pairs


def build_dev_dataset(output_path: str = "data/eval/dev/semantic_cases.jsonl") -> List[Dict[str, Any]]:
    """Builds the 80-case dev dataset (40 clean, 40 injected synthetic)."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    all_pairs = extract_aligned_pairs(DEV_SLUGS)

    if len(all_pairs) < 80:
        raise ValueError(f"Need at least 80 pairs, found {len(all_pairs)}")

    # 1. 40 Clean Pairs
    clean_cases = []
    for i in range(40):
        p = all_pairs[i]
        clean_cases.append({
            "case_id": f"dev_clean_{i+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p["en_text"],
            "hi_text": p["hi_text"],
            "is_synthetic": False,
            "expected_diff": False,
            "ground_truth": None
        })

    # 2. 40 Injected Pairs (40 pairs from index 40 onwards)
    injected_cases = []
    source_pool = all_pairs[40:80]

    # --- 8 MODALITY Cases ---
    modality_specs = [
        # 1-4: Mandatory to permissive (shall -> कर सकेगा)
        ("shall be given", "दी जाएगी", "दी जा सकेगी", "Mandatory duty weakened to discretionary permission", "shall be given", "दी जा सकेगी"),
        ("shall Endeavour to dispose", "प्रयास करेगा", "प्रयास कर सकेगा", "Mandatory judicial obligation changed to optional discretion", "shall Endeavour", "प्रयास कर सकेगा"),
        ("shall be deemed to be", "समझा जाएगा", "समझा जा सकेगा", "Mandatory legal fiction converted to discretionary presumption", "shall be deemed to be", "समझा जा सकेगा"),
        ("shall forward a copy", "प्रति अग्रेषित करेगा", "प्रति अग्रेषित कर सकेगा", "Mandatory reporting duty converted to discretionary action", "shall forward", "अग्रेषित कर सकेगा"),
        # 5-6: Permissive to mandatory (may -> करेगा)
        ("may grant an ex parte order", "आदेश दे सकेगा", "आदेश देगा", "Discretionary judicial relief converted to mandatory command", "may grant", "आदेश देगा"),
        ("may, on being satisfied", "समाधान होने पर... कर सकेगा", "समाधान होने पर... करेगा", "Discretionary relief converted to mandatory order", "may", "करेगा"),
        # 7-8: Negative prohibition to permission (shall not -> कर सकेगा)
        ("shall not be liable", "दायी नहीं होगा", "दायी हो सकेगा", "Statutory immunity converted to potential liability", "shall not be liable", "दायी हो सकेगा"),
        ("no court shall take cognizance", "कोई न्यायालय संज्ञान नहीं करेगा", "न्यायालय संज्ञान कर सकेगा", "Statutory jurisdictional bar converted to jurisdiction grant", "shall take cognizance", "संज्ञान कर सकेगा")
    ]

    for idx, (en_key, hi_orig, hi_repl, expl, q_en, q_hi) in enumerate(modality_specs):
        p = source_pool[idx]
        hi_text_mod = p["hi_text"].replace(hi_orig, hi_repl) if hi_orig in p["hi_text"] else p["hi_text"] + f" (यथास्थिति {hi_repl})"
        # Verify exact grounding in sources
        if q_en.lower() not in p["en_text"].lower():
            p_en = p["en_text"] + f" [The authority {q_en}]"
        else:
            p_en = p["en_text"]

        injected_cases.append({
            "case_id": f"dev_modality_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": hi_text_mod,
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

    # --- 8 OMISSION Cases ---
    omission_specs = [
        ("prior notice in writing", "लिखित सूचना दिए बिना", "Requirement of prior notice in writing present in English is omitted in Hindi", "prior notice in writing", None),
        ("after recording reasons in writing", "कारणों को लेखबद्ध करने के पश्चात्", "Mandatory duty to record written reasons omitted in Hindi", "recording reasons in writing", None),
        ("without prejudice to any other remedy", "किसी अन्य उपचार पर प्रतिकूल प्रभाव डाले बिना", "Clause safeguarding additional legal remedies omitted in Hindi", "without prejudice", None),
        ("with the prior approval of the Central Government", "केंद्रीय सरकार के पूर्व अनुमोदन से", "Requirement of Central Government prior approval omitted in Hindi", "prior approval of the Central Government", None),
        ("in the prescribed manner", "विहित रीति से", "Requirement to adhere to prescribed statutory procedure omitted in Hindi", "in the prescribed manner", None),
        ("subject to such conditions as may be imposed", "ऐसी शर्तों के अधीन रहते हुए जो अधिरोपित की जाएं", "Discretionary statutory conditions power omitted in Hindi", "subject to such conditions", None),
        ("within a reasonable time", "युक्तियुक्त समय के भीतर", "Procedural reasonable time limit omitted in Hindi", "reasonable time", None),
        ("after giving a reasonable opportunity of being heard", "सुनवाई का युक्तियुक्त अवसर देने के पश्चात्", "Fundamental natural justice hearing requirement omitted in Hindi", "opportunity of being heard", None)
    ]

    for idx, (en_frag, hi_frag, expl, q_en, q_hi) in enumerate(omission_specs):
        p = source_pool[8 + idx]
        p_en = p["en_text"] + f", provided that {en_frag} is given."
        # Hindi does NOT contain this requirement
        injected_cases.append({
            "case_id": f"dev_omission_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p["hi_text"],
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "OMISSION",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": q_en,
                "quote_hi": None
            }
        })

    # --- 8 ADDITION Cases ---
    addition_specs = [
        ("तथा ₹5,000 का अतिरिक्त शास्ति शुल्क संदाय करने पर ही", "Hindi adds an unmentioned prerequisite penalty fee of ₹5,000", None, "अतिरिक्त शास्ति शुल्क संदाय करने पर ही"),
        ("और केंद्रीय सरकार की पूर्व लिखित मंजूरी से ही", "Hindi adds a requirement of prior written sanction of the Central Government", None, "पूर्व लिखित मंजूरी से ही"),
        ("बशर्ते कि अपीलकर्ता जिला न्यायाधीश के समक्ष व्यक्तिगत रूप से उपस्थित हो", "Hindi adds an onerous requirement of mandatory personal appearance", None, "व्यक्तिगत रूप से उपस्थित हो"),
        ("तथा कम से कम दो राजपत्रित अधिकारियों के सत्यापन के अधीन", "Hindi adds an unmentioned verification condition by two gazetted officers", None, "दो राजपत्रित अधिकारियों के सत्यापन के अधीन"),
        ("और तीस दिन के भीतर हलफनामा दाखिल न करने पर आवेदन निरस्त समझा जाएगा", "Hindi introduces an automatic application cancellation penalty", None, "आवेदन निरस्त समझा जाएगा"),
        ("परंतु यह तब जब कि राज्य विधिक सेवा प्राधिकरण द्वारा प्रमाण-पत्र जारी किया गया हो", "Hindi adds an unmentioned certificate requirement from State Legal Services", None, "प्रमाण-पत्र जारी किया गया हो"),
        ("और ऐसी जांच के समस्त व्यय का भार व्यथित व्यक्ति वहन करेगा", "Hindi adds an unmentioned burden of investigation expenses on aggrieved person", None, "व्यय का भार व्यथित व्यक्ति वहन करेगा"),
        ("तथा द्वितीय अपील उच्च न्यायालय में ही संस्थित की जा सकेगी", "Hindi restricts second appeal forum exclusively to the High Court", None, "उच्च न्यायालय में ही संस्थित की जा सकेगी")
    ]

    for idx, (hi_added, expl, q_en, q_hi) in enumerate(addition_specs):
        p = source_pool[16 + idx]
        hi_text_mod = p["hi_text"] + f" {hi_added} ।"
        injected_cases.append({
            "case_id": f"dev_addition_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p["en_text"],
            "hi_text": hi_text_mod,
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

    # --- 8 SCOPE Cases ---
    scope_specs = [
        ("Central Government", "केंद्रीय सरकार", "राज्य सरकार", "Authority scope altered: Central Government replaced with State Government in Hindi", "Central Government", "राज्य सरकार"),
        ("every person", "प्रत्येक व्यक्ति", "केवल व्यथित व्यक्ति", "Entity scope narrowed: every person narrowed to aggrieved person only in Hindi", "every person", "केवल व्यथित व्यक्ति"),
        ("High Court", "उच्च न्यायालय", "सर्वोच्च न्यायालय", "Judicial forum scope shifted: High Court replaced with Supreme Court in Hindi", "High Court", "सर्वोच्च न्यायालय"),
        ("Judicial Magistrate", "न्यायिक मजिस्ट्रेट", "कार्यपालक मजिस्ट्रेट", "Jurisdiction shifted: Judicial Magistrate replaced with Executive Magistrate in Hindi", "Judicial Magistrate", "कार्यपालक मजिस्ट्रेट"),
        ("all complaints", "सभी परिवादों", "केवल प्रथम श्रेणी के परिवादों", "Subject-matter scope restricted in Hindi version", "all complaints", "केवल प्रथम श्रेणी के परिवादों"),
        ("throughout India", "संपूर्ण भारत", "केवल संघ राज्यक्षेत्रों", "Territorial jurisdiction narrowed from throughout India to Union Territories in Hindi", "throughout India", "केवल संघ राज्यक्षेत्रों"),
        ("any officer", "किसी अधिकारी", "केवल जिला मजिस्ट्रेट", "Designated officer scope narrowed to District Magistrate only in Hindi", "any officer", "केवल जिला मजिस्ट्रेट"),
        ("civil court", "सिविल न्यायालय", "राजस्व न्यायालय", "Court jurisdiction shifted from Civil Court to Revenue Court in Hindi", "civil court", "राजस्व न्यायालय")
    ]

    for idx, (en_target, hi_orig, hi_repl, expl, q_en, q_hi) in enumerate(scope_specs):
        p = source_pool[24 + idx]
        p_en = p["en_text"] if en_target.lower() in p["en_text"].lower() else p["en_text"] + f" [Authorized jurisdiction: {en_target}]."
        p_hi = p["hi_text"].replace(hi_orig, hi_repl) if hi_orig in p["hi_text"] else p["hi_text"] + f" (अधिकारिता: {hi_repl}) ।"

        injected_cases.append({
            "case_id": f"dev_scope_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi,
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

    # --- 8 DEFINITION Cases ---
    def_specs = [
        ("below the age of eighteen years", "अठारह वर्ष से कम", "सोलह वर्ष से कम आयु", "Statutory age definition threshold lowered from 18 to 16 in Hindi", "eighteen years", "सोलह वर्ष"),
        ("includes any adopted, step or foster child", "दत्तक बालक सम्मिलित है", "दत्तक बालक सम्मिलित नहीं है", "Definition exclusion: adopted children excluded from definition in Hindi", "includes any adopted", "सम्मिलित नहीं है"),
        ("shared household", "साझी गृहस्थी", "केवल पैतृक गृहस्थी", "Defined term scope narrowed from shared household to ancestral household in Hindi", "shared household", "केवल पैतृक गृहस्थी"),
        ("public authority", "लोक प्राधिकारी", "केवल सांविधिक निगम", "Definition of public authority narrowed to statutory corporations only in Hindi", "public authority", "केवल सांविधिक निगम"),
        ("aggrieved person", "व्यथित व्यक्ति", "केवल विवाहित महिला", "Definition narrowed from any woman in domestic relationship to married women only in Hindi", "aggrieved person", "केवल विवाहित महिला"),
        ("information", "सूचना", "केवल अंतिम रूप से अनुमोदित अभिलेख", "Definition of information narrowed to formally approved records only in Hindi", "information", "केवल अंतिम रूप से अनुमोदित अभिलेख"),
        ("third party", "पर-व्यक्ति", "केवल गैर-सरकारी व्यक्ति", "Third party definition restricted to non-governmental entities only in Hindi", "third party", "केवल गैर-सरकारी व्यक्ति"),
        ("competent authority", "सक्षम प्राधिकारी", "केवल राज्यपाल", "Competent authority definition restricted exclusively to Governor in Hindi", "competent authority", "केवल राज्यपाल")
    ]

    for idx, (en_frag, hi_orig, hi_repl, expl, q_en, q_hi) in enumerate(def_specs):
        p = source_pool[32 + idx]
        p_en = p["en_text"] if en_frag.lower() in p["en_text"].lower() else p["en_text"] + f" [Definition element: {en_frag}]."
        p_hi = p["hi_text"].replace(hi_orig, hi_repl) if hi_orig in p["hi_text"] else p["hi_text"] + f" (अर्थात् {hi_repl}) ।"

        injected_cases.append({
            "case_id": f"dev_definition_{idx+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi,
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": {
                "category": "DEFINITION",
                "severity": "HIGH",
                "explanation": expl,
                "quote_en": q_en,
                "quote_hi": q_hi
            }
        })

    all_dev_cases = clean_cases + injected_cases

    with open(output_path, "w", encoding="utf-8") as f:
        for c in all_dev_cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    return all_dev_cases


def build_heldout_dataset(output_path: str = "data/eval/heldout/semantic_cases.jsonl") -> List[Dict[str, Any]]:
    """Builds the frozen 40-case held-out dataset (20 clean, 20 injected synthetic)."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    all_pairs = extract_aligned_pairs(HELDOUT_SLUGS)

    if len(all_pairs) < 40:
        # Fall back to using remaining pairs from dev without overlapping with dev cases
        all_pairs = extract_aligned_pairs(DEV_SLUGS)[80:120]

    # 20 clean, 20 injected (4 per category)
    heldout_cases = []
    for i in range(20):
        p = all_pairs[i]
        heldout_cases.append({
            "case_id": f"heldout_clean_{i+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p["en_text"],
            "hi_text": p["hi_text"],
            "is_synthetic": False,
            "expected_diff": False,
            "ground_truth": None
        })

    # 20 injected
    source_pool = all_pairs[20:40]
    cats = ["MODALITY", "OMISSION", "ADDITION", "SCOPE", "DEFINITION"]
    for i in range(20):
        cat = cats[i % len(cats)]
        p = source_pool[i]
        if cat == "MODALITY":
            p_hi = p["hi_text"] + " (प्राधिकारी विवेकानुसार कर सकेगा) ।"
            p_en = p["en_text"] + " [The authority shall enforce this]."
            gt = {"category": "MODALITY", "severity": "HIGH", "explanation": "Heldout: mandatory vs discretionary shift", "quote_en": "shall", "quote_hi": "कर सकेगा"}
        elif cat == "OMISSION":
            p_hi = p["hi_text"]
            p_en = p["en_text"] + " [Subject to prior approval in writing]."
            gt = {"category": "OMISSION", "severity": "HIGH", "explanation": "Heldout: prior approval requirement omitted in Hindi", "quote_en": "prior approval in writing", "quote_hi": None}
        elif cat == "ADDITION":
            p_hi = p["hi_text"] + " परंतु ऐसा केवल विशेष न्यायाधिकरण की लिखित अनुमति से होगा ।"
            p_en = p["en_text"]
            gt = {"category": "ADDITION", "severity": "HIGH", "explanation": "Heldout: additional tribunal permission required in Hindi", "quote_en": None, "quote_hi": "विशेष न्यायाधिकरण की लिखित अनुमति"}
        elif cat == "SCOPE":
            p_hi = p["hi_text"] + " (अधिकारिता: केवल राज्य सरकार) ।"
            p_en = p["en_text"] + " [Jurisdiction: Central Government]."
            gt = {"category": "SCOPE", "severity": "HIGH", "explanation": "Heldout: jurisdiction shifted from Central to State Govt", "quote_en": "Central Government", "quote_hi": "राज्य सरकार"}
        else:
            p_hi = p["hi_text"] + " (अर्थात् केवल विधिक वारिस) ।"
            p_en = p["en_text"] + " [Definition: any representative]."
            gt = {"category": "DEFINITION", "severity": "HIGH", "explanation": "Heldout: definition restricted to legal heirs only", "quote_en": "any representative", "quote_hi": "केवल विधिक वारिस"}

        heldout_cases.append({
            "case_id": f"heldout_injected_{i+1:02d}",
            "act_slug": p["act_slug"],
            "en_paths": p["en_paths"],
            "hi_paths": p["hi_paths"],
            "en_text": p_en,
            "hi_text": p_hi,
            "is_synthetic": True,
            "expected_diff": True,
            "ground_truth": gt
        })

    with open(output_path, "w", encoding="utf-8") as f:
        for c in heldout_cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    return heldout_cases


if __name__ == "__main__":
    dev = build_dev_dataset()
    print(f"Generated {len(dev)} dev semantic cases in data/eval/dev/semantic_cases.jsonl")
    heldout = build_heldout_dataset()
    print(f"Generated {len(heldout)} held-out semantic cases in data/eval/heldout/semantic_cases.jsonl")
