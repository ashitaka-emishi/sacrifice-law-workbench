# Human Adjudication Ingestion

`scripts/human_reliability/ingest_adjudication.py` validates one JSON
adjudication submission against the #86 contract and the exact frozen #85
queue:

```bash
npm run human-reliability:adjudicate -- \
  --case lincoln \
  --cohort lincoln-en-cmt \
  --cohort-version 1.0.0 \
  --json /secure/adjudication-submission.json
```

## Immutable registration

Input bytes receive a deterministic `adjudication-registration-*` ID and are
stored read-only beneath
`adjudication/decisions/raw/<registration_id>/adjudication.json`. Re-ingesting
identical bytes is idempotent and verifies the stored bytes. Every attempt,
including invalid attempts, remains in `adjudication-register.json` with a
JSON/Markdown validation report.

Only one valid submission may govern a frozen queue digest. A corrected
submission may follow an invalid attempt, but a second valid decision set for
the same queue is rejected rather than silently superseding the first.

## Queue and decision reconciliation

Validation checks:

- case, cohort, language, layer, queue source, digest, schema, generator,
  generator hash, and code revision;
- every stable queue ID exactly once, with matching disagreement, item,
  reference, unit, and field identities;
- unique adjudication, queue, evidence, claim, and correction-candidate IDs;
- adjudicator membership declarations against the approved cohort;
- status-specific values, selected coder/reference basis, controlled
  vocabularies, bounded confidence, and nontrivial rationales;
- exact affected-claim and affected-dimension coverage from the queue; and
- correction targets against the queue reference ID, field, current reference
  value, adjudicated value, and case namespace.

Invalid submissions are preserved and reported but never enter normalized
results.

## Normalized results and unresolved cases

Valid decisions are joined to their complete queue entries in
`adjudication/results/<cohort>-<version>/adjudication-results.json`. Original
coder values, reference summaries, model summaries, source context, priority,
and the adjudicator's decision remain separately recoverable.

`deferred` and `unresolved` decisions remain first-class normalized results.
They set the cohort adjudication state to `unresolved`; ingestion never fills a
missing value from a coder majority, reference match, or model summary.

## Dedicated correction review layer

Only schema-valid `candidate` records are copied into
`correction-candidates/<cohort>-<version>/correction-candidates.json` and CSV.
The layer is explicitly review-only:

- `promotion_permitted` is false;
- `promotion_status` remains `pending_separate_authorization`;
- `promotion_id` remains null; and
- `direct_write_permitted` remains false.

The command writes only below `quality/human-reliability/`. It does not open
accepted annotations, corpus files, analysis artifacts, metadata, claims, or
publication files for writing. Correction promotion remains a separate,
authorized workflow.

Adjudication evidence may reproduce source-derived material and inherits the
approved cohort's `repository_allowed` or `local_only` policy. Local-only case
subtrees must remain gitignored.
