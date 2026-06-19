# Model Reliability Correction Governance

Multi-model outputs are diagnostic suggestions. They never directly revise an
accepted MIPVU decision, annotation, analysis result, prior human-reliability
artifact, or publication claim.

## Four distinct stages

1. **Suggestion.** A disagreement becomes a pending review candidate in
   `cases/<case_id>/quality/model-reliability/review-queue/`. It records model
   values, the reference value, and a bounded question, but no accepted value.
2. **Adjudication.** A human reviews source context and the codebook through a
   separate human-governed workflow. Model consensus is not the adjudicator.
3. **Accepted correction.** An authorized human may make a deliberate,
   separately reviewed edit to a canonical artifact. No model-reliability
   command performs this step.
4. **Downstream regeneration.** Ordinary corpus, analysis, status, audit, and
   publication pipelines are rerun after the accepted correction.

## Enforced write boundary

All model-reliability outputs resolve beneath
`cases/<case_id>/quality/model-reliability/`. Review suggestions are further
restricted to the dedicated `review-queue/` candidate layer.

The following remain immutable during an end-to-end model-reliability command:

- `metadata/`, `corpus/`, and `analysis/`;
- every case-local `quality/` artifact outside `model-reliability/`, including
  prior reliability results, review packets, and adjudication logs;
- `publication/`.

The pipeline snapshots these protected paths before execution. If any stage
attempts a direct, traversal-based, or symlink-assisted write, original bytes
are restored and the command fails with the affected paths. Output helpers also
reject destinations outside the writable subtree before writing.
