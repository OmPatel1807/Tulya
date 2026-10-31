# Tulya (तुल्य)
> "Two official versions of the same law. Do they say the same thing? Tulya checks, clause by clause, and shows the evidence."

Tulya is an evidence-backed bilingual law consistency auditor for Indian legal texts (English and Hindi), built for civic pulse, digital governance, and public information.

## Concept & Purpose
Indian Acts, rules, and notifications are published in two or more official languages (e.g., English and Hindi). Both versions are official. Discrepancies between language versions can alter legal meaning depending on which version is read.

Publicly reported cases include discrepancies in tax penalties (ten times payable vs. ten times in addition to tax), dropped qualifications, and differing land acquisition acreage.

Tulya serves as a **Reviewer's Assistant**:
- Audits existing official pairs clause by clause.
- Deterministic hard-fact verification (numbers, dates, percentages, amounts, durations, cross-references).
- Grounded LLM semantic comparison with exact bidirectional quotes.
- **Important Disclaimer**: Tulya flags differences for human review. It does not decide or imply which version is legally authoritative, nor does it provide legal advice.

---

## Current Status: Phase Loop 1 Complete (Ingestion & Normalization)
All 7 verified Central Act bilingual pairs (14 PDF files) are processed through the ingestion pipeline (`backend/app/ingest/`):
- PyMuPDF text extraction with `pdfplumber` fallback.
- Unicode NFC normalization and zero-width artifact stripping.
- Script validation and legacy font detection (`script_check.py`).
- Automatic edge-line repeated header and footer removal (`clean.py`).
- Cross-lingual hyphenated line break repair (`clean.py`).
- Language splitting for separate files (`_en`/`_hi`) and single bilingual files (`_bi`).

### Verified Corpus (`data/raw/`)
1. **The Environment (Protection) Act, 1986** (Act 29 of 1986) — *Short Act* (13 EN / 7 HI pages)
2. **The Protection of Women from Domestic Violence Act, 2005** (Act 43 of 2005) — *Short Act* (15 EN / 12 HI pages)
3. **The Right of Children to Free and Compulsory Education Act, 2009** (Act 35 of 2009) — *Short Act* (20 EN / 15 HI pages)
4. **The Right to Information Act, 2005** (Act 22 of 2005) — *Medium Act* (25 EN / 20 HI pages)
5. **The National Green Tribunal Act, 2010** (Act 19 of 2010) — *Medium Act* (23 EN / 19 HI pages)
6. **The Indian Contract Act, 1872** (Act 9 of 1872) — *Medium Act* (53 EN / 41 HI pages)
7. **The Insolvency and Bankruptcy Code, 2016** (Act 31 of 2016) — *Long Act* (174 EN / 106 HI pages)

Full provenance and direct bitstream URLs are documented in [`data/raw/SOURCES.md`](data/raw/SOURCES.md).

---

## Running the Ingestion Pipeline & Verifiers

### 1. Run Ingestion CLI on an Act
```bash
python3 -m backend.app.ingest.cli right_to_information_2005 --out data/processed/right_to_information_2005.json
```

### 2. Run Ingestion Verifier (Phase Loop 1 Exit Verifier)
```bash
python3 backend/eval/verify_ingest.py
```
To print 15 random sample lines per language per document for visual inspection:
```bash
python3 backend/eval/verify_ingest.py --samples
```

### 3. Run Unit Tests
```bash
python3 -m pytest backend/tests/ -v
```

### 4. Run Data Readiness Verifier (Phase Loop 0 Verifier)
```bash
python3 backend/scripts/validate_data.py --data-dir data/raw
```

---

## Known Limitations & Honest Assessments
1. **Partial-Legacy Gazettes**: Some official portal uploads (such as *Consumer Protection Act 2019*) contain hybrid PDFs where initial pages are in proprietary legacy 8-bit ASCII fonts (KrutiDev) while later pages are Unicode Devanagari. Tulya detects and discards these (`LEGACY_FONT_SUSPECTED`) to protect the integrity of downstream alignment and fact comparison.
2. **Inline Heading Formatting in Hindi Gazettes**: In several Acts (e.g., NGT 2010 and IBC 2016), Hindi translations format section headings inline with paragraph text or omit bold marginal tags, resulting in lower section-heading regex counts despite complete clause text presence.
3. **Usage Terms**: Official legal texts are sourced from `indiacode.gov.in` under fair-use provisions for academic, research, and legal review, with attribution to the Legislative Department, Ministry of Law and Justice. Commercial redistribution is prohibited.
