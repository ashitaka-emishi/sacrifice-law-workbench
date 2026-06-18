# Model Reliability Submission Ingestion

`scripts/model_reliability/ingest_submission.py` registers one manual JSON or
two-file CSV submission, validates it against the exact blind packet, and writes
only beneath `cases/<case_id>/quality/model-reliability/`.

Install the repository's Python dependencies with `pip install -r requirements.txt`
before running the command.

## Inputs

Native JSON uses `submission-schema.json` directly:

```bash
python3 scripts/model_reliability/ingest_submission.py \
  --case lincoln --json /path/to/submission.json
```

CSV transport uses one metadata row and one or more item rows as defined by
`submission-csv-contract.json`:

```bash
python3 scripts/model_reliability/ingest_submission.py \
  --case lincoln \
  --metadata-csv /path/to/metadata.csv \
  --items-csv /path/to/items.csv
```

JSON-valued CSV cells contain valid compact JSON. Invalid cells and rows remain
visible in the validation report; they are never silently omitted.

## Validation and outputs

Before registration, ingestion verifies the packet manifest hash, every payload
and prompt hash, and the prompt-to-task-layer binding. It then checks submission
schema, run metadata, packet and prompt identity, controlled vocabularies,
document/sentence/span/lexical-unit IDs, source-field alignment, duplicate span
sets, and complete coverage of the selected task-layer packet.

Exact source bytes are stored immutably under `submissions/raw/<registration>/`.
The submission register records valid and invalid attempts. Valid submissions
also enter `normalized/normalized-runs.json`; invalid submissions never do.
Machine-readable and Markdown reports preserve every parseable input row and
list all detected violations. Re-ingesting identical bytes is idempotent.

Inputs that appear to contain credentials or account identifiers are rejected
before any raw bytes are stored. No command writes to metadata, corpus, analysis,
existing reliability, review-packet, or publication paths.

## Rights-safe tests

The committed synthetic fixture under `test/fixtures/model-reliability/`
contains an invented French sentence, deterministic packets, valid JSON and CSV
submissions, named invalid submissions, and two controlled comparison runs. It
does not require project corpora or external APIs.

```bash
pip install -r requirements.txt
npm run test:model-reliability
```
