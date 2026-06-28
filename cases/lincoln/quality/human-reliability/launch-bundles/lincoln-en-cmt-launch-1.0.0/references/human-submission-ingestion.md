# Human Coder Submission Ingestion

`scripts/human_reliability/ingest_submission.py` ingests completed JSON or
single-file CSV submissions defined by the
[human coder submission contract](human-coder-submission-contract.md). It does
not require real submissions to test: the regression suite generates invented
French packets and coder responses. Production cohorts remain honestly
`absent` or `partial` until qualified people submit work.

## Cohort authority

Every ingestion command requires an approved case-local cohort manifest that
conforms to `schemas/human-reliability/cohort-manifest-schema.json`. The
manifest binds:

- case, sample, packet, language, task layer, and codebook identity;
- training and calibration versions;
- assigned pseudonymous primary coders and the required coder count;
- whether AI assistance belongs to the declared design; and
- packet rights constraints and either `repository_allowed` or `local_only`
  storage.

The cohort carries a canonical approval hash computed with
`approval.manifest_sha256` set to null. The approval hash, referenced packet
manifest, and all packet payload hashes are verified before any submission
bytes are stored. Restricted or local-only packet constraints cannot be paired
with repository-allowed storage, and a `local_only` output path must actually
be ignored by Git in a repository checkout.

## Commands

Preflight a returned submission without writing registration, normalized, or
status artifacts:

```bash
npm run human-reliability:preflight -- \
  --case <case_id> \
  --cohort cases/<case_id>/quality/human-reliability/cohorts/<cohort>.json \
  --json <completed-submission.json>
```

For CSV preflight, replace `--json` with `--csv`. Add `--json-output` when the
coordinator needs a machine-readable report. Preflight validates the same
cohort, packet, schema, declaration, coder identity, controlled-vocabulary,
and row-level contract checks as ingestion, plus explicit checks for leaked
internal fields such as accepted labels, model outputs, adjudication fields, or
sample roles. It returns a nonzero exit status when the returned file is
invalid and leaves case status unchanged.

Ingest canonical JSON:

```bash
python3 scripts/human_reliability/ingest_submission.py \
  --case <case_id> \
  --cohort cases/<case_id>/quality/human-reliability/cohorts/<cohort>.json \
  --json <completed-submission.json>
```

Ingest the single-file spreadsheet transport:

```bash
python3 scripts/human_reliability/ingest_submission.py \
  --case <case_id> \
  --cohort cases/<case_id>/quality/human-reliability/cohorts/<cohort>.json \
  --csv <completed-submission.csv>
```

Create or refresh status before any submission exists:

```bash
python3 scripts/human_reliability/ingest_submission.py \
  --case <case_id> \
  --cohort cases/<case_id>/quality/human-reliability/cohorts/<cohort>.json \
  --status-only
```

## Preservation and validation

Raw input is identified by a deterministic hash, copied byte-for-byte to
`submissions/raw/<registration_id>/`, and made read-only. Re-ingesting identical
bytes is idempotent and verifies that the stored copy has not changed. Every
parseable JSON response or CSV row appears in its validation report, including
invalid and duplicate rows.

Validation covers:

- JSON Schema and CSV shape;
- repeated CSV metadata and layer-specific columns;
- cohort, packet, sample, codebook, training, calibration, and coder identity;
- packet hash, item IDs, document/sentence/span bindings, and exact lexical-unit
  coverage;
- controlled vocabularies and namespaced case extensions;
- duplicate item rows, submission IDs, and coder submissions;
- required conflict, qualification, independence, and assistance declarations;
- comment length and prohibited control characters; and
- packet rights and storage restrictions.

Only valid submissions enter `normalized/normalized-coder-runs.json`. Invalid
attempts remain in the immutable raw store, submission register, and
per-registration JSON/Markdown validation reports. A corrected attempt may
supersede an invalid attempt by the same coder for status purposes; history is
never deleted.

## Ingestion states

These states describe submission ingestion only, not the entire human
reliability pipeline:

| State | Meaning |
|---|---|
| `absent` | No submission attempt exists for the approved cohort. |
| `partial` | At least one valid distinct primary coder exists, but fewer than the declared requirement. |
| `invalid` | The latest effective attempt for at least one coder/identity fails validation. |
| `complete` | The declared minimum of distinct assigned primary coders has valid submissions. |

For the normal design, `complete` requires two independent qualified primary
coders. It authorizes later agreement computation; it does not imply that
agreement, reference comparison, adjudication, reporting, or publication work
is complete.
