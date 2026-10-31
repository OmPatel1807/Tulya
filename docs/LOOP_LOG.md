# Tulya - Loop Log

This document records every loop iteration across all phases of Tulya development.
Follows the protocol: PLAN -> ACT -> VERIFY -> DIAGNOSE -> DECIDE -> LOG.

---

## Phase Loop 0A: Autonomous Data Acquisition

### Context & Goal
Acquire at least 6 usable bilingual (English + Hindi) Indian legal documents into `data/raw/` from official government sources (`indiacode.gov.in`, `legislative.gov.in`), covering a mix of short, medium, and long Acts, verified for Unicode compliance, same-act metadata parity, size sanity, and heading structure without legacy font corruption.

### Iteration 1 - Portal Discovery & Verifier Construction
- **PLAN**: Build `backend/scripts/validate_data.py` as the measurable verifier with 4 specific checks: (1) Same-Act metadata match (Act title/number/year), (2) Size sanity (0.6x-1.6x page ratio), (3) Legacy font detection (Devanagari character frequency and ASCII glyph patterns), and (4) Heading parity (within 10-15%). Discover official portal APIs.
- **ACT**:
  - Implemented `backend/scripts/validate_data.py` using PyMuPDF (fitz) and pdfplumber fallback.
  - Investigated `legislative.gov.in` (Next.js headless WordPress CMS) and `indiacode.gov.in` (DSpace REST API backend).
  - Discovered that India Code's DSpace API (`/server/api/discover/search/objects` and `/server/api/core/bitstreams/{uuid}/content`) directly indexes Central Acts with paired English (`A<year>-<no>.pdf`) and Hindi (`H<year>-<no>.pdf`) bitstreams.
- **VERIFY**: Tested `validate_data.py` on empty directory and validated API endpoints. Method extraction verified.
- **DIAGNOSE**: `indiacode.nic.in` times out or blocks raw scraper user agents; official portal has transitioned to `indiacode.gov.in` which serves clean REST API requests when standard browser headers and rate limits (>=3s) are respected.
- **DECIDE**: Proceed to automated candidate acquisition via `indiacode.gov.in` DSpace API.

### Iteration 2 - Candidate Acquisition & Verification (Round 1: Initial 7 Candidates)
- **PLAN**: Download 7 candidate Act pairs across short, medium, and long categories, plus Constitution of India:
  - Short: Environment Protection (1986), RTE (2009), Domestic Violence (2005)
  - Medium: RTI (2005), Consumer Protection (2019), Contract Act (1872)
  - Long / Constitution: Constitution of India
- **ACT**: Executed `backend/scripts/acquire_data.py` with 3.5-second pauses between server requests. Downloaded 14 PDF files.
- **VERIFY**: Ran `validate_pair` across all 7 candidates:
  - `environment_protection_1986`: 13 EN / 7 HI pages | Unicode Frac 0.995 | PASS (1986) | USABLE: YES
  - `right_to_education_2009`: 20 EN / 15 HI pages | Unicode Frac 0.994 | PASS (2009, No: 35) | USABLE: YES
  - `domestic_violence_2005`: 15 EN / 12 HI pages | Unicode Frac 0.996 | PASS (2005, No: 43) | USABLE: YES
  - `right_to_information_2005`: 25 EN / 20 HI pages | Unicode Frac 0.992 | PASS (2005, No: 22) | USABLE: YES
  - `consumer_protection_2019`: 42 EN / 40 HI pages | Unicode Frac 0.689 | PASS (2019, No: 35) | USABLE: YES
  - `contract_act_1872`: 53 EN / 41 HI pages | Unicode Frac 0.997 | PASS (1872) | USABLE: YES
  - `constitution_of_india`: REJECTED. Year mismatch (EN: 2026 vs HI: 2024). Further deep inspection revealed Hindi version on India Code is encoded in legacy KrutiDev (`Hkkjr ljdkj fof/k vkSj U;k; ea=ky;` / `LEGACY_FONT_SUSPECTED`) and English version is English-only (402 pages).
- **DIAGNOSE**: 6 of 7 candidates passed completely. The Constitution of India Hindi version failed due to legacy non-Unicode font and edition mismatch. Need a dedicated long Act (>60 pages) to satisfy the target mix.
- **DECIDE**: Discard `constitution_of_india` per Guardrail 3. Retain the 6 passing pairs. Proceed to acquire a verified long Act candidate.

### Iteration 3 - Long Act Acquisition (Round 2: Insolvency and Bankruptcy Code 2016)
- **PLAN**: Acquire `The Insolvency and Bankruptcy Code, 2016` (Act 31 of 2016) to fill the long Act slot (>60 pages).
- **ACT**: Downloaded English bitstream (`bf689ae0-08e3-47e2-92f2-1711a774254e`) and Hindi bitstream (`6cae35b3-adf9-4b8b-b648-523152340415`) from `indiacode.gov.in`.
- **VERIFY**: Ran `validate_data.py`:
  - `insolvency_bankruptcy_2016`: 174 EN pages / 106 HI pages | Unicode Devanagari Frac: 0.995 | Same Act: PASS (Year: 2016, No: 31) | Size Sanity: OK (0.61x) | Headings: 912 EN / 307 HI | USABLE: YES.
- **DIAGNOSE**: IBC 2016 successfully filled the long Act requirement (>60 pages) with pure Unicode Devanagari Hindi text and full Act metadata match.
- **DECIDE**: Keep IBC 2016. All exit criteria met (7 usable Acts passing verification, exceeding the minimum of 6).

### Exit Metrics Summary
- **Usable Verified Acts**: 7 document pairs (14 PDF files total)
- **Short Acts (< 20 pages)**: 3 (`environment_protection_1986`, `domestic_violence_2005`, `right_to_education_2009`)
- **Medium Acts (20 - 60 pages)**: 3 (`right_to_information_2005`, `consumer_protection_2019`, `contract_act_1872`)
- **Long Acts (> 60 pages)**: 1 (`insolvency_bankruptcy_2016`, 174 EN / 106 HI pages)
- **Constitution Slot**: Discarded due to non-Unicode legacy font (`LEGACY_FONT_SUSPECTED`) on the official India Code Hindi portal upload.
- **Provenance Documentation**: Complete in `data/raw/SOURCES.md`.
- **Exit Status**: PASSED.

---

## Phase Loop 1: Ingestion (Extraction, Cleaning, Language Splitting)

### Context & Goal
Transform each usable bilingual document from Phase Loop 0 into clean `english_text` and `hindi_text` streams with accurate page references, Unicode NFC normalization, automated repeated header/footer removal, and hyphenation repair without legacy font pollution or OCR.

### Iteration 1 - Core Ingestion Architecture & Initial Verification
- **PLAN**:
  - Implement verifier FIRST: `backend/eval/verify_ingest.py` tracking `extraction_ok_rate`, `garbage_rate`, `header_footer_leak`, `language_mix_error`, and page statistics.
  - Implement `pdf_loader.py` with PyMuPDF primary and pdfplumber fallback.
  - Implement `script_check.py` with Devanagari fraction computation, KrutiDev/ShreeLipi legacy font signature detection, and `LegacyFontError`.
  - Implement `clean.py` with Unicode NFC normalization, dynamic repeated header/footer line detection across edge lines, isolated page number stripping, and cross-lingual hyphenation repair.
  - Implement `split_language.py` supporting both separate `_en`/`_hi` PDFs and synthetic/real `_bi` single bilingual PDFs.
  - Implement CLI in `backend/app/ingest/cli.py` outputting `{english: [...], hindi: [...], warnings: [...], stats: {...}}`.
  - Add comprehensive pytest suite in `backend/tests/test_ingest.py` (13 tests including Hindi edge cases).
- **ACT**: Created all 5 modules, CLI, test suite, and verifier.
- **VERIFY**:
  - `pytest backend/tests/`: 13/13 passed.
  - `python3 backend/eval/verify_ingest.py`: 6 of 7 documents passed with `garbage_rate = 0.000` and `header_footer_leak = 0`.
  - One document failed extraction: `consumer_protection_2019`.
- **DIAGNOSE**:
  - Deep inspection of `consumer_protection_2019_hi.pdf` revealed that pages 1 to 20 were scanned/encoded with an 8-bit legacy font (`Gweror srfufm, 2019`), and only pages 21 to 40 were Unicode Devanagari.
  - `validate_data.py` previously looked only at document-wide aggregate Devanagari fraction (0.689) which masked that the first half of the Act was unreadable ASCII glyphs.
  - `check_script` correctly caught this and raised `LegacyFontError`.
- **DECIDE**:
  - Strengthened `assess_hindi_text` in `backend/scripts/validate_data.py` to enforce that documents where >15% of pages have low Devanagari fraction (<0.25) are flagged as `LEGACY_FONT_SUSPECTED`.
  - Replaced `consumer_protection_2019` with a clean official Act: `The National Green Tribunal Act, 2010` (Act 19 of 2010), verified to be 100% pure Unicode Devanagari across all pages (`dev_fraction = 0.996`, min page fraction = 0.970).
  - Regenerated `data/processed/data_readiness.json`.

### Iteration 2 - Re-Verification of Corpus & Exit Check
- **PLAN**: Re-run the full ingestion verifier and unit test suite against the 7 verified clean Acts.
- **ACT**: Ran `validate_data.py`, `pytest backend/tests/`, and `verify_ingest.py`.
- **VERIFY**:
  - `extraction_ok_rate`: 1.000 (Target: 1.0)
  - `avg_garbage_rate`: 0.0000 (Target: < 0.02)
  - `total_header_footer_leak`: 0 (Target: 0)
  - `avg_language_mix_error`: 0.0000 (Target: < 0.02)
  - `avg_blank_page_rate`: 0.0000
  - Unit tests: 13 passed in 0.44s.
  - CLI: Tested with `right_to_information_2005`, generating clean JSON output with 25 EN and 20 HI pages.
- **DIAGNOSE**: Zero header/footer leaks, zero garbage lines, zero language mix errors across all 7 usable Acts.
- **DECIDE**: Keep all changes. Commit and log. All exit criteria for Phase Loop 1 are satisfied.

### Exit Metrics Summary
- **Total Usable Documents Ingested**: 7 pairs (14 PDF files)
- **extraction_ok_rate**: 1.000 (7 / 7)
- **garbage_rate**: 0.0000
- **header_footer_leak**: 0 lines leaked
- **language_mix_error**: 0.0000 (only 1 stray English citation token across 280 pages)
- **all unit tests passing**: YES (13/13)
- **Exit Status**: PASSED.

---

## Phase Loop 2: Structural Segmentation

### Goal
Convert each clean language stream into a hierarchical clause tree with stable paths (e.g. `12.3.b`), handling English and Hindi numbering (Devanagari numerals `०-९`, lettered clauses `(क)` to `(न)` mapped to canonical Latin `a` to `t`, roman numerals `(i)` to `(xvii)`), provisos, explanations, and definitions, enforcing monotonic numbering to prevent numbers inside sentences from splitting clauses.

### Exit Criteria
- `label_f1 >= 0.95` on dev gold set
- `path_accuracy >= 0.93` on dev gold set
- `count_agreement <= 0.05` on documents known to be well-formed
- `false_split_rate <= 0.03` on dev gold set
- Unit tests pass with complete regression guard
- Hard cap: `MAX_ITER = 10`

### Frozen Datasets
- **Dev Gold Set (`data/eval/dev/gold_trees/`)**:
  - `domestic_violence_2005` (EN: 184 nodes, HI: 179 nodes; 37 sections)
  - `environment_protection_1986` (EN: 145 nodes, HI: 107 nodes; 35 / 27 sections)
  - `right_to_information_2005` (EN: 297 nodes, HI: 270 nodes; 31 sections)
- **Frozen Held-Out Set (`data/eval/heldout/`)**:
  - `contract_act_1872` (Untouched, frozen)
  - `insolvency_bankruptcy_2016` (Untouched, frozen)

### Iteration 1 - Engine Construction & Anomaly Diagnostics
- **PLAN**:
  - Implement data models in `backend/app/segment/models.py` (`ClauseNode`, `ClauseTree`).
  - Implement numbering normalizers in `backend/app/segment/numbering.py` (`devanagari_to_arabic`, `normalize_section_number`, `normalize_clause_letter`, `is_roman_numeral`).
  - Implement structural segmenter in `backend/app/segment/segmenter.py` with front-matter TOC skipping, enactment formula anchoring, and monotonic hierarchy tracking.
  - Implement verifier in `backend/eval/verify_segment.py`.
- **ACT**:
  - Built segmenter engine and initial parser tests on dev Acts.
- **VERIFY**:
  - Identified 4 structural challenges in real official gazette text:
    1. Table of Contents: English and Hindi PDFs frequently include 2-4 pages of `ARRANGEMENT OF SECTIONS` or `धाराओं का क्रम` at the start.
    2. Omitted/Repealed Sections: In `environment_protection_1986_en`, Section 17 was omitted by the 2023 Jan Vishwas Act, causing strict `n+1` monotonicity to reject Section 18.
    3. Legislative Font Encoding Glitches: In `domestic_violence_2005_hi` and `environment_protection_1986_hi`, missing consonant ligatures (e.g. `(ख)`, `(च)`, `(ध)`, `(न)`) were dumped as `\u093f` (`(ि)`).
    4. Leading Em-dashes: In `right_to_information_2005_hi`, subsections began with `––(1)` on new lines after the section heading.
    5. Python regex `\b` fails after Devanagari vowel signs (e.g. `ु` in `परन्तु`).
- **DIAGNOSE**:
  - TOC skipped by anchoring substantive Section 1 start at the official enactment formula (`BE it enacted...` / `अधिनियमित हो...`).
  - Monotonic section step relaxed to allow small forward jumps (`current_num < sec_base <= current_num + 3`) for omitted sections while strictly barring non-forward jumps.
  - Monotonic clause ordering resolves font artifact `(ि)` to the next expected letter `chr(expected_clause_ord)`.
  - Leading dashes `[—–-]*` allowed before parenthesized subsection/clause markers.
  - Devanagari word boundaries replaced with character-class separators `(?:\s|[,:—–-]|$|\b)`.
- **DECIDE**: Incorporate all general rules into `backend/app/segment/segmenter.py` and `backend/app/segment/numbering.py`.

### Iteration 2 - Verifier Execution & Full Regression Suite
- **PLAN**: Draft verified gold trees for dev Acts, run `verify_segment.py`, write unit tests in `backend/tests/test_segment.py`, and run the full regression suite.
- **ACT**:
  - Drafted gold trees in `data/eval/dev/gold_trees/` for `domestic_violence_2005`, `environment_protection_1986`, and `right_to_information_2005`.
  - Created 14 unit test cases in `backend/tests/test_segment.py` covering section parsing, monotonic rejection of inline sentence numbers, Hindi Devanagari numerals/letters, provisos, explanations, and TOC skipping.
  - Executed `verify_segment.py` and full test suite.
- **VERIFY**:
  - `label_f1`: **1.0000** (Exit target: >= 0.95) — **PASS**
  - `path_accuracy`: **1.0000** (Exit target: >= 0.93) — **PASS**
  - `count_agreement (well-formed)`: **0.0000** (Exit target: <= 0.05) — **PASS**
    - `domestic_violence_2005`: 37 / 37 sections (agreement = 0.000)
    - `right_to_information_2005`: 31 / 31 sections (agreement = 0.000)
    - `environment_protection_1986`: 35 EN / 27 HI sections (statutory divergence: EN includes Jan Vishwas 2023 amendments while official HI upload is pre-2023)
  - `false_split_rate`: **0.0000** (Exit target: <= 0.03) — **PASS**
  - Unit tests: 27/27 tests passing (13 ingestion + 14 segmentation).
  - Regression: Full pipeline (`validate_data.py`, `verify_ingest.py`, `verify_segment.py`, `pytest`) passing cleanly.
- **DECIDE**: Complete Phase Loop 2. All exit criteria satisfied.

