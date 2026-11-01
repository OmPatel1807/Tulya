"""
extractor.py - Robust Bilingual Legal Fact Extractor for English and Hindi.
Extracts numbers, percentages, money, duration, area/length, multipliers, dates,
and section references while masking leading clause enumeration labels.
Handles Devanagari vowel sign boundaries and multi-word scale compositions (lakh, crore).
"""

import re
from typing import List, Tuple, Set, Optional, Dict, Any

from backend.app.facts.models import FactType, FactSpan
from backend.app.facts.number_words import (
    devanagari_digits_to_arabic,
    parse_number_token,
    parse_english_number_words,
    parse_hindi_number_words,
    HI_NUMBERS,
    HI_ORDINALS,
    HI_SCALES,
    HI_FRACTIONS,
    EN_UNITS,
    EN_ORDINALS,
    EN_SCALES
)
from backend.app.facts.units import (
    DURATION_UNIT_MAP,
    AREA_LENGTH_UNIT_MAP,
    CURRENCY_MARKERS,
    MULTIPLIER_WORDS,
    GREGORIAN_MONTHS,
    SAKA_MONTHS
)
from backend.app.segment.numbering import (
    normalize_clause_letter,
    normalize_section_number
)

# Pattern to detect leading clause enumeration labels (e.g. "(1)", "(2)", "(a)", "(क)", "12.")
ENUMERATION_PREFIX_PATTERN = re.compile(
    r'^\s*(?:\d*\[)?[—–-]*\s*(?:\([०-९\d]+|[a-zA-Z]|[\u0900-\u097F]+\)|\d+[A-Za-z]?[.—–:\-])\s*'
)

B_START = r'(?:^|[.,:;!?।—–\-(/\[\s])'
B_END = r'(?=[.,:;!?।—–\-/\)\]\s]|$)'


class IntervalMask:
    """Tracks occupied character intervals to prevent overlapping sub-entity extraction."""

    def __init__(self):
        self.intervals: List[Tuple[int, int]] = []

    def add(self, start: int, end: int):
        self.intervals.append((start, end))

    def overlaps(self, start: int, end: int) -> bool:
        for s, e in self.intervals:
            if max(start, s) < min(end, e):
                return True
        return False


def get_enumeration_prefix_length(text: str) -> int:
    """Returns the end index of any leading clause enumeration label."""
    m = ENUMERATION_PREFIX_PATTERN.match(text)
    return m.end() if m else 0


def collect_preceding_number_words(text: str, unit_start: int, is_hindi: bool = False) -> Tuple[Optional[float], Optional[Tuple[int, int]], str]:
    """
    Scans backward from unit_start in text to collect all consecutive number words.
    Returns (parsed_value, (phrase_start, phrase_end), phrase_raw).
    """
    prefix_text = text[:unit_start]
    # Find all words with character spans before unit_start
    word_matches = list(re.finditer(r'[^\s.,:;!?।—–\(\)\[\]/]+', prefix_text))
    if not word_matches:
        return None, None, ""

    num_set = {**HI_NUMBERS, **HI_SCALES, **HI_FRACTIONS, **HI_ORDINALS} if is_hindi else {**EN_UNITS, **EN_SCALES, **EN_ORDINALS}

    collected_words = []
    first_match = None
    last_match = None

    for wm in reversed(word_matches):
        raw_word = wm.group(0)
        norm_key = raw_word if is_hindi else raw_word.lower().strip("-")

        # Check if it's a known number word or pure number token (digits)
        is_num_word = norm_key in num_set or (not is_hindi and norm_key == "and")
        is_num_digit = parse_number_token(raw_word) is not None

        if is_num_word or is_num_digit:
            collected_words.append(raw_word)
            if last_match is None:
                last_match = wm
            first_match = wm
        else:
            break

    if not collected_words or first_match is None or last_match is None:
        return None, None, ""

    collected_words.reverse()
    val = parse_hindi_number_words(collected_words) if is_hindi else parse_english_number_words(collected_words)
    if val is not None and val > 0:
        return val, (first_match.start(), last_match.end()), text[first_match.start():last_match.end()]

    return None, None, ""


def extract_dates(text: str, mask: IntervalMask) -> List[FactSpan]:
    """Extracts explicit calendar dates in English and Hindi."""
    facts = []

    # 1. Day Month Year: e.g. "15th January, 2020", "15 जनवरी 2020", "१५ जनवरी, २०२०"
    p_dmy = re.compile(
        rf'{B_START}([०-९\d]{{1,2}})(?:st|nd|rd|th)?\s*(?:day\s+of\s+)?([A-Za-z\u0900-\u097F]+)[,\s]+([०-९\d]{{4}}){B_END}'
    )
    for m in p_dmy.finditer(text):
        start = m.start(1)
        end = m.end(3)
        if mask.overlaps(start, end):
            continue

        day_str = devanagari_digits_to_arabic(m.group(1))
        month_word = m.group(2).lower()
        year_str = devanagari_digits_to_arabic(m.group(3))

        month_num = GREGORIAN_MONTHS.get(month_word) or SAKA_MONTHS.get(month_word)
        if month_num is not None:
            day_int = int(day_str)
            year_int = int(year_str)
            if 1 <= day_int <= 31 and 1800 <= year_int <= 2100:
                iso_date = f"{year_int:04d}-{month_num:02d}-{day_int:02d}"
                mask.add(start, end)
                facts.append(
                    FactSpan(
                        fact_type=FactType.DATE,
                        raw_text=text[start:end],
                        normalized_value=iso_date,
                        unit="date",
                        start_char=start,
                        end_char=end
                    )
                )

    # 2. Month Day, Year: e.g. "January 15, 2020", "जनवरी 15, 2020"
    p_mdy = re.compile(
        rf'{B_START}([A-Za-z\u0900-\u097F]+)\s+([०-९\d]{{1,2}})(?:st|nd|rd|th)?[,\s]+([०-९\d]{{4}}){B_END}'
    )
    for m in p_mdy.finditer(text):
        start = m.start(1)
        end = m.end(3)
        if mask.overlaps(start, end):
            continue

        month_word = m.group(1).lower()
        day_str = devanagari_digits_to_arabic(m.group(2))
        year_str = devanagari_digits_to_arabic(m.group(3))

        month_num = GREGORIAN_MONTHS.get(month_word) or SAKA_MONTHS.get(month_word)
        if month_num is not None:
            day_int = int(day_str)
            year_int = int(year_str)
            if 1 <= day_int <= 31 and 1800 <= year_int <= 2100:
                iso_date = f"{year_int:04d}-{month_num:02d}-{day_int:02d}"
                mask.add(start, end)
                facts.append(
                    FactSpan(
                        fact_type=FactType.DATE,
                        raw_text=text[start:end],
                        normalized_value=iso_date,
                        unit="date",
                        start_char=start,
                        end_char=end
                    )
                )

    # 3. Numeric Dates: "DD.MM.YYYY" or "DD/MM/YYYY" or "DD-MM-YYYY"
    p_num = re.compile(rf'{B_START}([०-९\d]{{1,2}})[\.\/\-]([०-९\d]{{1,2}})[\.\/\-]([०-९\d]{{4}}){B_END}')
    for m in p_num.finditer(text):
        start = m.start(1)
        end = m.end(3)
        if mask.overlaps(start, end):
            continue

        day_int = int(devanagari_digits_to_arabic(m.group(1)))
        month_int = int(devanagari_digits_to_arabic(m.group(2)))
        year_int = int(devanagari_digits_to_arabic(m.group(3)))

        if 1 <= day_int <= 31 and 1 <= month_int <= 12 and 1800 <= year_int <= 2100:
            iso_date = f"{year_int:04d}-{month_int:02d}-{day_int:02d}"
            mask.add(start, end)
            facts.append(
                FactSpan(
                    fact_type=FactType.DATE,
                    raw_text=text[start:end],
                    normalized_value=iso_date,
                    unit="date",
                    start_char=start,
                    end_char=end
                )
            )

    return facts


def extract_money(text: str, mask: IntervalMask) -> List[FactSpan]:
    """Extracts monetary amounts in Rupees, normalizing lakhs and crores."""
    facts = []

    # 1. Prefix currency symbols: e.g. "Rs. 50,000", "₹ 1.5 lakh", "रु. ५०,०००", "INR 10 crore"
    p_prefix = re.compile(
        rf'{B_START}(Rs\.?|₹|INR|रु\.?|रु)\s*([०-९\d,]+(?:\.[०-९\d]+)?)\s*(crores?|lakhs?|lacs?|million|करोड़|लाख)?{B_END}',
        re.IGNORECASE
    )
    for m in p_prefix.finditer(text):
        start = m.start(1)
        end = m.end(3) if m.group(3) else m.end(2)
        if mask.overlaps(start, end):
            continue

        val = parse_number_token(m.group(2))
        if val is None:
            continue

        scale_word = (m.group(3) or "").lower()
        if scale_word in ("crore", "crores", "करोड़"):
            val *= 10000000.0
        elif scale_word in ("lakh", "lakhs", "lac", "lacs", "लाख"):
            val *= 100000.0
        elif scale_word == "million":
            val *= 1000000.0

        mask.add(start, end)
        facts.append(
            FactSpan(
                fact_type=FactType.MONEY,
                raw_text=text[start:end],
                normalized_value=val,
                unit="INR",
                start_char=start,
                end_char=end
            )
        )

    # 2. Suffix currency unit with digits: e.g. "50,000 rupees", "५०,००० रुपये", "5 lakh rupees", "10 करोड़ रुपये"
    p_suffix_num = re.compile(
        rf'{B_START}([०-९\d,]+(?:\.[०-९\d]+)?)\s*(crores?|lakhs?|lacs?|million|करोड़|लाख)?\s*(rupees|rupee|रुपये|रुपया|रुपए){B_END}',
        re.IGNORECASE
    )
    for m in p_suffix_num.finditer(text):
        start = m.start(1)
        end = m.end(3)
        if mask.overlaps(start, end):
            continue

        val = parse_number_token(m.group(1))
        if val is None:
            continue

        scale_word = (m.group(2) or "").lower()
        if scale_word in ("crore", "crores", "करोड़"):
            val *= 10000000.0
        elif scale_word in ("lakh", "lakhs", "lac", "lacs", "लाख"):
            val *= 100000.0
        elif scale_word == "million":
            val *= 1000000.0

        mask.add(start, end)
        facts.append(
            FactSpan(
                fact_type=FactType.MONEY,
                raw_text=text[start:end],
                normalized_value=val,
                unit="INR",
                start_char=start,
                end_char=end
            )
        )

    # 3. Suffix currency unit with written words (e.g. "fifty thousand rupees", "पचास हजार रुपये")
    p_rupee_marker = re.compile(rf'{B_START}(rupees|rupee|रुपये|रुपया|रुपए){B_END}', re.IGNORECASE)
    for m in p_rupee_marker.finditer(text):
        u_start = m.start(1)
        u_end = m.end(1)
        if mask.overlaps(u_start, u_end):
            continue

        marker_str = m.group(1).lower()
        is_hindi = marker_str in ("रुपये", "रुपया", "रुपए")

        val, span, raw_phrase = collect_preceding_number_words(text, u_start, is_hindi=is_hindi)
        if val is not None and span is not None:
            full_start = span[0]
            full_end = u_end
            if not mask.overlaps(full_start, full_end):
                mask.add(full_start, full_end)
                facts.append(
                    FactSpan(
                        fact_type=FactType.MONEY,
                        raw_text=text[full_start:full_end],
                        normalized_value=val,
                        unit="INR",
                        start_char=full_start,
                        end_char=full_end
                    )
                )

    return facts


def extract_percentages(text: str, mask: IntervalMask) -> List[FactSpan]:
    """Extracts percentage facts (e.g. '10%', '10 percent', 'दस प्रतिशत')."""
    facts = []

    # 1. Digits followed by % or percent / प्रतिशत
    p_pct_num = re.compile(
        rf'{B_START}([०-९\d,]+(?:\.[०-९\d]+)?)\s*(%|percent|per cent|प्रतिशत|फीसद|फीसदी|फ़ीसदी){B_END}',
        re.IGNORECASE
    )
    for m in p_pct_num.finditer(text):
        start = m.start(1)
        end = m.end(2)
        if mask.overlaps(start, end):
            continue

        val = parse_number_token(m.group(1))
        if val is not None:
            mask.add(start, end)
            facts.append(
                FactSpan(
                    fact_type=FactType.PERCENT,
                    raw_text=text[start:end],
                    normalized_value=val,
                    unit="%",
                    start_char=start,
                    end_char=end
                )
            )

    # 2. Number words followed by percent / प्रतिशत
    p_pct_marker = re.compile(rf'{B_START}(percent|per cent|प्रतिशत|फीसदी){B_END}', re.IGNORECASE)
    for m in p_pct_marker.finditer(text):
        u_start = m.start(1)
        u_end = m.end(1)
        if mask.overlaps(u_start, u_end):
            continue

        marker_str = m.group(1).lower()
        is_hindi = marker_str in ("प्रतिशत", "फीसदी")

        val, span, raw_phrase = collect_preceding_number_words(text, u_start, is_hindi=is_hindi)
        if val is not None and span is not None:
            full_start = span[0]
            full_end = u_end
            if not mask.overlaps(full_start, full_end):
                mask.add(full_start, full_end)
                facts.append(
                    FactSpan(
                        fact_type=FactType.PERCENT,
                        raw_text=text[full_start:full_end],
                        normalized_value=val,
                        unit="%",
                        start_char=full_start,
                        end_char=full_end
                    )
                )

    return facts


def extract_durations(text: str, mask: IntervalMask) -> List[FactSpan]:
    """Extracts statutory duration limits (days, months, years, weeks, hours, minutes)."""
    facts = []

    duration_keywords_regex = r'(?:days?|weeks?|months?|years?|annum|hours?|minutes?|दिन|दिवस|ददि|सप्ताह|हफ्ते|हफ्ता|मास|माह|महीने|महीना|वर्ष|साल|िषत|घंटे|घंटा|मिनट)'

    # 1. Digits followed by unit
    p_dur_num = re.compile(
        rf'{B_START}([०-९\d,]+(?:\.[०-९\d]+)?)\s*({duration_keywords_regex}){B_END}',
        re.IGNORECASE
    )
    for m in p_dur_num.finditer(text):
        start = m.start(1)
        end = m.end(2)
        if mask.overlaps(start, end):
            continue

        val = parse_number_token(m.group(1))
        unit_raw = m.group(2).lower()
        unit_canon = DURATION_UNIT_MAP.get(unit_raw)

        if val is not None and unit_canon:
            mask.add(start, end)
            facts.append(
                FactSpan(
                    fact_type=FactType.DURATION,
                    raw_text=text[start:end],
                    normalized_value=val,
                    unit=unit_canon,
                    start_char=start,
                    end_char=end
                )
            )

    # 2. Number words followed by duration unit
    p_dur_marker = re.compile(rf'{B_START}({duration_keywords_regex}){B_END}', re.IGNORECASE)
    for m in p_dur_marker.finditer(text):
        u_start = m.start(1)
        u_end = m.end(1)
        if mask.overlaps(u_start, u_end):
            continue

        unit_raw = m.group(1).lower()
        unit_canon = DURATION_UNIT_MAP.get(unit_raw)
        if not unit_canon:
            continue

        is_hindi = any('\u0900' <= ch <= '\u097F' for ch in unit_raw)

        val, span, raw_phrase = collect_preceding_number_words(text, u_start, is_hindi=is_hindi)
        if val is not None and span is not None:
            full_start = span[0]
            full_end = u_end
            if not mask.overlaps(full_start, full_end):
                mask.add(full_start, full_end)
                facts.append(
                    FactSpan(
                        fact_type=FactType.DURATION,
                        raw_text=text[full_start:full_end],
                        normalized_value=val,
                        unit=unit_canon,
                        start_char=full_start,
                        end_char=full_end
                    )
                )

    return facts


def extract_area_length(text: str, mask: IntervalMask) -> List[FactSpan]:
    """Extracts area and length units (acres, hectares, sq metres, km, metres)."""
    facts = []

    area_keywords_regex = r'(?:acres?|एकड़|hectares?|हेक्टेयर|sq\.?\s*metres?|square metres?|square meters?|वर्ग मीटर|sq\.?\s*ft|square feet?|वर्ग फुट|sq\.?\s*yards?|वर्ग गज|kilometres?|kilometers?|kms?|किलोमीटर|किमी|कि\.मी\.|metres?|meters?|मीटर|centimetres?|centimeters?|cm|सेंटीमीटर|सेमी|miles?|मील)'

    # 1. Digits followed by unit
    p_unit_num = re.compile(
        rf'{B_START}([०-९\d,]+(?:\.[०-९\d]+)?)\s*({area_keywords_regex}){B_END}',
        re.IGNORECASE
    )
    for m in p_unit_num.finditer(text):
        start = m.start(1)
        end = m.end(2)
        if mask.overlaps(start, end):
            continue

        val = parse_number_token(m.group(1))
        unit_raw = m.group(2).lower().replace("  ", " ")
        unit_canon = AREA_LENGTH_UNIT_MAP.get(unit_raw)
        if not unit_canon:
            unit_canon = AREA_LENGTH_UNIT_MAP.get(unit_raw.replace(".", "").strip())

        if val is not None and unit_canon:
            mask.add(start, end)
            facts.append(
                FactSpan(
                    fact_type=FactType.AREA_LENGTH,
                    raw_text=text[start:end],
                    normalized_value=val,
                    unit=unit_canon,
                    start_char=start,
                    end_char=end
                )
            )

    # 2. Number words followed by area/length unit
    p_unit_marker = re.compile(rf'{B_START}({area_keywords_regex}){B_END}', re.IGNORECASE)
    for m in p_unit_marker.finditer(text):
        u_start = m.start(1)
        u_end = m.end(1)
        if mask.overlaps(u_start, u_end):
            continue

        unit_raw = m.group(1).lower().strip()
        unit_canon = AREA_LENGTH_UNIT_MAP.get(unit_raw)
        if not unit_canon:
            unit_canon = AREA_LENGTH_UNIT_MAP.get(unit_raw.replace(".", "").strip())
        if not unit_canon:
            continue

        is_hindi = any('\u0900' <= ch <= '\u097F' for ch in unit_raw)

        val, span, raw_phrase = collect_preceding_number_words(text, u_start, is_hindi=is_hindi)
        if val is not None and span is not None:
            full_start = span[0]
            full_end = u_end
            if not mask.overlaps(full_start, full_end):
                mask.add(full_start, full_end)
                facts.append(
                    FactSpan(
                        fact_type=FactType.AREA_LENGTH,
                        raw_text=text[full_start:full_end],
                        normalized_value=val,
                        unit=unit_canon,
                        start_char=full_start,
                        end_char=full_end
                    )
                )

    return facts


def extract_multipliers(text: str, mask: IntervalMask) -> List[FactSpan]:
    """Extracts multiplier expressions (e.g. 'ten times', 'दस गुना', 'twice', 'दुगुना')."""
    facts = []

    # 1. Fixed multiplier words (twice, दुगुना, etc.)
    for kw, mult_val in MULTIPLIER_WORDS.items():
        pattern = rf'{B_START}{re.escape(kw)}{B_END}'
        for m in re.finditer(pattern, text, re.IGNORECASE):
            # Locate exact keyword inside match
            sub_start = m.group(0).find(kw)
            start = m.start() + (sub_start if sub_start >= 0 else 0)
            end = start + len(kw)
            if mask.overlaps(start, end):
                continue
            mask.add(start, end)
            facts.append(
                FactSpan(
                    fact_type=FactType.MULTIPLIER,
                    raw_text=text[start:end],
                    normalized_value=mult_val,
                    unit="multiplier",
                    start_char=start,
                    end_char=end
                )
            )

    # 2. Digits followed by times / गुना (e.g. '10 times', '१० गुना')
    p_num_mult = re.compile(rf'{B_START}([०-९\d,]+(?:\.[०-९\d]+)?)\s*(times|fold|गुना|गुणा){B_END}', re.IGNORECASE)
    for m in p_num_mult.finditer(text):
        start = m.start(1)
        end = m.end(2)
        if mask.overlaps(start, end):
            continue
        val = parse_number_token(m.group(1))
        if val is not None:
            mask.add(start, end)
            facts.append(
                FactSpan(
                    fact_type=FactType.MULTIPLIER,
                    raw_text=text[start:end],
                    normalized_value=val,
                    unit="multiplier",
                    start_char=start,
                    end_char=end
                )
            )

    # 3. Number words followed by times / गुना (e.g. 'seven times', 'सात गुना', 'दस गुना')
    p_mult_marker = re.compile(rf'{B_START}(times|fold|गुना|गुणा){B_END}', re.IGNORECASE)
    for m in p_mult_marker.finditer(text):
        u_start = m.start(1)
        u_end = m.end(1)
        if mask.overlaps(u_start, u_end):
            continue

        marker_str = m.group(1).lower()
        is_hindi = marker_str in ("गुना", "गुणा")

        val, span, raw_phrase = collect_preceding_number_words(text, u_start, is_hindi=is_hindi)
        if val is not None and span is not None:
            full_start = span[0]
            full_end = u_end
            if not mask.overlaps(full_start, full_end):
                mask.add(full_start, full_end)
                facts.append(
                    FactSpan(
                        fact_type=FactType.MULTIPLIER,
                        raw_text=text[full_start:full_end],
                        normalized_value=val,
                        unit="multiplier",
                        start_char=full_start,
                        end_char=full_end
                    )
                )

    return facts


def extract_section_references(text: str, mask: IntervalMask) -> List[FactSpan]:
    """Extracts internal statutory cross-references (e.g. 'section 12', 'sections 18, 19 and 20', 'उपधारा (2)', 'खंड (ख)')."""
    facts = []

    # Section / धारा / िारा (corrupted font variant) - supports single sections and comma/and-separated lists
    p_sec_list = re.compile(
        rf'{B_START}(sections?|sec\.|धारा|िारा)\s*([०-९\d]+[A-Za-zक-ह]?(?:\s*,\s*[०-९\d]+[A-Za-zक-ह]?)*(?:\s*(?:and|or|तथा|या|से)\s*[०-९\d]+[A-Za-zक-ह]?)?){B_END}',
        re.IGNORECASE
    )
    for m in p_sec_list.finditer(text):
        full_start = m.start(1)
        full_end = m.end(2)
        if mask.overlaps(full_start, full_end):
            continue
        target_group = m.group(2)
        num_matches = list(re.finditer(r'[०-९\d]+[A-Za-zक-ह]?', target_group))
        mask.add(full_start, full_end)
        if len(num_matches) <= 1:
            raw_target = m.group(2)
            norm_id = normalize_section_number(raw_target)
            facts.append(
                FactSpan(
                    fact_type=FactType.SECTION_REF,
                    raw_text=text[full_start:full_end],
                    normalized_value={"target_type": "section", "target_id": norm_id},
                    unit="section_ref",
                    start_char=full_start,
                    end_char=full_end
                )
            )
        else:
            for nm in num_matches:
                t_str = nm.group(0)
                norm_id = normalize_section_number(t_str)
                t_start = m.start(2) + nm.start()
                t_end = m.start(2) + nm.end()
                facts.append(
                    FactSpan(
                        fact_type=FactType.SECTION_REF,
                        raw_text=t_str,
                        normalized_value={"target_type": "section", "target_id": norm_id},
                        unit="section_ref",
                        start_char=t_start,
                        end_char=t_end
                    )
                )

    # Sub-section / उपधारा / उप[ध|ि]ारा with optional parentheses
    p_subsec = re.compile(rf'{B_START}(sub-sections?|subsection|उपधारा|उप-धारा|उप[ध|ि]ारा)\s*\(?([०-९\d]+)\)?{B_END}', re.IGNORECASE)
    for m in p_subsec.finditer(text):
        start = m.start(1)
        end = m.end(2)
        if end < len(text) and text[end] == ')':
            end += 1
        if mask.overlaps(start, end):
            continue
        raw_target = m.group(2)
        norm_id = devanagari_digits_to_arabic(raw_target)
        mask.add(start, end)
        facts.append(
            FactSpan(
                fact_type=FactType.SECTION_REF,
                raw_text=text[start:end],
                normalized_value={"target_type": "sub_section", "target_id": norm_id},
                unit="section_ref",
                start_char=start,
                end_char=end
            )
        )

    # Clause / खंड / खण्ड / ििंड / ििंढ
    p_clause = re.compile(rf'{B_START}(clauses?|खंड|खण्ड|ििंड|ििंढ|खण्\s*ड)\s*\(?([a-zA-Z]|[\u0900-\u097F]+)\)?{B_END}', re.IGNORECASE)
    for m in p_clause.finditer(text):
        start = m.start(1)
        end = m.end(2)
        if end < len(text) and text[end] == ')':
            end += 1
        if mask.overlaps(start, end):
            continue
        raw_target = m.group(2)
        norm_letter = normalize_clause_letter(raw_target)
        if norm_letter == 'ि':
            # Gazette OCR corrupted font variant where 'ख' was decoded as 'ि'
            norm_letter = 'b'
        mask.add(start, end)
        facts.append(
            FactSpan(
                fact_type=FactType.SECTION_REF,
                raw_text=text[start:end],
                normalized_value={"target_type": "clause", "target_id": norm_letter},
                unit="section_ref",
                start_char=start,
                end_char=end
            )
        )

    return facts


# Idiomatic Hindi non-numeric words following 'एक'
HI_IDIOM_AFTER_EK = {'साथ', 'दूसरे', 'दूसरा', 'समान', 'जैसा', 'जैसी', 'जैसे', 'समय', 'मात्र', 'ओर', 'तरफ', 'बार', 'रूप'}


def extract_standalone_numbers(text: str, mask: IntervalMask, enum_prefix_end: int) -> List[FactSpan]:
    """
    Extracts standalone numbers and number words that are not part of other structured facts.
    Ignores any tokens within the leading enumeration prefix and filters Hindi idiomatic 'एक'.
    """
    facts = []

    # 1. Compound English numbers: twenty-one, thirty-five, etc.
    p_compound = re.compile(
        rf'{B_START}(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)-(one|two|three|four|five|six|seven|eight|nine){B_END}',
        re.IGNORECASE
    )
    for m in p_compound.finditer(text):
        start = m.start(1)
        end = m.end(2)
        if end <= enum_prefix_end or mask.overlaps(start, end):
            continue
        tens = EN_UNITS[m.group(1).lower()]
        units = EN_UNITS[m.group(2).lower()]
        val = float(tens + units)
        mask.add(start, end)
        facts.append(
            FactSpan(
                fact_type=FactType.NUMBER,
                raw_text=text[start:end],
                normalized_value=val,
                unit=None,
                start_char=start,
                end_char=end
            )
        )

    # 2. Standalone digits (Arabic and Devanagari)
    p_digits = re.compile(rf'{B_START}([०-९\d,]+(?:\.[०-९\d]+)?){B_END}')
    for m in p_digits.finditer(text):
        start = m.start(1)
        end = m.end(1)
        # Must not be within the leading clause label prefix
        if end <= enum_prefix_end or mask.overlaps(start, end):
            continue

        raw = m.group(1)
        val = parse_number_token(raw)
        if val is not None:
            mask.add(start, end)
            facts.append(
                FactSpan(
                    fact_type=FactType.NUMBER,
                    raw_text=text[start:end],
                    normalized_value=val,
                    unit=None,
                    start_char=start,
                    end_char=end
                )
            )

    # 3. Standalone English number words (skip 'one' to prevent article/pronoun false positives)
    for w, num_val in {**EN_UNITS, **EN_ORDINALS}.items():
        if w.lower() == "one":
            continue
        pattern = rf'{B_START}({re.escape(w)}){B_END}'
        for m in re.finditer(pattern, text, re.IGNORECASE):
            start = m.start(1)
            end = m.end(1)
            if end <= enum_prefix_end or mask.overlaps(start, end):
                continue
            mask.add(start, end)
            facts.append(
                FactSpan(
                    fact_type=FactType.NUMBER,
                    raw_text=text[start:end],
                    normalized_value=float(num_val),
                    unit=None,
                    start_char=start,
                    end_char=end
                )
            )

    # 4. Standalone Hindi number words (skip 'एक' which functions as indefinite article 'a'/'an')
    for w, num_val in {**HI_NUMBERS, **HI_ORDINALS}.items():
        if w == "एक":
            continue
        pattern = rf'{B_START}({re.escape(w)}){B_END}'
        for m in re.finditer(pattern, text):
            start = m.start(1)
            end = m.end(1)
            if end <= enum_prefix_end or mask.overlaps(start, end):
                continue
            mask.add(start, end)
            facts.append(
                FactSpan(
                    fact_type=FactType.NUMBER,
                    raw_text=text[start:end],
                    normalized_value=float(num_val),
                    unit=None,
                    start_char=start,
                    end_char=end
                )
            )

    return facts


def extract_facts(text: str) -> List[FactSpan]:
    """
    Complete fact extraction pipeline for a single clause text string.
    Identifies enumeration prefix, extracts structured entities with non-overlapping spans,
    and returns sorted list of canonical FactSpan objects.
    """
    if not text or not text.strip():
        return []

    mask = IntervalMask()
    enum_end = get_enumeration_prefix_length(text)

    # Mask structural labels: e.g. "CHAPTER IV", "अध्याय 4", "PART II", "भाग 2", "SCHEDULE I", "अनुसूची 1"
    p_structural = re.compile(
        rf'{B_START}(?:chapters?|parts?|schedules?|अध्याय|भाग|अनुसूची)\s+([IVXLCDM\d०-९]+){B_END}',
        re.IGNORECASE
    )
    for m in p_structural.finditer(text):
        mask.add(m.start(), m.end())

    all_facts: List[FactSpan] = []

    # Priority 1: Dates
    all_facts.extend(extract_dates(text, mask))

    # Priority 2: Money
    all_facts.extend(extract_money(text, mask))

    # Priority 3: Percentage
    all_facts.extend(extract_percentages(text, mask))

    # Priority 4: Duration
    all_facts.extend(extract_durations(text, mask))

    # Priority 5: Area / Length
    all_facts.extend(extract_area_length(text, mask))

    # Priority 6: Multipliers
    all_facts.extend(extract_multipliers(text, mask))

    # Priority 7: Section References
    all_facts.extend(extract_section_references(text, mask))

    # Priority 8: Standalone Numbers (excluding enumeration prefix)
    all_facts.extend(extract_standalone_numbers(text, mask, enum_end))

    # Sort facts by character position
    all_facts.sort(key=lambda f: f.start_char)
    return all_facts
