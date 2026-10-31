"""
number_words.py - Bimodal (English & Hindi) Number Word Parser and Normalizer.
Translates written number phrases, scales (lakh, crore), fractions, ordinals,
and digits (Arabic & Devanagari) into exact canonical numbers.
"""

import re
from typing import Optional, Tuple, List

# Devanagari digits to Arabic
DEV_DIGIT_MAP = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

def devanagari_digits_to_arabic(text: str) -> str:
    """Replaces Devanagari numerals with Arabic numerals."""
    res = []
    for ch in text:
        res.append(DEV_DIGIT_MAP.get(ch, ch))
    return "".join(res)


# English base number words
EN_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
}

EN_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
    "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
    "thirtieth": 30, "fortieth": 40, "fiftieth": 50
}

EN_SCALES = {
    "hundred": 100,
    "thousand": 1000,
    "lakh": 100000,
    "lakhs": 100000,
    "lac": 100000,
    "lacs": 100000,
    "crore": 10000000,
    "crores": 10000000,
    "million": 1000000,
    "millions": 1000000,
    "billion": 1000000000
}


# Hindi 1-100 base numbers
HI_NUMBERS = {
    "शून्य": 0, "सिफर": 0,
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छ:": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14, "पंद्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18, "अठारि": 18, "उन्नीस": 19, "बीस": 20,
    "इक्कीस": 21, "बाईस": 22, "तेईस": 23, "चौबीस": 24, "पच्चीस": 25, "छब्बीस": 26, "सत्ताईस": 27, "अट्ठाईस": 28, "उनतीस": 29, "तीस": 30,
    "इकतीस": 31, "बत्तीस": 32, "तैंतीस": 33, "चौंतीस": 34, "पैंतीस": 35, "छत्तीस": 36, "सैंतीस": 37, "अड़तीस": 38, "उनतालीस": 39, "चालीस": 40,
    "इकतालीस": 41, "बयालीस": 42, "तैंतालीस": 43, "चवालीस": 44, "पैंतालीस": 45, "छियालीस": 46, "सैंतालीस": 47, "अड़तालीस": 48, "उनचास": 49, "पचास": 50,
    "इक्यावन": 51, "इक्याउन": 51, "बावन": 52, "तिरपन": 53, "तिरेपन": 53, "चौवन": 54, "पचपन": 55, "छप्पन": 56, "सत्तावन": 57, "अट्ठावन": 58, "उनसठ": 59, "साठ": 60,
    "इकसठ": 61, "बासठ": 62, "तिरसठ": 63, "चौंसठ": 64, "पैंसठ": 65, "छियासठ": 66, "सरसठ": 67, "अड़सठ": 68, "उनहत्तर": 69, "सत्तर": 70,
    "इकहत्तर": 71, "बहत्तर": 72, "तिहत्तर": 73, "चौहत्तर": 74, "पचहत्तर": 75, "छिहत्तर": 76, "सतहत्तर": 77, "अठहत्तर": 78, "उन्यासी": 79, "उनासी": 79, "अस्सी": 80,
    "इक्यासी": 81, "बयासी": 82, "तिरासी": 83, "चौरासी": 84, "पचासी": 85, "छियासी": 86, "सत्तासी": 87, "अट्ठासी": 88, "नवासी": 89, "नब्बे": 90,
    "इक्यानवे": 91, "बानवे": 92, "बायनवे": 92, "तिरानवे": 93, "चौरानवे": 94, "पचानवे": 95, "छियानवे": 96, "संतानवे": 97, "अट्ठानवे": 98, "निन्यानवे": 99, "सौ": 100
}

HI_ORDINALS = {
    "पहला": 1, "प्रथम": 1, "पहली": 1, "पहले": 1,
    "दूसरा": 2, "द्वितीय": 2, "दूसरी": 2, "दूसरे": 2,
    "तीसरा": 3, "तृतीय": 3, "तीसरी": 3, "तीसरे": 3,
    "चौथा": 4, "चतुर्थ": 4, "चौथी": 4, "चौथे": 4,
    "पांचवां": 5, "पाँचवाँ": 5, "पंचम": 5, "पांचवीं": 5, "पांचवें": 5,
    "छठा": 6, "षष्ठ": 6, "छठी": 6, "छठे": 6,
    "सातवां": 7, "सप्तम": 7, "सातवीं": 7, "सातवें": 7,
    "आठवां": 8, "अष्टम": 8, "आठवीं": 8, "आठवें": 8,
    "नौवां": 9, "नवम": 9, "नौवीं": 9, "नौवें": 9,
    "दसवां": 10, "दशम": 10, "दसवीं": 10, "दसवें": 10
}

HI_SCALES = {
    "सौ": 100,
    "हजार": 1000,
    "हज़ार": 1000,
    "लाख": 100000,
    "करोड़": 10000000,
    "करोड": 10000000,
    "अरब": 1000000000
}

HI_FRACTIONS = {
    "आधा": 0.5,
    "पाव": 0.25,
    "चौथाई": 0.25,
    "एक चौथाई": 0.25,
    "तिहाई": 1.0 / 3.0,
    "एक तिहाई": 1.0 / 3.0,
    "दो तिहाई": 2.0 / 3.0,
    "तीन चौथाई": 0.75,
    "डेढ़": 1.5,
    "ढाई": 2.5
}


def parse_number_token(tok: str) -> Optional[float]:
    """
    Parses a single number token, which may be digits (Arabic or Devanagari),
    comma-separated (1,00,000), decimal (0.3 or ०.३), or negative.
    """
    clean = devanagari_digits_to_arabic(tok.strip())
    # Remove commas in numbers (e.g. 50,000 or 1,00,000)
    clean_num = clean.replace(",", "")
    try:
        return float(clean_num)
    except ValueError:
        return None


def parse_english_number_words(words: List[str]) -> Optional[float]:
    """
    Parses a sequence of English number words (e.g. 'twenty five thousand', 'one lakh fifty thousand').
    """
    if not words:
        return None

    # Check for single ordinal
    if len(words) == 1 and words[0].lower() in EN_ORDINALS:
        return float(EN_ORDINALS[words[0].lower()])

    total = 0.0
    current = 0.0
    found_any = False

    for w in words:
        w_lower = w.lower().strip("-")
        if w_lower in EN_UNITS:
            current += EN_UNITS[w_lower]
            found_any = True
        elif w_lower in EN_SCALES:
            scale = EN_SCALES[w_lower]
            found_any = True
            if current == 0.0:
                current = 1.0
            if scale >= 1000:
                total += current * scale
                current = 0.0
            else:
                current *= scale
        elif w_lower == "and":
            continue
        else:
            num = parse_number_token(w_lower)
            if num is not None:
                current += num
                found_any = True
            else:
                return None

    if not found_any:
        return None

    return total + current


def parse_hindi_number_words(words: List[str]) -> Optional[float]:
    """
    Parses a sequence of Hindi number words (e.g. 'पचास हजार', 'एक लाख पचास हजार', 'डेढ़ लाख').
    """
    if not words:
        return None

    joined = " ".join(words).strip()
    if joined in HI_FRACTIONS:
        return float(HI_FRACTIONS[joined])

    if len(words) == 1 and words[0] in HI_ORDINALS:
        return float(HI_ORDINALS[words[0]])

    total = 0.0
    current = 0.0
    found_any = False

    for w in words:
        w_clean = w.strip()
        if w_clean in HI_FRACTIONS:
            current += HI_FRACTIONS[w_clean]
            found_any = True
        elif w_clean in HI_NUMBERS:
            current += HI_NUMBERS[w_clean]
            found_any = True
        elif w_clean in HI_SCALES:
            scale = HI_SCALES[w_clean]
            found_any = True
            if current == 0.0:
                current = 1.0
            if scale >= 1000:
                total += current * scale
                current = 0.0
            else:
                current *= scale
        else:
            num = parse_number_token(w_clean)
            if num is not None:
                current += num
                found_any = True
            else:
                return None

    if not found_any:
        return None

    return total + current
