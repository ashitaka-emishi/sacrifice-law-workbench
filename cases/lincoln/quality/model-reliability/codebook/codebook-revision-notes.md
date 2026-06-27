# Codebook Revision Notes: lincoln

> Human-governed methodological notes only. Model agreement is not evidence,
> these recommendations do not adjudicate review items, and no entry changes an
> accepted annotation retroactively.

## Summary

| Recommendations | Accepted | Rejected | Deferred | Stable categories | Ambiguous instructions | Common model errors | Multilingual problems |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 | 0 | 0 | 12 | 1 | 11 | 0 | 0 |

All generated recommendations default to **deferred**. Accepted and rejected
statuses require an explicit human decision register with a reviewer and
rationale. Accepted recommendations authorize a future codebook-edit workflow;
they do not themselves edit the codebook or prior decisions.

## Accepted recommendations

None.
## Rejected recommendations

None.
## Deferred recommendations

### `codebook-rec-bb05431c881b` — `cmt.cluster_id`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 4 queued `reference-challenge` item(s) affect `cmt.cluster_id` in `en`.
- Proposed change: Review the reference and codebook wording independently; do not adopt the model value by vote.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-1c1d7d367726` — `cmt.conceptual_metaphor`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 7 queued `semantic-instability` item(s) affect `cmt.conceptual_metaphor` in `en`.
- Proposed change: Clarify the decision rule for `cmt.conceptual_metaphor` with contrastive examples.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-44d3f615fe5e` — `cmt.entailments`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 7 queued `semantic-instability` item(s) affect `cmt.entailments` in `en`.
- Proposed change: Clarify the decision rule for `cmt.entailments` with contrastive examples.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-7c2926693152` — `cmt.source_domain_primary`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 2 queued `domain-instability` item(s) affect `cmt.source_domain_primary` in `en`.
- Proposed change: Clarify domain and cluster distinctions with contrastive mapping examples.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-c035eb0400cd` — `cmt.source_domain_primary`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 3 queued `reference-challenge` item(s) affect `cmt.source_domain_primary` in `en`.
- Proposed change: Review the reference and codebook wording independently; do not adopt the model value by vote.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-8efcb632c3ca` — `cmt.source_domain_secondary`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 6 queued `domain-instability` item(s) affect `cmt.source_domain_secondary` in `en`.
- Proposed change: Clarify domain and cluster distinctions with contrastive mapping examples.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-a7c275633158` — `cmt.source_domain_secondary`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 1 queued `reference-challenge` item(s) affect `cmt.source_domain_secondary` in `en`.
- Proposed change: Review the reference and codebook wording independently; do not adopt the model value by vote.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-1aff00c39134` — `cmt.target_domain`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 3 queued `reference-challenge` item(s) affect `cmt.target_domain` in `en`.
- Proposed change: Review the reference and codebook wording independently; do not adopt the model value by vote.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-ce1e63f5bbd8` — `cmt.target_domain`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 2 queued `target-domain-instability` item(s) affect `cmt.target_domain` in `en`.
- Proposed change: Clarify domain and cluster distinctions with contrastive mapping examples.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-39e5d178f21b` — `confidence`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 1 queued `confidence-instability` item(s) affect `confidence` in `en`.
- Proposed change: Add confidence anchors and examples for adjacent confidence levels.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-b4281c87be86` — `uncertainty.status`

- Finding: `ambiguous-instruction`
- Layer / language: `cmt` / `en`
- Observation: 1 queued `context-instability` item(s) affect `uncertainty.status` in `en`.
- Proposed change: Clarify the decision rule for `uncertainty.status` with contrastive examples.
- Training/calibration use: Use the reviewed examples as a contrastive calibration set; retain source language and uncertainty notes.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`

### `codebook-rec-5eb2c5b87e2e` — `cmt.cluster_id`

- Finding: `stable-category`
- Layer / language: `cmt` / `en`
- Observation: All defined model-pair diagnostics were stable for `cmt.cluster_id`.
- Proposed change: Retain the current rule for now and preserve this field as a positive calibration example.
- Training/calibration use: Use as a stable positive example, while preserving the original source and task context.
- Human decision rationale: Awaiting explicit human review.
- Reviewer: `not assigned`
