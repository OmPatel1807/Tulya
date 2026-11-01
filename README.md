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

## Current Status: Phase Loop 6 Complete (End-to-End Evaluation & Improvement)
Tulya has completed its end-to-end evaluation harness and outer improvement loop:
- **Harness & Error Injector** (`backend/eval/inject.py`): Programmatically verified single-error injections into Hindi text across `NUMERIC`, `OMISSION`, `ADDITION`, `MODALITY`, and `SCOPE`, strictly partitioned by document.
- **Regression Suite** (`data/eval/dev/real_inspired_synthetic/cases.jsonl`): Synthetic reproductions of reported public statutory discrepancies (tax penalties, dropped qualifications, acreage differences).
- **Pipeline Runner & Merger** (`backend/app/pipeline/`): Reconciles deterministic fact differences and LLM semantic findings into unified `AuditFinding` records with verbatim Rule R2 quote verification.
- **Scorecard (Dev Set)**:
  - Injected Error Recall: **100.0%** (50 / 50)
  - Overall Precision: **87.7%** (50 TP / 7 FP)
  - Overall F1 Score: **0.935**
  - Clean False Positive Rate: **0.00** per 100 clauses (0 clean false positives)
  - Regression Cases Flagged: **6 / 6 (100.0%)**
- **Single Held-Out Evaluation (Rule R6)**: Evaluated once on frozen Acts (`contract_act_1872`, `insolvency_bankruptcy_2016`) with full distribution shift analysis in [`eval/report.md`](eval/report.md) and [`eval/results.json`](eval/results.json).

---

## Python Interpreter & Environment Requirements

- **Python Version**: `Python >= 3.10` (tested on `Python 3.14.6`)
- **Active Interpreter**: `/opt/anaconda3/bin/python3`
- **Core Dependencies** ([`requirements.txt`](requirements.txt)):
  - `pydantic` (v2 data modeling)
  - `pymupdf` & `pdfplumber` (text and PDF stream ingestion)
  - `sentence-transformers` & `torch` (LaBSE multilingual clause embeddings)
  - `rapidfuzz` (lexical alignment & misplaced clause screening)
  - `pytest` (test harness)

---

## Running the Pipeline & Verifiers

### 1. Run End-to-End Pipeline Verifier (Phase Loop 6 Exit Verifier)
```bash
python3 backend/eval/verify_pipeline.py
```

To run on the frozen held-out dataset:
```bash
python3 backend/eval/verify_pipeline.py --heldout
```

### 2. Generate Full Evaluation Artifacts (report.md & results.json)
```bash
python3 backend/eval/generate_report.py
```

### 3. Run Semantic Stage Verifier (Phase Loop 5 Exit Verifier)
```bash
PYTHONPATH=. python3 backend/eval/verify_semantic.py
```

### 2. Run Fact Extraction & Comparison Verifier (Phase Loop 4 Exit Verifier)
```bash
python3 backend/eval/verify_facts.py
```

### 3. Run Alignment Verifier (Phase Loop 3 Exit Verifier)
```bash
python3 backend/eval/verify_align.py
```

### 4. Run Structural Segmentation Verifier (Phase Loop 2 Exit Verifier)
```bash
python3 backend/eval/verify_segment.py
```

### 5. Run Ingestion Verifier (Phase Loop 1 Exit Verifier)
```bash
python3 backend/eval/verify_ingest.py
```

### 6. Run Ingestion CLI on an Act
```bash
python3 -m backend.app.ingest.cli right_to_information_2005 --out data/processed/right_to_information_2005.json
```

### 7. Run Full Unit Test Suite (All 78 Tests)
```bash
pytest backend/tests/ -v
```

### 8. Run Data Readiness Verifier (Phase Loop 0 Verifier)
```bash
python3 backend/scripts/validate_data.py --data-dir data/raw
```

---

## Known Limitations & Honest Assessments
1. **Additive Statutory Syntax Limit ("needs semantic stage")**: Pure numeric extraction alone cannot resolve structural phrase modifications such as "ten times the tax" vs. "tax plus a penalty of ten times the tax". Both clauses contain the numeric multiplier 10.0. Tulya's fact engine explicitly identifies additive statutory markers ("plus", "in addition to", "के अतिरिक्त") and marks these cases as `needs_semantic_stage = True` for the downstream semantic auditor.
2. **Partial-Legacy Gazettes**: Some official portal uploads (such as *Consumer Protection Act 2019*) contain hybrid PDFs where initial pages are in proprietary legacy 8-bit ASCII fonts (KrutiDev) while later pages are Unicode Devanagari. Tulya detects and discards these (`LEGACY_FONT_SUSPECTED`) to protect the integrity of downstream alignment and fact comparison.
3. **Inline Heading Formatting in Hindi Gazettes**: In several Acts (e.g., NGT 2010 and IBC 2016), Hindi translations format section headings inline with paragraph text or omit bold marginal tags, resulting in lower section-heading regex counts despite complete clause text presence.
4. **Usage Terms**: Official legal texts are sourced from `indiacode.gov.in` under fair-use provisions for academic, research, and legal review, with attribution to the Legislative Department, Ministry of Law and Justice. Commercial redistribution is prohibited.
