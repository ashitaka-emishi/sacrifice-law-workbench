# Human Coder Disagreement Classification

`scripts/human_reliability/classify_disagreements.py` converts the detailed
coder-pair patterns from the reference-comparison stage into a neutral,
schema-validated adjudication input:

```bash
npm run human-reliability:disagreements -- \
  --case lincoln \
  --cohort lincoln-en-cmt \
  --cohort-version 1.0.0
```

The command requires matching `human-agreement.json` and
`reference-comparison.json` artifacts beneath the cohort comparison directory.
It validates both schemas, confirms that their cohort identity and immutable
input-run provenance agree, rejects stale upstream generator hashes, and
verifies the sample against the approved hash in the packet manifest.

Outputs are written beside those inputs:

- `disagreement-log.json`, validated by
  `schemas/human-reliability/disagreement-log-schema.json`; and
- `disagreement-log.csv`, a flattened coordinator/adjudicator view.

## Substantive records

Coder splits, uncertain-versus-confident patterns, and shared coder challenges
to an available reference become disagreement records. Agreement with a
reference and equal coder values where no reference is available do not.
Shared divergence from a reference is classified as a `reference_challenge`:
neither the shared coder value nor the reference is presumed correct.

Every record retains both pseudonymous coder IDs and values, the reference
value and authority when available, the originating #83 pattern, and a stable
ID. Field categories cover identification, lexical boundaries, semantics,
domains, clusters, interpretation, violence/obligation, agency/absence,
confidence/uncertainty, and scope disposition. Unknown fields fail closed
instead of falling into a generic category.

Confidence deltas below `0.10` remain visible in the upstream metric artifact
but are not promoted to substantive item-level disagreements.

## Risk and priority

The approved sample manifest contributes design roles, declared provenance
risks, and predeclared claim impact. Language-sensitive fields receive a
material source-language flag; a declared provenance risk escalates that flag
to high. High-impact claims, shared reference challenges, provenance-sensitive
language questions, and three-position splits receive high adjudication
priority.

`possible_codebook_ambiguity` is a review flag, not a diagnosis. It is raised
only from explicit sample ambiguity/rival-control roles or observable patterns
such as uncertainty splits, qualitative disagreements, and three-position
splits. Its reasons remain attached to the record.

## Coordinator-held samples

Some approved sample manifests are intentionally local-only because their
selection metadata is coordinator-held or source-restricted. If the manifest
is not present beneath `quality/human-reliability/samples/`, provide it without
copying it into the repository:

```bash
npm run human-reliability:disagreements -- \
  --case hitler \
  --cohort <cohort-id> \
  --cohort-version <version> \
  --sample-manifest /secure/coordinator/sample-manifest.json
```

The output records `coordinator://sample-manifest` plus its SHA-256 digest; it
does not disclose the external path or reproduce source text. The classifier
writes only below the cohort comparison directory and never modifies accepted
annotations, source corpora, submissions, or upstream comparison artifacts.
