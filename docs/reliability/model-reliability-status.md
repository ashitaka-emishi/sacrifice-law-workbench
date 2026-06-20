# Model Reliability Validation and Status

`npm run validate` validates model-reliability artifacts whenever they are
present. Checks include JSON schemas, packet and prompt hashes, packet item IDs,
submission registrations and validation reports, normalized run IDs and packet
provenance, disagreement logs, review-queue coverage, and consensus-report
consistency. Cases with no model-reliability artifacts remain valid.

`npm run status` writes
`cases/<case_id>/quality/model-reliability/status.json` and includes the state
and warnings in `project-status.qmd`. States are:

- `absent`: no model-reliability workflow artifacts exist;
- `designed`: a validated sample and deterministic packets exist, with no
  submissions;
- `partial`: execution started, but fewer than two runs or downstream outputs
  are incomplete;
- `invalid`: a present artifact, hash, identifier, registration, or submission
  fails validation;
- `complete`: at least two validated runs and every comparison, disagreement,
  queue, and report artifact are present and consistent.

Absent submissions are an expected warning rather than a validation or
rendering failure. `npm run pipeline` and Quarto therefore continue while
refreshing packets for cases with approved samples and surfacing the warning on
the generated status page. Invalid present artifacts remain errors and cannot
be silently treated as absent.

Case status and milestone completion are related but distinct. `complete`
status confirms a valid artifact chain. The final
[completion checklist](model-reliability-completion-checklist.md) additionally
requires documentation, protected-authority checks, and successful status,
validation, pipeline, and Quarto commands.
