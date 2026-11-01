# Tulya End-to-End Pipeline Evaluation Report

> "Two official versions of the same law. Do they say the same thing? Tulya checks, clause by clause, and shows the evidence."

## Executive Summary
- **Dev Evaluation**: Recall = **100.0%**, Precision = **87.7%**, F1 = **0.935**, Clean FP Rate = **0.00** per 100 clauses.
- **Held-out Evaluation**: Recall = **88.0%**, Precision = **47.8%**, F1 = **0.620**, Clean FP Rate = **16.00** per 100 clauses.
- **Regression Cases**: **6 / 6 (100.0%)** flagged across all reported statutory discrepancy patterns.
- **Guardrail Compliance**: Strictly adheres to Rule R5 (all synthetic injections explicitly labeled synthetic) and Rule R6 (held-out documents frozen and evaluated exactly once without post-hoc tuning).

---

## 1. Side-by-Side Comparison: Dev vs. Held-out

### A. Overall & Category Metrics

| Metric / Category | Dev Injected | Dev Recall | Dev Precision | Dev F1 | Held-out Injected | Held-out Recall | Held-out Precision | Held-out F1 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NUMERIC** | 10 | 100.0% | 90.9% | 0.952 | 5 | 100.0% | 41.7% | 0.588 |
| **OMISSION** | 10 | 100.0% | 100.0% | 1.000 | 5 | 60.0% | 100.0% | 0.750 |
| **ADDITION** | 10 | 100.0% | 90.9% | 0.952 | 5 | 80.0% | 80.0% | 0.800 |
| **MODALITY** | 10 | 100.0% | 83.3% | 0.909 | 5 | 100.0% | 41.7% | 0.588 |
| **SCOPE** | 10 | 100.0% | 76.9% | 0.870 | 5 | 100.0% | 100.0% | 1.000 |
| **OVERALL** | **50** | **100.0%** | **87.7%** | **0.935** | **25** | **88.0%** | **47.8%** | **0.620** |

### B. Pipeline Performance & Safety Breakdown

| Pipeline Metric | Dev Set | Held-out Set (Frozen) | Target / Specification |
| :--- | :--- | :--- | :--- |
| **Clean False Positive Rate** | **0.00** per 100 clauses | **16.00** per 100 clauses | <= 5.0 per 100 clauses |
| **Total Clean False Positives** | 0 findings (0 clauses) | 9 findings (4 clauses) | Benchmark |
| **Deterministic Only (Fact Stage)** | 16 (28.1%) | 40 (70.2%) | Tracked |
| **LLM Only (Semantic Stage)** | 35 (61.4%) | 14 (24.6%) | Tracked |
| **Both (Confirmed & Merged)** | 6 (10.5%) | 3 (5.3%) | Tracked |
| **Ungrounded Discard Rate (Rule R2)** | 0.0% (0 discards) | 0.0% (0 discards) | Exact quote grounding |
| **Latency per 100 Clauses** | 0.28 s | 0.20 s | Real-time interactive |
| **Cost per 100 Clauses** | $0.0033 | $0.0028 | < $0.05 / 100 clauses |

---

## 2. Regression Suite: Reported Real-World Statutory Divergences

The regression suite replicates reported public statutory patterns under strict synthetic labeling (Rule R5):

| Case ID | Pattern Description | Injected In | Expected Category | Status | Primary Finding Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `reg_synth_01_ten_times_tax` | pattern_a_ten_times_tax | Hindi | `ADDITION` | **FLAGGED (PASS)** | EN: 'ten times the tax' | HI: 'कर के अतिरिक्त' |
| `reg_synth_01b_tax_plus_penalty` | pattern_a_ten_times_tax | Hindi | `OMISSION` | **FLAGGED (PASS)** | EN: 'tax plus a penalty' | HI: 'None' |
| `reg_synth_02_missing_qualification_notice` | pattern_b_missing_qualification | Hindi | `OMISSION` | **FLAGGED (PASS)** | EN: 'prior notice in writing' | HI: 'None' |
| `reg_synth_02b_missing_qualification_approval` | pattern_b_missing_qualification | Hindi | `OMISSION` | **FLAGGED (PASS)** | EN: 'prior approval of the Central Government' | HI: 'None' |
| `reg_synth_03_area_03_vs_3_acres` | pattern_c_area_order_of_magnitude | Hindi | `NUMERIC` | **FLAGGED (PASS)** | EN: '0.3 acres' | HI: '3 एकड़' |
| `reg_synth_03b_area_10_vs_100_hectares` | pattern_c_area_order_of_magnitude | Hindi | `NUMERIC` | **FLAGGED (PASS)** | EN: '10 hectares' | HI: '100 हेक्टेयर' |

---

## 3. Analysis of Held-out Discrepancy (Honest Assessment)

While **injected recall on held-out remained high at 88.0%** (22 out of 25 synthetic discrepancies detected, with 100% recall on NUMERIC, MODALITY, and SCOPE), **overall precision dropped from 87.7% to 47.8%** and **clean false positive rate rose from 0.0 to 16.0 findings per 100 clauses**.

In accordance with Rule R6, **we do NOT tune post-hoc on held-out documents**. Instead, we diagnose the exact root causes of this divergence:

### Root Causes of Held-out Distribution Shift:
1. **Dense Legislative Footnote Citations in Corporate Codes (Insolvency and Bankruptcy Code, 2016)**:
   - *Observation*: In `heldout_clean_10`, the Hindi PDF included substantive amendment notes in the clause body (`2018 का 26, धारा 2 द्वारा (1-1-2018 से) अंतःस्थापित`) that were omitted from the English clause text.
   - *Impact*: The deterministic fact engine detected the dates ('2018') and section numbers ('धारा 2') as `MISSING_IN_EN`, producing false positive findings on clean text.
   - *Diagnosis*: Unlike Dev Acts (Domestic Violence, RTI, EPA) where amendments are either consolidated or absent, IBC 2016 has extensive legislative insertion footnotes that were extracted into the Hindi body text stream.

2. **Devanagari Section Suffix Letter Mapping (`धारा 45झ` vs `Section 45-I`)**:
   - *Observation*: In `heldout_clean_09`, English cited `section 45` of the RBI Act, while Hindi cited `धारा 45झ` (Section 45-I in Devanagari transliteration).
   - *Impact*: Section reference normalizer recognized '45' vs '45झ' as a `VALUE_MISMATCH`, producing a deterministic finding on a clean aligned clause.

3. **Categorization of Embedded Numbers in Omission/Addition**:
   - *Observation*: In `heldout_omission_03` ('one crore rupees' omitted), `heldout_omission_05` ('forty-eight hours' omitted), and `heldout_addition_05` ('सात दिन' added), the pipeline DID detect the discrepancy, but classified them as `NUMERIC` rather than `OMISSION` or `ADDITION`.
   - *Impact*: While the system successfully alerted human reviewers to the discrepancy, the strict category evaluation labeled them as category false positives / false negatives.

---

## 4. Known Failure Modes

Based on genuine misses and false positives across all iterations, the following failure modes have been identified:

1. **Hybrid Sub-word Devanagari Numerals**: Multi-word numbers like 'एक सौ बीस' (120) occasionally decompose into 'सौ' and 'बीस' when gazette typography inserts non-standard whitespace, triggering partial number mismatches against English compound numbers.
2. **Statutory Reference Asymmetry in Suffix Letters**: Indian legislative drafting uses Roman letters for inserted sections (e.g., Section 14A, 45-I) while Hindi uses Devanagari consonants (धारा 14क, 45झ). If the letter suffix is omitted in one language stream, it is flagged as a factual mismatch.
3. **Amendment Divergence Across Gazette Publications**: English and Hindi uploads on official portals are occasionally updated in different gazette cycles (e.g. EPA 1986 where English reflects Jan Vishwas Act 2023 amendments while Hindi reflects the principal Act). The pipeline flags these as true statutory divergences, though they stem from publication edition lag.
4. **Incidental Legal Ordinals**: Ordinal words like 'प्रथम' (first) in 'प्रथम श्रेणी' (first class magistrate) or 'द्वितीय' (second) in 'द्वितीय अपील' (second appeal) can trigger false fact mismatches if the opposing language uses alternative phrasing.

---

## 5. System Limitations

1. **Reviewer's Assistant Constraint**: Tulya identifies and surfaces discrepancies with exact quoted evidence for human review. It does NOT decide which version is legally authoritative, nor does it resolve conflicting judicial precedents regarding statutory translation hierarchy.
2. **Strict Verbatim Grounding Guard (Rule R2)**: Tulya enforces that quotes must be exact substrings of source texts. While this eliminates hallucinations, it means findings that describe structural shifts across distant paragraphs are reported as unaligned clauses rather than merged semantic quotes.
3. **Scan/OCR Gazette Quality**: Tulya requires Unicode Devanagari text. If a portal upload uses legacy 8-bit non-Unicode fonts (e.g. KrutiDev ASCII mapping) or scanned raster PDFs without an OCR text layer, Tulya halts extraction with `LegacyFontError` rather than guessing corrupted text.
