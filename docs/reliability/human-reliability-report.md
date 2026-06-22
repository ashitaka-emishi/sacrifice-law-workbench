# Human Reliability Report Generation

`scripts/human_reliability/generate_report.py` produces a cohort-scoped,
publication-ready JSON and Markdown report from the human reliability artifact
chain.

Run:

```bash
python3 scripts/human_reliability/generate_report.py \
  --case <case_id> \
  --cohort <cohort_id> \
  --cohort-version <version>
```

The command writes:

```text
cases/<case_id>/quality/human-reliability/comparisons/
  <cohort_id>-<cohort_version>/
    human-reliability-report.json
    human-reliability-report.md
```

The JSON output conforms to
`schemas/human-reliability/human-reliability-report-schema.json`.

## Honest execution states

- `designed` means the approved cohort, sample, and blind packet exist but no
  valid primary-coder ingestion has begun.
- `partial` means ingestion or the required pre-adjudication analysis chain is
  incomplete.
- `complete` means ingestion is complete and the cohort has validated
  human-human agreement, coder-to-reference comparison, and disagreement
  classification artifacts.

Adjudication is reported separately and is not required for the pre-adjudication
report to be complete. Missing metrics, reference fields, disagreements, or
adjudication are never rendered as evidence of agreement.

## Reporting boundaries

The report preserves training and calibration versions, blindness and AI-use
rules, sample and exclusion counts, coder completion, field-level agreement,
reference alignment, disagreements, adjudication status, correction-candidate
counts, and exact case/language/layer/cohort scope.

It emits no pooled or project-wide reliability score. Human-human agreement is
kept separate from reference comparison. Adjudication does not replace the
original coder-pair metrics, and correction candidates do not authorize edits
to accepted annotations.
