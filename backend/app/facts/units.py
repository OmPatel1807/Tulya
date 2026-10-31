"""
units.py - Units, Currencies, Multipliers, and Month Normalizers for Legal Text.
Maps bilingual surface forms into canonical standardized representations.
"""

from typing import Dict, Optional, Tuple

# Duration unit mapping -> canonical name
DURATION_UNIT_MAP: Dict[str, str] = {
    # English
    "day": "day", "days": "day",
    "week": "week", "weeks": "week",
    "month": "month", "months": "month",
    "year": "year", "years": "year", "annum": "year",
    "hour": "hour", "hours": "hour",
    "minute": "minute", "minutes": "minute",
    # Hindi
    "दिन": "day", "दिवस": "day", "रोज़": "day", "रोज": "day", "ददि": "day",
    "सप्ताह": "week", "हफ्ते": "week", "हफ्ता": "week",
    "मास": "month", "माह": "month", "महीने": "month", "महीना": "month",
    "वर्ष": "year", "साल": "year", "िषत": "year",
    "घंटा": "hour", "घंटे": "hour",
    "मिनट": "minute"
}

# Area & Length unit mapping -> canonical name
AREA_LENGTH_UNIT_MAP: Dict[str, str] = {
    # Area
    "acre": "acre", "acres": "acre", "एकड़": "acre",
    "hectare": "hectare", "hectares": "hectare", "हेक्टेयर": "hectare",
    "sq. metre": "sq_m", "sq. metres": "sq_m", "sq metre": "sq_m", "sq metres": "sq_m",
    "square metre": "sq_m", "square metres": "sq_m", "square meter": "sq_m", "square meters": "sq_m",
    "sq m": "sq_m", "sq.m": "sq_m", "sq.m.": "sq_m", "वर्ग मीटर": "sq_m",
    "sq. foot": "sq_ft", "sq. feet": "sq_ft", "square foot": "sq_ft", "square feet": "sq_ft",
    "sq ft": "sq_ft", "sq.ft": "sq_ft", "वर्ग फुट": "sq_ft",
    "sq. yard": "sq_yd", "sq. yards": "sq_yd", "square yard": "sq_yd", "square yards": "sq_yd",
    "वर्ग गज": "sq_yd",
    # Length
    "kilometre": "km", "kilometres": "km", "kilometer": "km", "kilometers": "km", "km": "km", "kms": "km",
    "किलोमीटर": "km", "किमी": "km", "कि.मी.": "km",
    "metre": "m", "metres": "m", "meter": "m", "meters": "m", "m": "m",
    "मीटर": "m",
    "centimetre": "cm", "centimetres": "cm", "centimeter": "cm", "centimeters": "cm", "cm": "cm", "cms": "cm",
    "सेंटीमीटर": "cm", "सेमी": "cm",
    "mile": "mile", "miles": "mile", "मील": "mile"
}

# Currency mappings -> canonical currency code
CURRENCY_MARKERS = {
    "rupee": "INR", "rupees": "INR", "rs": "INR", "rs.": "INR", "inr": "INR", "₹": "INR",
    "रुपये": "INR", "रुपया": "INR", "रु": "INR", "रु.": "INR",
    "paise": "PAISE", "paisa": "PAISE", "पैसे": "PAISE", "पैसा": "PAISE"
}

# Multiplier mapping
MULTIPLIER_WORDS = {
    "twice": 2.0, "दो गुना": 2.0, "दुगुना": 2.0, "दोगुना": 2.0, "दोहरी": 2.0,
    "thrice": 3.0, "तीन गुना": 3.0, "तिगुना": 3.0,
    "fourfold": 4.0, "four times": 4.0, "चार गुना": 4.0,
    "fivefold": 5.0, "five times": 5.0, "पांच गुना": 5.0, "पाँच गुना": 5.0,
    "tenfold": 10.0, "ten times": 10.0, "दस गुना": 10.0
}

# Month names to numbers (1-12)
GREGORIAN_MONTHS = {
    # English
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    # Hindi
    "जनवरी": 1, "फरवरी": 2, "मार्च": 3, "अप्रैल": 4, "मई": 5, "जून": 6,
    "जुलाई": 7, "अगस्त": 8, "सितम्बर": 9, "सितंबर": 9, "अक्टूबर": 10, "अक्तूबर": 10, "नवम्बर": 11, "नवंबर": 11, "दिसम्बर": 12, "दिसंबर": 12
}

SAKA_MONTHS = {
    "चैत्र": 1, "वैशाख": 2, "ज्येष्ठ": 3, "आषाढ़": 4, "श्रावण": 5, "सावन": 5,
    "भाद्रपद": 6, "भादों": 6, "आश्विन": 7, "क्वार": 7, "कार्तिक": 8,
    "मार्गशीर्ष": 9, "अगहन": 9, "पौष": 10, "पूस": 10, "माघ": 11, "फाल्गुन": 12, "फागुन": 12
}
