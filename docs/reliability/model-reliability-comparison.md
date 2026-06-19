# Model Reliability Agreement Diagnostics

`scripts/model_reliability/compare_runs.py` compares validated normalized model
runs without treating agreement as evidence that an annotation is correct.
It writes:

- `comparisons/agreement-results.json`, the complete machine-readable result;
- `comparisons/agreement-summary.csv`, a flat review and reporting view.

Run it after at least two comparable submissions have been ingested:

```bash
python3 scripts/model_reliability/compare_runs.py --case lincoln
```

The output keeps two diagnostic families separate:

- model-vs-model stability for each run pair;
- model-vs-reference divergence for each run.

Every summary is stratified by case, source language, document, task layer,
field, and run or run pair. Case-wide rows use a null `document_id`; document
rows retain the source document ID. The comparator refuses to pool source
languages.

Nominal fields report observed agreement. Cohen's kappa is limited to
closed-vocabulary judgments, and is included only when at least two
observations exist and expected agreement is not degenerate. Open-ended
identification rationales and CMT labels retain exact agreement without chance
correction. Proposed lexical boundaries use character-span Jaccard overlap;
set-valued CMT and agency fields also use Jaccard overlap. Confidence reports
mean absolute difference. Sparse, absent, and mathematically undefined values
remain in the output with `status: "undefined"` and a reason.

The accepted MIPVU layer supplies identification and lexical-boundary
references. Accepted annotation instances supply available CMT fields and
reference confidence. Interpretive, agency, or absence reference fields that
do not exist in accepted artifacts are reported with zero comparable
observations rather than inferred. Model-vs-model diagnostics still report
those fields when submitted by both runs.

The comparator reads accepted artifacts but writes only below
`cases/<case_id>/quality/model-reliability/`.
