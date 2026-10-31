"""
test_ingest.py - Unit tests for Tulya Ingestion Module (Phase Loop 1).
Includes unit tests with Hindi cases for Devanagari fraction, legacy font detection,
header/footer removal, hyphenation repair, and language splitting on synthetic data.
"""

import pytest
from backend.app.ingest.script_check import (
    devanagari_fraction,
    check_script,
    LegacyFontError
)
from backend.app.ingest.clean import (
    normalize_unicode,
    repair_hyphenation,
    detect_repeated_headers_footers,
    clean_page_text,
    clean_stream
)
from backend.app.ingest.split_language import split_bilingual_pages


# ---------------------------------------------------------
# 1. Tests for Devanagari Fraction
# ---------------------------------------------------------

def test_devanagari_fraction_pure_hindi():
    text = "सूचना का अधिकार अधिनियम, 2005"
    frac = devanagari_fraction(text)
    assert frac >= 0.95, f"Expected fraction near 1.0, got {frac}"


def test_devanagari_fraction_pure_english():
    text = "The Right to Information Act, 2005"
    frac = devanagari_fraction(text)
    assert frac == 0.0, f"Expected fraction 0.0, got {frac}"


def test_devanagari_fraction_mixed():
    text = "Section 3. सूचना का अधिकार"
    frac = devanagari_fraction(text)
    # 'Section' has 7 latin chars; 'सूचना का अधिकार' has 14 devanagari chars
    assert 0.40 <= frac <= 0.85, f"Expected mixed fraction, got {frac}"


def test_devanagari_fraction_empty_and_digits():
    assert devanagari_fraction("") == 0.0
    assert devanagari_fraction("1234567890 !@#$%^&*()") == 0.0


# ---------------------------------------------------------
# 2. Tests for Legacy Font Detection
# ---------------------------------------------------------

def test_legacy_font_detection_krutidev():
    # Hand-made synthetic KrutiDev string representing "भारत सरकार विधि और न्याय मंत्रालय"
    krutidev_garbage = "Hkkjr ljdkj fof/k vkSj U;k; ea=ky; fo/kk;h foHkkx"
    res = check_script(krutidev_garbage, expected_lang="hi", strict=False)
    assert res["verdict"] == "LEGACY_FONT_SUSPECTED"
    assert "Legacy non-Unicode" in res["message"]


def test_legacy_font_detection_high_ascii():
    # Hand-made synthetic high-ASCII legacy font string representing "भारत का संविधान"
    high_ascii_garbage = "£ÉÉ®iÉ BÉEÉ ºÉÆÉÊ´ÉvÉÉxÉ [1 ˜_, 2024 €Ȫ ™ ȡͪ ɮ™˜ȡ“]"
    res = check_script(high_ascii_garbage, expected_lang="hi", strict=False)
    assert res["verdict"] == "LEGACY_FONT_SUSPECTED"


def test_legacy_font_strict_exception():
    krutidev_garbage = "Hkkjr ljdkj fof/k vkSj U;k; ea=ky;"
    with pytest.raises(LegacyFontError) as exc_info:
        check_script(krutidev_garbage, expected_lang="hi", strict=True)
    assert "Legacy non-Unicode Hindi font detected" in str(exc_info.value)


def test_unicode_hindi_passes_check():
    clean_hindi = "भारत का संविधान [10 सितम्बर, 2026 को यथाविद्यमान] भारत सरकार विधि और न्याय मंत्रालय"
    res = check_script(clean_hindi, expected_lang="hi", strict=True)
    assert res["verdict"] == "OK_UNICODE_HINDI"
    assert res["devanagari_fraction"] >= 0.80


# ---------------------------------------------------------
# 3. Tests for Hyphenation Repair
# ---------------------------------------------------------

def test_hyphenation_repair_english():
    broken = "This is a regula-\ntion under the Act to provide infor-\nmation."
    repaired = repair_hyphenation(broken)
    assert "regulation" in repaired
    assert "information" in repaired
    assert "regula-\ntion" not in repaired


def test_hyphenation_repair_hindi():
    broken = "यह अधि-\nनियम नागरिकों को पारदर्-\nशिता प्रदान करता है।"
    repaired = repair_hyphenation(broken)
    assert "अधिनियम" in repaired
    assert "पारदर्शिता" in repaired
    assert "अधि-\nनियम" not in repaired


# ---------------------------------------------------------
# 4. Tests for Header / Footer Removal
# ---------------------------------------------------------

def test_header_footer_removal():
    # 4 synthetic pages with repeated headers and footers
    pages = [
        "THE GAZETTE OF INDIA : EXTRAORDINARY\n[PART II—SEC. 1]\n1. Short title and commencement.\n(1) This Act may be called the Test Act.\nPage 1 of 4",
        "THE GAZETTE OF INDIA : EXTRAORDINARY\n[PART II—SEC. 1]\n2. Definitions.\nIn this Act, unless the context otherwise requires:\nPage 2 of 4",
        "THE GAZETTE OF INDIA : EXTRAORDINARY\n[PART II—SEC. 1]\n3. Obligation of public authorities.\nEvery public authority shall maintain records.\nPage 3 of 4",
        "THE GAZETTE OF INDIA : EXTRAORDINARY\n[PART II—SEC. 1]\n4. Miscellaneous provisions.\nPowers to make rules.\nPage 4 of 4"
    ]

    repeated = detect_repeated_headers_footers(pages, threshold=0.50)
    assert "THE GAZETTE OF INDIA : EXTRAORDINARY" in repeated
    assert "[PART II—SEC. 1]" in repeated

    cleaned = clean_page_text(pages[0], repeated)
    assert "THE GAZETTE OF INDIA : EXTRAORDINARY" not in cleaned
    assert "[PART II—SEC. 1]" not in cleaned
    assert "Page 1 of 4" not in cleaned
    assert "1. Short title and commencement." in cleaned
    assert "(1) This Act may be called the Test Act." in cleaned


def test_hindi_header_footer_removal():
    pages = [
        "भारत का राजपत्र : असाधारण\n[भाग II—खण्ड 1]\nधारा 1. संक्षिप्त नाम और प्रारंभ।\n(1) यह अधिनियम कहा जा सकेगा।\nपृष्ठ 1",
        "भारत का राजपत्र : असाधारण\n[भाग II—खण्ड 1]\nधारा 2. परिभाषाएं।\nइस अधिनियम में, जब तक कि संदर्भ से अन्यथा अपेक्षित न हो:\nपृष्ठ 2",
        "भारत का राजपत्र : असाधारण\n[भाग II—खण्ड 1]\nधारा 3. लोक प्राधिकारियों की बाध्यताएं।\nप्रत्येक लोक प्राधिकारी अभिलेख रखेगा।\nपृष्ठ 3"
    ]

    repeated = detect_repeated_headers_footers(pages, threshold=0.50)
    assert "भारत का राजपत्र : असाधारण" in repeated
    assert "[भाग II—खण्ड 1]" in repeated

    cleaned = clean_page_text(pages[0], repeated)
    assert "भारत का राजपत्र : असाधारण" not in cleaned
    assert "धारा 1. संक्षिप्त नाम और प्रारंभ।" in cleaned
    assert "(1) यह अधिनियम कहा जा सकेगा।" in cleaned


# ---------------------------------------------------------
# 5. Tests for Language Splitting on Synthetic Two-Column / Mixed PDF
# ---------------------------------------------------------

def test_language_splitting_synthetic_bilingual():
    """
    Synthetic bilingual page data representing two columns / interleaved clauses:
    English on one stream, Hindi on the other.
    """
    synthetic_raw_pages = [
        {
            "page_no": 1,
            "raw_text": (
                "THE RIGHT TO INFORMATION ACT, 2005\n"
                "An Act to provide for setting out the practical regime of right to information.\n"
                "सूचना का अधिकार अधिनियम, 2005\n"
                "नागरिकों को सूचना के अधिकार की व्यावहारिक पद्धति स्थापित करने के लिए अधिनियम।"
            ),
            "method": "synthetic_test"
        },
        {
            "page_no": 2,
            "raw_text": (
                "Section 1. Short title, extent and commencement.\n"
                "(1) This Act may be called the Right to Information Act, 2005.\n"
                "धारा 1. संक्षिप्त नाम, विस्तार और प्रारंभ।\n"
                "(1) इस अधिनियम का संक्षिप्त नाम सूचना का अधिकार अधिनियम, 2005 है।"
            ),
            "method": "synthetic_test"
        }
    ]

    en_pages, hi_pages, warnings = split_bilingual_pages(synthetic_raw_pages)

    assert len(en_pages) == 2
    assert len(hi_pages) == 2

    # Check English content
    en_text_p1 = en_pages[0]["raw_text"]
    assert "THE RIGHT TO INFORMATION ACT, 2005" in en_text_p1
    assert "An Act to provide for setting out" in en_text_p1
    assert "सूचना का अधिकार" not in en_text_p1

    # Check Hindi content
    hi_text_p1 = hi_pages[0]["raw_text"]
    assert "सूचना का अधिकार अधिनियम, 2005" in hi_text_p1
    assert "नागरिकों को सूचना के अधिकार" in hi_text_p1
    assert "THE RIGHT TO INFORMATION" not in hi_text_p1
