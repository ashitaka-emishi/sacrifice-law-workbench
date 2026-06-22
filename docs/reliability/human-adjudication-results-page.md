# Human Adjudication Results Page

`scripts/human_reliability/generate_adjudication_results_page.py` generates
`human-adjudication-results.qmd` from approved cohort manifests, normalized
adjudication results, and dedicated correction-candidate artifacts.

Run:

```bash
npm run human-reliability:adjudication-results
```

The page reports:

- cohort, source-language, task-layer, and execution state;
- accepted, rejected, deferred, and unresolved outcomes;
- codebook and recoding implications;
- affected-claim dispositions and follow-up requirements; and
- correction-candidate counts and their unpromoted authority state.

The page never reproduces source text, adjudicated values, rationales, evidence,
coder values, or reference values. For `local_only` cohorts it also suppresses
all item-level decision metadata and exposes aggregate counts only.

Correction candidates remain proposals beneath the dedicated review layer.
Rendering a candidate cannot assign a promotion ID, authorize a direct write,
or alter a canonical corpus, analysis, metadata, claim, or publication
artifact.
