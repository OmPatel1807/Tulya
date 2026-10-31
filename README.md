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

## Current Status: Phase Loop 5 Complete (Grounded Semantic Stage)
Bilingual English and Hindi clauses are compared semantically for substantive differences in legal effect, backed by strict grounding and deterministic safety guards:
- **Data Models** (`backend/app/semantic/models.py`): Pydantic models for `SemanticFinding` (`category`, `severity`, `explanation`, `quote_en`, `quote_hi`, `confidence`) across categories: `MODALITY`, `OMISSION`, `ADDITION`, `SCOPE`, `DEFINITION`, `REORDERED` / `MISPLACED`.
- **Grounding Guard (Rule R2)** (`backend/app/semantic/grounding.py`): Every finding requires exact verbatim substring quotes from both versions (or null when content is genuinely missing) after Unicode NFKC and whitespace normalization. Hallucinated or non-verbatim quotes are discarded and tracked.
- **Modality Lexicon & Deontic Pre-screening** (`backend/app/semantic/modality.py`): Detects statutory shifts between mandatory obligations (`shall`, `must` / `करेगा`, `होगी`) and permissive discretions (`may`, `entitled to` / `कर सकेगा`, `हो सकेगी`).
- **Persistent Disk Caching** (`backend/app/semantic/cache.py`): SQLite cache (`semantic_responses.sqlite`) keyed by `SHA-256(provider:model:prompt_version:content_hash)` ensuring determinism, instant replay, and strict budget adherence.
- **Cross-Section Misplaced Clause Lookup** (`backend/app/semantic/reorder_lookup.py`): Scans candidate clauses across opposing statutory trees using RapidFuzz and cross-lingual LaBSE embeddings to distinguish cross-section relocations from true omissions.
- **Semantic Comparator Client** (`backend/app/semantic/client.py`): Modular provider architecture supporting Gemini (`google-genai`), Anthropic (`anthropic`), and offline high-fidelity mock inference; handles JSON validation with single retry and ThreadPool concurrency.
- **Evaluation Dev Set** (`data/eval/dev/semantic_cases.jsonl`): 80 cases (40 clean pairs, 40 injected synthetic errors across modality, omission, addition, scope, and definition).
- **Frozen Held-Out Set** (`data/eval/heldout/semantic_cases.jsonl`): 40 cases kept strictly untouched for evaluation.
- **Semantic Verifier** (`backend/eval/verify_semantic.py`): 100% recall on MODALITY, OMISSION, ADDITION, SCOPE; 97.6% precision; 0.0 clean false positive rate; 0.0% JSON failure rate; 19,568 tokens used (well within 300,000 budget).

### Verified Corpus (`data/raw/`)
1. **The Environment (Protection) Act, 1986** (Act 29 of 1986) — *Short Act* (13 EN / 7 HI pages)
2. **The Protection of Women from Domestic Violence Act, 2005** (Act 43 of 2005) — *Short Act* (15 EN / 12 HI pages)
3. **The Right of Children to Free and Compulsory Education Act, 2009** (Act 35 of 2009) — *Short Act* (20 EN / 15 HI pages)
4. **The Right to Information Act, 2005** (Act 22 of 2005) — *Medium Act* (25 EN / 20 HI pages)
5. **The National Green Tribunal Act, 2010** (Act 19 of 2010) — *Medium Act* (23 EN / 19 HI pages)
6. **The Indian Contract Act, 1872** (Act 9 of 1872) — *Medium Act* (53 EN / 41 HI pages) [Frozen Held-Out]
7. **The Insolvency and Bankruptcy Code, 2016** (Act 31 of 2016) — *Long Act* (174 EN / 106 HI pages) [Frozen Held-Out]

Full provenance and direct bitstream URLs are documented in [`data/raw/SOURCES.md`](data/raw/SOURCES.md).

---

## Running the Pipeline & Verifiers

### 1. Run Semantic Stage Verifier (Phase Loop 5 Exit Verifier)
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
