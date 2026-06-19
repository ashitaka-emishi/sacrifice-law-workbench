# Model Reliability Disagreement Classification

`scripts/model_reliability/classify_disagreements.py` converts field-level
comparison evidence into an item-level diagnostic log and a human-readable
instability report:

```bash
python3 scripts/model_reliability/classify_disagreements.py --case lincoln
```

The command requires the normalized runs and `agreement-results.json` produced
by the ingestion and comparison stages. It writes only beneath
`cases/<case_id>/quality/model-reliability/comparisons/`:

- `disagreement-log.json`;
- `disagreement-log.csv`;
- `instability-report.md`.

Each substantive record identifies the case, source language, document,
cluster when stable, task layer, field, affected item and unit, model values,
optional reference value, agreement pattern, category, possible codebook
ambiguity, claim impact, human-review priority, and a bounded review question.

The taxonomy covers identification, lexical boundaries, semantic and
contextual rationales, CMT domains and clusters, violence and obligation
functions, agency and absence, confidence, invalid schemas, hallucinated IDs,
and reference challenges. Confidence differences below 0.10 are not promoted
to substantive instability.

Agreement patterns distinguish two-way, majority/minority, and multi-way
splits, missing-run coverage, invalid submissions, hallucinated identifiers,
and unanimous model divergence from the accepted reference. Each record groups
run IDs by canonical value so the pattern remains auditable. A unanimous
reference challenge is always high priority, but it is not an automatic
correction: shared model error remains possible.

Rejected submissions remain visible through their ingestion validation
reports. Unknown identifiers are classified as hallucination instability;
other contract violations are schema instability. They are reported separately
from valid-run field metrics.

The Markdown report summarizes instability by case, language, document,
cluster, task layer, category, and priority. It describes a multi-model stress
test, not human inter-annotator reliability, and cannot modify accepted
annotations.
