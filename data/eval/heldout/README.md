# Frozen Held-Out Dataset

In accordance with Rule R6 of the Tulya specification:
- **Held-out Documents**:
  1. `contract_act_1872` (The Indian Contract Act, 1872)
  2. `insolvency_bankruptcy_2016` (The Insolvency and Bankruptcy Code, 2016)
- **Constraint**: These documents are strictly frozen. They must NEVER be used for tuning heuristics, debugging segmentation rules, prompt engineering, or threshold optimization.
- **Evaluation**: They will only be evaluated at the final Phase Loop 6/8 pipeline assessment.
