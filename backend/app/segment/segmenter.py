"""
segmenter.py - Structural Segmentation Engine for Bilingual Legal Acts.

Parses cleaned text streams into hierarchical Clause Trees with stable paths:
  - Top-level sections (e.g. '1', '2', '3')
  - Sub-sections (e.g. '1.1', '1.2')
  - Lettered clauses (e.g. '2.a', '2.b', mapped from '(क)', '(ख)')
  - Sub-clauses (e.g. '2.a.i', '2.a.ii')
  - Provisos (e.g. '3.proviso_1')
  - Explanations (e.g. '3.explanation_1')

Features:
  - Skips front-matter Table of Contents (Arrangement of Sections)
  - Monotonic numbering validation (prevents mid-sentence false splits)
  - Bi-script support (English & Unicode Devanagari numerals and letters)
  - Footnote / Schedule exclusion
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from backend.app.segment.models import ClauseNode, ClauseTree
from backend.app.segment.numbering import (
    devanagari_to_arabic,
    normalize_section_number,
    normalize_clause_letter,
    is_roman_numeral,
    roman_to_int,
    HINDI_CONSONANT_MAP
)

# Common words following footnotes that distinguish them from real sections
FOOTNOTE_START_WORDS = {
    "ins.", "subs.", "omitted", "vide", "w.e.f.", "notification", "the",
    "added", "brackets", "words", "see", "धारा", "वर्ष", "के"
}

# Regex to detect enactment formula
ENACTMENT_PATTERNS_EN = [
    re.compile(r'\bBE\s+it\s+enacted\b', re.IGNORECASE),
    re.compile(r'\bAn\s+Act\s+to\b', re.IGNORECASE)
]

ENACTMENT_PATTERNS_HI = [
    re.compile(r'(?:अधिनियमित|अधिधिर्धमत|अधिधिर्मित|अिधिनयिमत|अहिहियहमत)\s*(?:हो|िो)'),
    re.compile(r'(?:संसद्|संसद|सिंसद्)\s*(?:द्वारा|द्व?य?यरय|᳇ारा)\s*(?:निम्नलिखित|धिम्?निधिधित|िन᭥\s*निलिखत|हिम्\s*िहलहित)\s*रूप\s*में\s*यह')
]

# Patterns signaling the end of substantive sections
END_MATTER_PATTERNS = [
    re.compile(r'^\s*(?:THE\s+)?(?:FIRST|SECOND|THIRD|FOURTH)?\s*SCHEDULE\b', re.IGNORECASE),
    re.compile(r'^\s*(?:पहली|दूसरी|तीसरी)?\s*अनुसूची\b'),
    re.compile(r'^\s*STATEMENT\s+OF\s+OBJECTS\s+AND\s+REASONS\b', re.IGNORECASE),
    re.compile(r'^\s*उद्देश्यों\s+और\s+कारणों\s+का\s+कथन\b')
]

# Proviso patterns
PROVISO_PATTERNS_EN = re.compile(r'^\s*Provided\s+(?:further\s+|also\s+)?that\b', re.IGNORECASE)
PROVISO_PATTERNS_HI = re.compile(r'^\s*(?:परन्तु|परंतु|परंतुक)(?:\s|[,:—–-]|$)', re.UNICODE)

# Explanation patterns
EXPLANATION_PATTERNS_EN = re.compile(r'^\s*Explanation(?:\s+([I|V|X]+|\d+))?\s*[.—–:\-]', re.IGNORECASE)
EXPLANATION_PATTERNS_HI = re.compile(r'^\s*स्पष्टीकरण(?:\s*([१-९\d]+))?(?:\s|[.—–:\-]|$)', re.UNICODE)


def find_substantive_start(lines: List[Tuple[str, int]], lang: str) -> int:
    """
    Finds index of the line where substantive Section 1 begins, skipping front-matter TOC.
    """
    enactment_idx = -1
    patterns = ENACTMENT_PATTERNS_EN if lang == "en" else ENACTMENT_PATTERNS_HI

    for idx, (line, _) in enumerate(lines):
        for pat in patterns:
            if pat.search(line):
                enactment_idx = idx
                break
        if enactment_idx != -1:
            break

    search_start = enactment_idx if enactment_idx != -1 else 0

    # Look for Section 1 after enactment formula (or from start if no enactment)
    for idx in range(search_start, len(lines)):
        line, _ = lines[idx]
        # Match Section 1 pattern
        m = re.match(r'^\s*(?:\d*\[)?(?:SECTIONS?|SEC\.|धारा)?\s*(?:1|१)\.\s*(.*)', line, re.IGNORECASE)
        if m:
            content = m.group(1).strip()
            # If after enactment, or content is substantive (not just TOC heading)
            if enactment_idx != -1 or "(1)" in content or "––(1)" in content or "—(1)" in content or "Short title" in content or "संक्षिप्त" in content:
                return idx

    return 0


def clean_line_token(line: str) -> str:
    """Removes common leading artifact symbols."""
    return line.strip()


def parse_section_header(line: str, expected_num: int, current_num: int) -> Optional[Tuple[str, str, str]]:
    """
    Attempts to parse a line as a section heading adhering to monotonic ordering.
    Returns: (section_id, title, rest_of_line) or None.
    """
    # Regex matching:
    # 1. '1. Short title...'
    # 2. '1[1. Short title...' (footnote replacement)
    # 3. 'Section 1. Short title...' / 'धारा 1. ...'
    # 4. '1A. ...' / '१क. ...'
    pat = r'^\s*(?:\d*\[)?(?:SECTIONS?|SEC\.|धारा)?\s*([०-९\d]+[\u0900-\u097Fa-zA-Z]?)\.\s*(.*)'
    m = re.match(pat, line, re.IGNORECASE)
    if not m:
        return None

    raw_sec_str = m.group(1)
    rest = m.group(2).strip()

    norm_sec = normalize_section_number(raw_sec_str)

    # Extract numeric base and letter suffix
    base_match = re.match(r'^(\d+)([A-Z]?)$', norm_sec)
    if not base_match:
        return None

    sec_base = int(base_match.group(1))
    sec_suffix = base_match.group(2)

    # Monotonicity check:
    # Next section must be strictly forward, allowing small steps (+1, +2, +3) for omitted sections
    is_valid = False
    if not sec_suffix:
        if current_num < sec_base <= current_num + 3:
            is_valid = True
        elif current_num == 0 and sec_base == 1:
            is_valid = True
    else:
        # Inserted section: e.g. 5A when current is 5, or 14B when current is 14
        if sec_base == current_num:
            is_valid = True
        elif current_num < sec_base <= current_num + 3:
            is_valid = True

    if not is_valid:
        return None

    # Filter out footnote lines like '1. Ins. by Act 18 of 2023' or '1. 19th November...'
    first_word = rest.split()[0].lower().strip(".,;:()") if rest.split() else ""
    if first_word in FOOTNOTE_START_WORDS and ("act" in rest.lower() or "subs" in rest.lower() or "ins" in rest.lower() or "vide" in rest.lower()):
        return None

    # Separate title and body if separated by em-dash
    # e.g. "Short title, extent and commencement.—(1) This Act..."
    em_dash_match = re.search(r'^(.*?)(?:[.—–-]{2,}|[.—–-]\s*\()', rest)
    if em_dash_match and len(em_dash_match.group(1).strip()) > 2:
        title = em_dash_match.group(1).strip(".—–- ")
        body = rest[len(em_dash_match.group(1)):].lstrip(".—–- ")
    elif "—" in rest:
        parts = rest.split("—", 1)
        title = parts[0].strip()
        body = parts[1].strip()
    elif "––" in rest:
        parts = rest.split("––", 1)
        title = parts[0].strip()
        body = parts[1].strip()
    else:
        title = rest
        body = ""

    return norm_sec, title, body


def segment_document(pages: List[Dict[str, Any]], lang: str = "en", act_slug: str = "") -> ClauseTree:
    """
    Main segmentation pipeline converting ingested document pages into a ClauseTree.
    """
    tree = ClauseTree(act_slug=act_slug, language=lang)

    # 1. Flatten all pages into line stream with line-level page tracking
    lines: List[Tuple[str, int]] = []
    for p in pages:
        p_no = p.get("page_no", 1)
        text = p.get("text", "")
        for l in text.split("\n"):
            cleaned = clean_line_token(l)
            if cleaned:
                lines.append((cleaned, p_no))

    if not lines:
        return tree

    # 2. Skip front-matter / Table of Contents
    start_line_idx = find_substantive_start(lines, lang)

    # 3. Partition lines into sections
    raw_sections: List[Dict[str, Any]] = []
    current_sec_data: Optional[Dict[str, Any]] = None
    expected_sec_num = 1
    current_sec_num = 0

    for idx in range(start_line_idx, len(lines)):
        line, page_no = lines[idx]

        # Check for schedule or end of substantive sections
        if any(pat.search(line) for pat in END_MATTER_PATTERNS):
            if current_sec_num >= 10:  # Only treat as end if substantive sections are well underway
                break

        header_res = parse_section_header(line, expected_sec_num, current_sec_num)
        if header_res:
            sec_id, title, rest_body = header_res
            base_num = int(re.match(r'^\d+', sec_id).group(0))

            if current_sec_data:
                raw_sections.append(current_sec_data)

            current_sec_num = base_num
            expected_sec_num = base_num + 1

            current_sec_data = {
                "sec_id": sec_id,
                "title": title,
                "page_no": page_no,
                "lines": [(rest_body, page_no)] if rest_body else []
            }
        else:
            if current_sec_data:
                current_sec_data["lines"].append((line, page_no))

    if current_sec_data:
        raw_sections.append(current_sec_data)

    # 4. Parse each section's lines into structured clause tree
    for rsec in raw_sections:
        sec_node = parse_section_body(
            sec_id=rsec["sec_id"],
            title=rsec["title"],
            lines=rsec["lines"],
            page_no=rsec["page_no"],
            lang=lang
        )
        tree.sections.append(sec_node)

    return tree


def parse_section_body(sec_id: str, title: str, lines: List[Tuple[str, int]], page_no: int, lang: str) -> ClauseNode:
    """
    Parses the internal content of a single section into subsections, clauses, sub-clauses, provisos, explanations.
    Enforces monotonic progression to ensure numbers inside sentences do not split clauses.
    """
    root_node = ClauseNode(
        path=sec_id,
        label=sec_id,
        title=title if title else None,
        text="",
        page_no=page_no,
        children=[]
    )

    if not lines:
        return root_node

    # State machine tracking active hierarchy
    # Possible states:
    # Top-level text of section
    # Subsections: path e.g. "1.1", "1.2"
    # Clauses: path e.g. "2.a", "1.1.a"
    # Sub-clauses: path e.g. "2.a.i"
    # Provisos / Explanations

    top_text_parts: List[str] = []
    
    # Active child nodes
    subsections: List[ClauseNode] = []
    current_subsec: Optional[ClauseNode] = None
    expected_subsec_num = 1

    # In sections without subsections (e.g. definitions section 2), clauses attach directly to section
    clauses: List[ClauseNode] = []
    current_clause: Optional[ClauseNode] = None
    expected_clause_ord = ord('a')

    # Sub-clauses (i, ii, iii) under a clause
    current_subclause: Optional[ClauseNode] = None
    expected_roman_int = 1

    proviso_count = 0
    explanation_count = 0

    for line_text, p_no in lines:
        line_clean = line_text.strip()
        if not line_clean:
            continue

        # Check for Proviso
        proviso_match = PROVISO_PATTERNS_EN.match(line_clean) or PROVISO_PATTERNS_HI.match(line_clean)
        if proviso_match:
            proviso_count += 1
            parent_path = current_subsec.path if current_subsec else sec_id
            p_node = ClauseNode(
                path=f"{parent_path}.proviso_{proviso_count}",
                label=f"Proviso {proviso_count}" if lang == "en" else f"परन्तुक {proviso_count}",
                text=line_clean,
                page_no=p_no,
                children=[]
            )
            if current_subsec:
                current_subsec.children.append(p_node)
            else:
                root_node.children.append(p_node)
            continue

        # Check for Explanation
        exp_match = EXPLANATION_PATTERNS_EN.match(line_clean) or EXPLANATION_PATTERNS_HI.match(line_clean)
        if exp_match:
            explanation_count += 1
            parent_path = current_subsec.path if current_subsec else sec_id
            e_node = ClauseNode(
                path=f"{parent_path}.explanation_{explanation_count}",
                label=f"Explanation {explanation_count}" if lang == "en" else f"स्पष्टीकरण {explanation_count}",
                text=line_clean,
                page_no=p_no,
                children=[]
            )
            if current_subsec:
                current_subsec.children.append(e_node)
            else:
                root_node.children.append(e_node)
            continue

        # Check for Subsection: e.g. '(1)', '(१)', '––(1)' at line start
        subsec_match = re.match(r'^\s*(?:\d*\[)?[—–-]*\s*\(([०-९\d]+)\)\s*(.*)', line_clean)
        if subsec_match:
            raw_num_str = subsec_match.group(1)
            num_int = int(devanagari_to_arabic(raw_num_str))
            rest = subsec_match.group(2).strip()

            # Monotonic check: must be expected_subsec_num
            if num_int == expected_subsec_num:
                # Close previous clause / subclause
                current_clause = None
                current_subclause = None
                expected_clause_ord = ord('a')

                new_path = f"{sec_id}.{num_int}"
                current_subsec = ClauseNode(
                    path=new_path,
                    label=f"({raw_num_str})",
                    text=rest,
                    page_no=p_no,
                    children=[]
                )
                root_node.children.append(current_subsec)
                expected_subsec_num = num_int + 1
                continue

        # Check for Clause: e.g. '(a)', '(b)', '(क)', '(ख)', '––(a)' at line start
        clause_match = re.match(r'^\s*(?:\d*\[)?[—–-]*\s*\(([a-zA-Z]|[\u0900-\u097F]+)\)\s*(.*)', line_clean)
        if clause_match:
            raw_letter = clause_match.group(1)
            norm_letter = normalize_clause_letter(raw_letter)
            rest = clause_match.group(2).strip()
            # If norm_letter is corrupted font artifact 'ि' (U+093F), resolve to expected letter
            if raw_letter == 'ि' and 'a' <= chr(expected_clause_ord) <= 'z':
                norm_letter = chr(expected_clause_ord)

            if len(norm_letter) == 1 and 'a' <= norm_letter <= 'z':
                letter_ord = ord(norm_letter)

                # Monotonic check: must match expected_clause_ord
                if letter_ord == expected_clause_ord:
                    # In definitions (Section 2), clauses attach directly to section (root_node)
                    if sec_id == "2" and current_subsec and current_subsec.path == f"{sec_id}.1":
                        parent_target = root_node
                    else:
                        parent_target = current_subsec if current_subsec else root_node

                    new_path = f"{parent_target.path}.{norm_letter}"
                    current_clause = ClauseNode(
                        path=new_path,
                        label=f"({raw_letter})",
                        text=rest,
                        page_no=p_no,
                        children=[]
                    )
                    parent_target.children.append(current_clause)
                    expected_clause_ord = letter_ord + 1
                    current_subclause = None
                    expected_roman_int = 1
                    continue

        # Check for Sub-clause: e.g. '(i)', '(ii)', '(iii)', '––(i)' at line start
        subclause_match = re.match(r'^\s*(?:\d*\[)?[—–-]*\s*\(([ivxlcdm]+)\)\s*(.*)', line_clean, re.IGNORECASE)
        if subclause_match:
            raw_roman = subclause_match.group(1).lower()
            rest = subclause_match.group(2).strip()

            if is_roman_numeral(raw_roman):
                r_int = roman_to_int(raw_roman)
                if r_int == expected_roman_int and current_clause:
                    new_path = f"{current_clause.path}.{raw_roman}"
                    current_subclause = ClauseNode(
                        path=new_path,
                        label=f"({raw_roman})",
                        text=rest,
                        page_no=p_no,
                        children=[]
                    )
                    current_clause.children.append(current_subclause)
                    expected_roman_int = r_int + 1
                    continue

        # Continuation text of the innermost active element
        if current_subclause:
            current_subclause.text = f"{current_subclause.text} {line_clean}".strip()
        elif current_clause:
            current_clause.text = f"{current_clause.text} {line_clean}".strip()
        elif current_subsec:
            current_subsec.text = f"{current_subsec.text} {line_clean}".strip()
        else:
            top_text_parts.append(line_clean)

    root_node.text = " ".join(top_text_parts).strip()
    return root_node
