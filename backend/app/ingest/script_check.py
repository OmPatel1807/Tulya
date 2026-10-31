"""
script_check.py - Analyzes text scripts, checks Devanagari Unicode validity,
and detects non-Unicode legacy Hindi font corruption (e.g. KrutiDev, ShreeLipi).
"""

import re
from typing import Dict, Any, Tuple

# Unicode Devanagari range: U+0900 to U+097F
DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')
LATIN_RE = re.compile(r'[a-zA-Z]')

# Typical high-ASCII or odd character patterns found in legacy 8-bit Devanagari font encodings
LEGACY_FONT_CHARS = re.compile(r'[¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]')
# Common KrutiDev / legacy word patterns (e.g. 'Hkkjr', 'ljdkj', 'fof/k', 'vkSj', 'U;k;', 'dks', 'esa', 'gS', 'Fkk')
LEGACY_WORD_PATTERNS = re.compile(r'\b(Hkkjr|ljdkj|fof/k|vkSj|U;k;|dks|esa|gS|Fkk|dk|dh|ds|gSa|rkfd|okys|funsZf'
                                  r'k|BÉEÉ|ºÉÆÉÊ´ÉvÉÉxÉ|fo/kk;h|jktHkk"kk)\b')

COMMON_ENGLISH_WORDS = {
    "the", "and", "or", "of", "to", "in", "for", "with", "on", "at", "by", "from",
    "act", "section", "shall", "be", "is", "are", "government", "state", "court",
    "order", "public", "person", "authority", "rules", "regulations", "provisions"
}


class LegacyFontError(Exception):
    """Raised when text appears to be encoded in a non-Unicode legacy font."""
    pass


def devanagari_fraction(text: str) -> float:
    """
    Computes the fraction of Devanagari characters relative to total alphabetic characters.
    Returns 0.0 if there are no alphabetic characters.
    """
    if not text:
        return 0.0
    dev_count = len(DEVANAGARI_RE.findall(text))
    lat_count = len(LATIN_RE.findall(text))
    total = dev_count + lat_count
    if total == 0:
        return 0.0
    return dev_count / total


def check_script(text: str, expected_lang: str = "hi", strict: bool = False) -> Dict[str, Any]:
    """
    Assesses a text sample.
    Verdicts:
      - OK_UNICODE_HINDI: Devanagari fraction > 0.45
      - ENGLISH: Valid English text (Devanagari fraction < 0.10, standard English words present)
      - LEGACY_FONT_SUSPECTED: Non-Unicode font encoding detected (KrutiDev / ShreeLipi)
      - MIXED: Substantial presence of both scripts (0.15 <= fraction <= 0.45)
      - EMPTY: No meaningful text
    """
    stripped = text.strip()
    if not stripped:
        return {
            "verdict": "EMPTY",
            "devanagari_fraction": 0.0,
            "message": "Text sample is empty."
        }

    frac = devanagari_fraction(stripped)
    dev_count = len(DEVANAGARI_RE.findall(stripped))
    lat_count = len(LATIN_RE.findall(stripped))

    # Check for legacy font indicators
    legacy_char_count = len(LEGACY_FONT_CHARS.findall(stripped))
    legacy_word_count = len(LEGACY_WORD_PATTERNS.findall(stripped))

    is_legacy = False
    if legacy_word_count >= 2:
        is_legacy = True
    elif legacy_char_count > 10 and frac < 0.30:
        is_legacy = True
    elif expected_lang == "hi" and frac < 0.20 and lat_count > 30:
        # Check if it's English text or ASCII gibberish
        words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{2,}\b', stripped)]
        en_word_hits = sum(1 for w in words if w in COMMON_ENGLISH_WORDS)
        if len(words) > 0 and (en_word_hits / len(words)) < 0.10:
            is_legacy = True

    if is_legacy:
        verdict = "LEGACY_FONT_SUSPECTED"
        msg = ("Legacy non-Unicode Hindi font detected (e.g. KrutiDev/ShreeLipi). "
               "Please supply a modern Unicode Devanagari (UTF-8) PDF version. OCR is disabled.")
        if strict:
            raise LegacyFontError(msg)
        return {
            "verdict": verdict,
            "devanagari_fraction": round(frac, 4),
            "message": msg
        }

    if frac >= 0.45:
        verdict = "OK_UNICODE_HINDI"
        msg = "Unicode Devanagari text verified."
    elif frac < 0.10:
        verdict = "ENGLISH"
        msg = "English text detected."
    else:
        verdict = "MIXED"
        msg = "Mixed English and Devanagari text detected."

    return {
        "verdict": verdict,
        "devanagari_fraction": round(frac, 4),
        "message": msg
    }
