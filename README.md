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

## Current Status: Phase Loop 0A Complete
Seven official Central Act bilingual pairs (14 PDF files) have been acquired directly from the official repository ([India Code Portal](https://indiacode.gov.in), Legislative Department, Ministry of Law and Justice, Government of India).

### Acquired & Verified Documents (`data/raw/`)
1. **The Environment (Protection) Act, 1986** (Act 29 of 1986) — *Short Act* (13 EN / 7 HI pages)
2. **The Protection of Women from Domestic Violence Act, 2005** (Act 43 of 2005) — *Short Act* (15 EN / 12 HI pages)
3. **The Right of Children to Free and Compulsory Education Act, 2009** (Act 35 of 2009) — *Short Act* (20 EN / 15 HI pages)
4. **The Right to Information Act, 2005** (Act 22 of 2005) — *Medium Act* (25 EN / 20 HI pages)
5. **The Consumer Protection Act, 2019** (Act 35 of 2019) — *Medium Act* (42 EN / 40 HI pages)
6. **The Indian Contract Act, 1872** (Act 9 of 1872) — *Medium Act* (53 EN / 41 HI pages)
7. **The Insolvency and Bankruptcy Code, 2016** (Act 31 of 2016) — *Long Act* (174 EN / 106 HI pages)

Full provenance and direct bitstream URLs are documented in [`data/raw/SOURCES.md`](data/raw/SOURCES.md).

---

## Running Data Verification
```bash
python3 backend/scripts/validate_data.py --data-dir data/raw
```
To output as structured JSON:
```bash
python3 backend/scripts/validate_data.py --data-dir data/raw --json
```

---

## Known Limitations & Honest Assessments
1. **Legacy Font Hindi Uploads**: A significant fraction of older state and central gazette uploads on government portals use proprietary legacy 8-bit ASCII fonts (such as KrutiDev or ShreeLipi) rather than Unicode NFC Devanagari. For instance, the official Hindi PDF of the Constitution of India on India Code decodes to ASCII glyph strings (`Hkkjr ljdkj fof/k vkSj U;k; ea=ky;`). In compliance with guardrails, Tulya flags and rejects these (`LEGACY_FONT_SUSPECTED`) rather than producing hallucinated or corrupted text.
2. **Heading Parity Variations**: In some Acts (e.g., IBC 2016), Hindi translations format clause headers inline or omit bold marginal headers, causing heading count discrepancies between English and Hindi streams despite matching section bodies.
3. **Usage Terms**: Official legal texts are sourced from `indiacode.gov.in` under fair-use provisions for academic, research, and legal review, with attribution to the Legislative Department, Ministry of Law and Justice. Commercial redistribution and scraping without rate-limiting are prohibited.
