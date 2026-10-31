"""
test_segment.py - Unit tests for Phase Loop 2 (Structural Segmentation).
Tests section parsing, monotonic subsection enforcement, Hindi numeral/letter mappings,
provisos, explanations, and prevention of inline sentence false splits.
"""

import pytest
from backend.app.segment.models import ClauseNode, ClauseTree
from backend.app.segment.numbering import (
    devanagari_to_arabic,
    normalize_section_number,
    normalize_clause_letter,
    is_roman_numeral,
    roman_to_int
)
from backend.app.segment.segmenter import (
    segment_document,
    parse_section_header,
    find_substantive_start
)


class TestNumberingNormalization:
    """Tests for script translation and numbering normalizers."""

    def test_devanagari_digit_conversion(self):
        assert devanagari_to_arabic("१२३४५") == "12345"
        assert devanagari_to_arabic("०९") == "09"
        assert devanagari_to_arabic("धारा १२") == "धारा 12"

    def test_section_number_normalization(self):
        assert normalize_section_number("12") == "12"
        assert normalize_section_number("12A") == "12A"
        assert normalize_section_number("१२") == "12"
        assert normalize_section_number("१२क") == "12A"
        assert normalize_section_number("५ख") == "5B"

    def test_clause_letter_normalization(self):
        assert normalize_clause_letter("a") == "a"
        assert normalize_clause_letter("A") == "a"
        assert normalize_clause_letter("क") == "a"
        assert normalize_clause_letter("ख") == "b"
        assert normalize_clause_letter("ग") == "c"
        assert normalize_clause_letter("ङ") == "e"
        assert normalize_clause_letter("च") == "f"
        assert normalize_clause_letter("छ") == "g"
        assert normalize_clause_letter("न") == "t"

    def test_roman_numeral_parsing(self):
        assert is_roman_numeral("i") is True
        assert is_roman_numeral("iv") is True
        assert is_roman_numeral("xvii") is True
        assert is_roman_numeral("abc") is False
        assert roman_to_int("iii") == 3
        assert roman_to_int("v") == 5


class TestSectionHeadingDetection:
    """Tests for section boundary detection in English and Hindi."""

    def test_english_section_header(self):
        res = parse_section_header("1. Short title, extent and commencement.—(1) This Act...", expected_num=1, current_num=0)
        assert res is not None
        sec_id, title, rest = res
        assert sec_id == "1"
        assert "Short title" in title
        assert "(1) This Act..." in rest

    def test_hindi_section_header(self):
        res = parse_section_header("1. संक्षिप्त नाम, विस्तार और प्रारम्भ––(1) इस अधिनियम का...", expected_num=1, current_num=0)
        assert res is not None
        sec_id, title, rest = res
        assert sec_id == "1"
        assert "संक्षिप्त नाम" in title
        assert "(1) इस अधिनियम का..." in rest

    def test_inserted_section_header(self):
        # 5A after 5
        res = parse_section_header("5A. Appeal to National Green Tribunal.—Any person...", expected_num=6, current_num=5)
        assert res is not None
        sec_id, title, _ = res
        assert sec_id == "5A"

    def test_footnote_exclusion(self):
        # Footnotes starting with '1. Ins. by Act' must not be parsed as Section 1
        res = parse_section_header("1. Ins. by Act 18 of 2023, s. 2 and Schedule", expected_num=1, current_num=14)
        assert res is None


class TestMonotonicSegmentation:
    """Tests ensuring numbers inside sentences do not split clauses."""

    def test_prevent_inline_numbers_splitting_clauses(self):
        raw_text = """1. Short title, extent and commencement.—(1) This Act may be called the Test Act.
(2) Subject to sub-section (1), it shall come into force within (2) months from the date of assent.
(3) In accordance with section 4 and clause (b) of sub-section (1), notifications shall be issued.
2. Definitions.—In this Act, unless the context otherwise requires,—
(a) "court" means any civil court referred to in section 9;
(b) "officer" means an officer of rank (2) or higher."""

        pages = [{"page_no": 1, "text": raw_text}]
        tree = segment_document(pages, lang="en", act_slug="test_act")

        assert len(tree.sections) == 2
        sec1 = tree.sections[0]
        assert sec1.path == "1"
        # Only 3 subsections: (1), (2), (3)
        assert [c.path for c in sec1.children] == ["1.1", "1.2", "1.3"]
        # Subsection 1.2 should contain "within (2) months" as inline text without creating a spurious clause
        assert "within (2) months" in sec1.children[1].text

        sec2 = tree.sections[1]
        assert sec2.path == "2"
        # Clauses 2.a and 2.b
        assert [c.path for c in sec2.children] == ["2.a", "2.b"]
        assert "rank (2) or higher" in sec2.children[1].text

    def test_hindi_monotonic_subsections_and_clauses(self):
        raw_text = """भारत गणराज्य के वर्ष में संसद् द्वारा निम्नलिखित रूप में यह अधिनियमित हो :—
1. संक्षिप्त नाम, विस्तार और प्रारम्भ––––(1) इस अधिनियम का संक्षिप्त नाम परीक्षण अधिनियम है ।
(2) उपधारा (1) के उपबंधों के अधीन रहते हुए यह (30) दिन के भीतर प्रवृत्त होगा ।
2. परिभाषाएं––इस अधिनियम में, जब तक कि संदर्भ से अन्यथा अपेक्षित न हो,––
(क) “न्यायालय” से धारा 9 में निर्दिष्ट कोई सिविल न्यायालय अभिप्रेत है ;
(ख) “अधिकारी” से श्रेणी (2) का कोई अधिकारी अभिप्रेत है ।"""

        pages = [{"page_no": 1, "text": raw_text}]
        tree = segment_document(pages, lang="hi", act_slug="test_act_hi")

        assert len(tree.sections) == 2
        sec1 = tree.sections[0]
        assert sec1.path == "1"
        assert [c.path for c in sec1.children] == ["1.1", "1.2"]
        assert "(30) दिन" in sec1.children[1].text

        sec2 = tree.sections[1]
        assert sec2.path == "2"
        assert [c.path for c in sec2.children] == ["2.a", "2.b"]
        assert "श्रेणी (2)" in sec2.children[1].text


class TestProvisosAndExplanations:
    """Tests for provisos and explanations segmentation."""

    def test_provisos_and_explanations_english(self):
        raw_text = """3. Definition of domestic violence.—For the purposes of this Act, any conduct constitutes violence in case it—
(a) harms the aggrieved person; or
(b) harasses the aggrieved person:
Provided that an aggrieved person may file a complaint:
Provided further that no complaint shall be dismissed without hearing.
Explanation I.—For the purposes of this section, conduct includes gestures.
Explanation II.—For determining intention, regard shall be had to the overall context."""

        pages = [{"page_no": 1, "text": raw_text}]
        tree = segment_document(pages, lang="en", act_slug="test_proviso_en")

        assert len(tree.sections) == 1
        sec3 = tree.sections[0]
        paths = [c.path for c in sec3.flatten()]
        assert "3.a" in paths
        assert "3.b" in paths
        assert "3.proviso_1" in paths
        assert "3.proviso_2" in paths
        assert "3.explanation_1" in paths
        assert "3.explanation_2" in paths

    def test_provisos_and_explanations_hindi(self):
        raw_text = """3. घरेलू हिंसा की परिभाषा—इस अधिनियम के प्रयोजनों के लिए, कोई आचरण घरेलू हिंसा गठित करेगा यदि वह—
(क) व्यथित व्यक्ति को नुकसान पहुंचाता है; या
(ख) व्यथित व्यक्ति को परेशान करता है :
परन्तु यह कि व्यथित व्यक्ति कोई परिवाद फाइल कर सकेगा :
परन्तु यह और कि सुनवाई के बिना कोई परिवाद खारिज नहीं किया जाएगा ।
स्पष्टीकरण 1—इस धारा के प्रयोजनों के लिए आचरण के अंतर्गत संकेत भी हैं ।
स्पष्टीकरण 2—आशय का अवधारण करने के लिए समग्र संदर्भ का ध्यान रखा जाएगा ।"""

        pages = [{"page_no": 1, "text": raw_text}]
        tree = segment_document(pages, lang="hi", act_slug="test_proviso_hi")

        assert len(tree.sections) == 1
        sec3 = tree.sections[0]
        paths = [c.path for c in sec3.flatten()]
        assert "3.a" in paths
        assert "3.b" in paths
        assert "3.proviso_1" in paths
        assert "3.proviso_2" in paths
        assert "3.explanation_1" in paths
        assert "3.explanation_2" in paths


class TestTableOfContentsSkipping:
    """Tests that front-matter Table of Contents is skipped."""

    def test_skip_toc_in_english(self):
        pages = [
            {"page_no": 1, "text": "ARRANGEMENT OF SECTIONS\n1. Short title.\n2. Definitions.\n3. Powers."},
            {"page_no": 2, "text": "BE it enacted by Parliament in the Fifty-sixth Year as follows:—\n1. Short title, extent and commencement.—(1) This Act may be called Actual Act.\n2. Definitions.—In this Act..."}
        ]
        tree = segment_document(pages, lang="en", act_slug="test_toc_en")
        assert len(tree.sections) == 2
        assert tree.sections[0].path == "1"
        assert tree.sections[0].page_no == 2
        assert "Actual Act" in tree.sections[0].children[0].text

    def test_skip_toc_in_hindi(self):
        pages = [
            {"page_no": 1, "text": "धाराओं का क्रम\n1. संक्षिप्त नाम ।\n2. परिभाषाएं ।"},
            {"page_no": 2, "text": "भारत गणराज्य के वर्ष में संसद् द्वारा निम्नलिखित रूप में यह अधिनियमित हो :—\n1. संक्षिप्त नाम, विस्तार और प्रारम्भ––(1) इस अधिनियम का नाम वास्तविक अधिनियम है ।\n2. परिभाषाएं––इस अधिनियम में..."}
        ]
        tree = segment_document(pages, lang="hi", act_slug="test_toc_hi")
        assert len(tree.sections) == 2
        assert tree.sections[0].path == "1"
        assert tree.sections[0].page_no == 2
        assert "वास्तविक अधिनियम" in tree.sections[0].children[0].text
