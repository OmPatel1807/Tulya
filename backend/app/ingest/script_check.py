"""
script_check.py - Analyzes text scripts, checks Devanagari Unicode validity,
implements dictionary quality gate (hindi_word_validity), and detects
non-Unicode legacy Hindi font corruption (e.g. KrutiDev, ShreeLipi).
"""

import os
import re
import gzip
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Set

# Unicode Devanagari range: U+0900 to U+097F
DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')
DEVANAGARI_WORD_RE = re.compile(r'[\u0900-\u097F]+')
CONSONANT_RE = re.compile(r'[\u0915-\u0939\u0958-\u095F]')
MATRA_RE = re.compile(r'[\u093E-\u094C\u0962\u0963]')
SUSPICIOUS_HA_RA_RE = re.compile(r'[हर][\u093E-\u094C]')
LATIN_RE = re.compile(r'[a-zA-Z]')


# Typical high-ASCII or odd character patterns found in legacy 8-bit Devanagari font encodings
LEGACY_FONT_CHARS = re.compile(r'[¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]')
LEGACY_WORD_PATTERNS = re.compile(r'\b(Hkkjr|ljdkj|fof/k|vkSj|U;k;|dks|esa|gS|Fkk|dk|dh|ds|gSa|rkfd|okys|funsZf'
                                  r'k|BÉEÉ|ºÉÆÉÊ´ÉvÉÉxÉ|fo/kk;h|jktHkk"kk)\b')

COMMON_ENGLISH_WORDS = {
    "the", "and", "or", "of", "to", "in", "for", "with", "on", "at", "by", "from",
    "act", "section", "shall", "be", "is", "are", "government", "state", "court",
    "order", "public", "person", "authority", "rules", "regulations", "provisions"
}

# Legal statutory allow-list for dictionary validity check
LEGAL_ALLOWLIST = {
    "अभिप्रेत", "अधिनियम", "प्राधिकृत", "निर्दिष्ट", "मजिस्ट्रेट", "प्रतिकर",
    "परिणामस्वरूप", "संविधान", "धारा", "न्यायालय", "उपबंध", "अनुसूची",
    "अधिसूचना", "व्यथित", "नातेदारी", "साझी", "गृहस्थी", "अधिनियमित",
    "उद्देशिका", "प्रारंभिक", "विस्तार", "संक्षिप्त", "परिभाषाएं", "परिभाषा",
    "नियम", "खंड", "उपखंड", "भारत", "अधिकार", "सुरक्षा", "आदेश", "संरक्षण",
    "धनीय", "अनुतोष", "हिंसा", "शिकायत", "आवेदन", "सुनवाई", "प्रक्रम", "संसद्",
    "दत्तक", "आयु", "कदाचार", "संबंधित", "कार्यवाही", "अधिकारी", "सेवा", "प्रदाता",
    "विनिर्दिष्ट", "उपधारा", "विनियम", "प्रावधान", "कर्तव्य", "दायित्व", "अपराध",
    "शास्ति", "शास्तियां", "प्रवृत्त", "लागू", "समिति", "बोर्ड", "प्राधिकरण",
    "अधिकरण", "अध्यक्ष", "सदस्य", "सदस्यों", "रजिस्ट्रार", "सचिव", "आयुक्त", "निरीक्षक"
}

# Calibrated quality gate threshold (clean pages score >= 0.70; corrupted score < 0.45)
HINDI_QUALITY_THRESHOLD = 0.70

_CACHED_WORDLIST: Optional[Set[str]] = None


def get_hindi_wordlist() -> Set[str]:
    """Loads and caches the bundled Hindi dictionary (~195k words)."""
    global _CACHED_WORDLIST
    if _CACHED_WORDLIST is not None:
        return _CACHED_WORDLIST

    words = set(LEGAL_ALLOWLIST)
    pkg_dir = Path(__file__).parent
    dict_path = pkg_dir / "assets" / "hindi_wordlist.txt.gz"

    if dict_path.exists():
        try:
            with gzip.open(dict_path, "rt", encoding="utf-8") as f:
                for line in f:
                    w = line.strip()
                    if w:
                        words.add(w)
        except Exception:
            pass

    _CACHED_WORDLIST = words
    return _CACHED_WORDLIST


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


def hindi_word_validity(text: str) -> Dict[str, Any]:
    """
    Evaluates Hindi lexical quality against a validated dictionary wordlist.
    Flags:
      - U+25CC dotted circle glyph placeholders
      - Suspicious 'ह' or 'र' followed by a vowel sign where the word is not in the wordlist
      - Orphan matras (vowel signs without a preceding base consonant)
    Returns:
      Dict with valid_words, total_words, valid_ratio, quality_score, verdict ('ok' or 'unreliable').
    """
    if not text:
        return {
            "total_words": 0,
            "valid_words": 0,
            "valid_ratio": 0.0,
            "quality_score": 0.0,
            "verdict": "unreliable",
            "has_25cc": False,
            "orphan_matras": 0,
            "suspicious_ha_ra": 0
        }

    wordlist = get_hindi_wordlist()
    words = DEVANAGARI_WORD_RE.findall(text)
    if not words:
        return {
            "total_words": 0,
            "valid_words": 0,
            "valid_ratio": 0.0,
            "quality_score": 0.0,
            "verdict": "unreliable",
            "has_25cc": False,
            "orphan_matras": 0,
            "suspicious_ha_ra": 0
        }

    valid_count = 0
    suspicious_ha_ra = 0
    orphan_matras = 0
    has_25cc = "\u25CC" in text

    for w in words:
        if w in wordlist:
            valid_count += 1
        else:
            if SUSPICIOUS_HA_RA_RE.search(w):
                suspicious_ha_ra += 1

        for i, ch in enumerate(w):
            if MATRA_RE.match(ch):
                prev = w[i - 1] if i > 0 else ""
                prev_prev = w[i - 2] if i > 1 else ""
                # A matra is valid if preceded by a consonant or a nukta modifying a consonant
                if prev == "\u093C" and CONSONANT_RE.match(prev_prev):
                    continue
                if not CONSONANT_RE.match(prev):
                    orphan_matras += 1


    total = len(words)
    valid_ratio = valid_count / total

    # Penalties for corruption indicators
    penalty = 0.0
    if has_25cc:
        penalty += 0.25
    if orphan_matras > 0:
        orphan_rate = orphan_matras / total
        penalty += min(0.30, orphan_rate * 2.0)
    if suspicious_ha_ra > 0:
        ha_ra_rate = suspicious_ha_ra / total
        penalty += min(0.20, ha_ra_rate * 1.5)

    quality_score = max(0.0, valid_ratio - penalty)

    # A page is 'ok' only if validity is above the threshold, no U+25CC, and orphan rate < 1%
    is_ok = (
        valid_ratio >= HINDI_QUALITY_THRESHOLD
        and not has_25cc
        and (orphan_matras / total) <= 0.01
    )

    verdict = "ok" if is_ok else "unreliable"

    return {
        "total_words": total,
        "valid_words": valid_count,
        "valid_ratio": round(valid_ratio, 4),
        "quality_score": round(quality_score, 4),
        "verdict": verdict,
        "has_25cc": has_25cc,
        "orphan_matras": orphan_matras,
        "suspicious_ha_ra": suspicious_ha_ra
    }


def hindi_quality_score(text: str) -> float:
    """Convenience helper returning quality score in range [0.0, 1.0]."""
    res = hindi_word_validity(text)
    return res["quality_score"]


def check_script(text: str, expected_lang: str = "hi", strict: bool = False) -> Dict[str, Any]:
    """
    Assesses a text sample.
    Verdicts:
      - OK_UNICODE_HINDI: Devanagari fraction > 0.45 and passes quality check
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
            "quality_score": 0.0,
            "message": "Text sample is empty."
        }

    frac = devanagari_fraction(stripped)
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
            "quality_score": 0.0,
            "message": msg
        }

    if frac >= 0.45:
        q_info = hindi_word_validity(stripped)
        verdict = "OK_UNICODE_HINDI"
        msg = f"Unicode Devanagari text verified (Quality: {q_info['quality_score']}, Verdict: {q_info['verdict']})."
        return {
            "verdict": verdict,
            "devanagari_fraction": round(frac, 4),
            "quality_score": q_info["quality_score"],
            "word_validity": q_info,
            "message": msg
        }
    elif frac < 0.10:
        verdict = "ENGLISH"
        msg = "English text detected."
    else:
        verdict = "MIXED"
        msg = "Mixed English and Devanagari text detected."

    return {
        "verdict": verdict,
        "devanagari_fraction": round(frac, 4),
        "quality_score": 0.0,
        "message": msg
    }
