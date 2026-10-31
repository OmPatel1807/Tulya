"""
numbering.py - Normalization and mapping for Hindi & English legal numbering schemes.
Maps Devanagari numerals, lettered clauses, roman numerals, and special markers
to stable canonical identifiers.
"""

import re
from typing import Optional, Tuple

DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

HINDI_CONSONANT_MAP = {
    'क': 'a', 'ख': 'b', 'ग': 'c', 'घ': 'd', 'ङ': 'e',
    'च': 'f', 'छ': 'g', 'ज': 'h', 'झ': 'i', 'ञ': 'j',
    'ट': 'k', 'ठ': 'l', 'ड': 'm', 'ढ': 'n', 'ण': 'o',
    'त': 'p', 'थ': 'q', 'द': 'r', 'ध': 's', 'न': 't',
    'प': 'u', 'फ': 'v', 'ब': 'w', 'भ': 'x', 'म': 'y',
    'य': 'z'
}

# Lettered section suffixes: e.g. 12A / 12क
HINDI_SUFFIX_MAP = {
    'क': 'A', 'ख': 'B', 'ग': 'C', 'घ': 'D',
    'ङ': 'E', 'च': 'F', 'छ': 'G', 'ज': 'H'
}

ROMAN_NUMERALS = {
    'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5,
    'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10,
    'xi': 11, 'xii': 12, 'xiii': 13, 'xiv': 14, 'xv': 15,
    'xvi': 16, 'xvii': 17, 'xviii': 18, 'xix': 19, 'xx': 20
}


def devanagari_to_arabic(text: str) -> str:
    """Replaces all Devanagari digits with Arabic digits."""
    for dev, ara in DEVANAGARI_DIGITS.items():
        text = text.replace(dev, ara)
    return text


def normalize_section_number(sec_token: str) -> str:
    """
    Normalizes section tokens like '12', '12A', '१२', '१२क' to '12', '12A'.
    """
    s = devanagari_to_arabic(sec_token.strip())
    # Check for Hindi suffix letter: e.g. '12क'
    match = re.match(r'^(\d+)([\u0900-\u097Fa-zA-Z]?)$', s)
    if match:
        num = match.group(1)
        suffix = match.group(2)
        if suffix in HINDI_SUFFIX_MAP:
            return f"{num}{HINDI_SUFFIX_MAP[suffix]}"
        elif suffix:
            return f"{num}{suffix.upper()}"
        return num
    return s


def normalize_clause_letter(letter_token: str) -> str:
    """
    Normalizes clause letter tokens like 'a', 'b', 'क', 'ख' to canonical lowercase Latin 'a', 'b'.
    """
    tok = letter_token.strip().lower()
    if tok in HINDI_CONSONANT_MAP:
        return HINDI_CONSONANT_MAP[tok]
    return tok


def is_roman_numeral(token: str) -> bool:
    """Checks if a string is a standard roman numeral (i - xx)."""
    return token.strip().lower() in ROMAN_NUMERALS


def roman_to_int(token: str) -> int:
    """Converts a roman numeral (i - xx) to integer."""
    return ROMAN_NUMERALS.get(token.strip().lower(), 0)
