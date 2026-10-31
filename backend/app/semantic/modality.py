"""
modality.py - Modality Lexicon and Pre-screening for Legal Deontic Shifts.

Identifies potential divergence in statutory obligation vs discretion:
- Mandatory: shall, must, shall not / करेगा, होगी, बाध्य होगा, नहीं करेगा
- Discretionary: may, entitled to, at its discretion / कर सकेगा, हो सकेगी, अधिकारी होगा
"""

import re
from typing import Dict, List, Any, Optional

EN_MANDATORY_REGEX = re.compile(
    r'\b(?:shall\s+not|must\s+not|is\s+required\s+to|bound\s+to|shall|must)\b',
    re.IGNORECASE
)
EN_PERMISSIVE_REGEX = re.compile(
    r'\b(?:may\s+not|may\s+be|entitled\s+to|at\s+its\s+discretion|may)\b',
    re.IGNORECASE
)

HI_MANDATORY_REGEX = re.compile(
    r'(?:नहीं\s+करेगा|नहीं\s+होगी|बाध्य\s+होगा|अपेक्षित\s+होगा|करेगा|करेगी|करेंगे|होगी|होगा)',
    re.UNICODE
)
HI_PERMISSIVE_REGEX = re.compile(
    r'(?:कर\s+सकेगा|कर\s+सकेगी|कर\s+सकेंगे|हो\s+सकेगा|हो\s+सकेगी|अधिकारी\s+होगा|अनुज्ञात\s+होगा)',
    re.UNICODE
)


def detect_modality_hints(en_text: str, hi_text: str) -> Optional[Dict[str, Any]]:
    """
    Scans English and Hindi clauses for potential deontic modality conflicts.
    Returns hint dict if a candidate shift is detected, or None.
    """
    en_has_shall = bool(EN_MANDATORY_REGEX.search(en_text))
    en_has_may = bool(EN_PERMISSIVE_REGEX.search(en_text))

    hi_has_mandatory = bool(HI_MANDATORY_REGEX.search(hi_text))
    hi_has_permissive = bool(HI_PERMISSIVE_REGEX.search(hi_text))

    # Shift 1: English mandatory ("shall"), but Hindi permissive ("कर सकेगा")
    if en_has_shall and not en_has_may and hi_has_permissive:
        return {
            "candidate": True,
            "type": "MANDATORY_TO_PERMISSIVE",
            "en_indicator": "shall / mandatory",
            "hi_indicator": "कर सकेगा / permissive",
            "note": "English appears mandatory ('shall') while Hindi appears permissive ('कर सकेगा')"
        }

    # Shift 2: English permissive ("may"), but Hindi mandatory ("करेगा")
    if en_has_may and not en_has_shall and hi_has_mandatory and not hi_has_permissive:
        return {
            "candidate": True,
            "type": "PERMISSIVE_TO_MANDATORY",
            "en_indicator": "may / permissive",
            "hi_indicator": "करेगा / mandatory",
            "note": "English appears permissive ('may') while Hindi appears mandatory ('करेगा')"
        }

    return None
