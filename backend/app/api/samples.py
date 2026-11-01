"""
samples.py - Catalog of bundled bilingual statutory samples.
"""

from typing import List, Optional
from backend.app.api.models import SampleItem


BUNDLED_SAMPLES: List[SampleItem] = [
    SampleItem(
        id="domestic_violence_2005",
        slug="domestic_violence_2005",
        title="The Protection of Women from Domestic Violence Act, 2005",
        category="Short Act",
        pages_en=15,
        pages_hi=12,
        description="Pivotal welfare legislation providing civil remedies and protection orders for women against domestic abuse.",
        has_reported_issues=True,
        highlighted_issues=[
            "Section 3 clause ordering variation (economic abuse Roman numerals vs. Devanagari letters)",
            "Mandatory obligation phrasing ('shall forward copy' vs. discretionary Hindi translations)",
            "Gazette OCR consonant ligatures and numerical cross-references"
        ]
    ),
    SampleItem(
        id="right_to_information_2005",
        slug="right_to_information_2005",
        title="The Right to Information Act, 2005",
        category="Medium Act",
        pages_en=25,
        pages_hi=20,
        description="Foundational transparency statute mandating proactive disclosure and citizen access to public records.",
        has_reported_issues=True,
        highlighted_issues=[
            "Section 2 definitions merged clause typography (clause 2.i printed continuously with 2.i.i in Hindi)",
            "Strict 30-day statutory timeline facts and penalty currency normalizations",
            "Appellate authority and Central Information Commission jurisdiction bounds"
        ]
    ),
    SampleItem(
        id="environment_protection_1986",
        slug="environment_protection_1986",
        title="The Environment (Protection) Act, 1986",
        category="Short Act",
        pages_en=13,
        pages_hi=7,
        description="Comprehensive central framework for environmental safety, hazardous substance regulation, and industrial standards.",
        has_reported_issues=True,
        highlighted_issues=[
            "Jan Vishwas Act 2023 amendment statutory asymmetry (Sections 14A, 14B, 15A, 15B added in English, omitted in pre-amendment Hindi)",
            "Section 17 statutory omission",
            "Stringent pollutant discharge numerical thresholds and laboratory evidence procedures"
        ]
    ),
    SampleItem(
        id="right_to_education_2009",
        slug="right_to_education_2009",
        title="The Right of Children to Free and Compulsory Education Act, 2009",
        category="Short Act",
        pages_en=20,
        pages_hi=15,
        description="Statute guaranteeing free and compulsory elementary education to every child between ages 6 and 14.",
        has_reported_issues=False,
        highlighted_issues=[
            "25% private school reservation quota factual verification",
            "School Management Committee composition ratios and teacher-pupil norms"
        ]
    ),
    SampleItem(
        id="national_green_tribunal_2010",
        slug="national_green_tribunal_2010",
        title="The National Green Tribunal Act, 2010",
        category="Medium Act",
        pages_en=23,
        pages_hi=19,
        description="Specialized judicial tribunal statute for effective and expeditious disposal of environmental disputes.",
        has_reported_issues=False,
        highlighted_issues=[
            "Limitation period duration facts (6 months, 30 days condonation)",
            "Tribunal Chairperson and judicial member qualifications"
        ]
    )
]


def get_sample_by_id(sample_id: str) -> Optional[SampleItem]:
    for s in BUNDLED_SAMPLES:
        if s.id == sample_id or s.slug == sample_id:
            return s
    return None

