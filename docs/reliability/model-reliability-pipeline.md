# Multi-Model Reliability Pipeline Commands

`scripts/model_reliability/pipeline.py` exposes every reliability stage through
one Python-first command surface. All stages operate on manually supplied files;
none requires an API key or calls a model provider.

```bash
python3 scripts/model_reliability/pipeline.py packets --case lincoln
python3 scripts/model_reliability/pipeline.py ingest --case lincoln \
  --json /path/to/submission.json
python3 scripts/model_reliability/pipeline.py compare --case lincoln
python3 scripts/model_reliability/pipeline.py disagreements --case lincoln
python3 scripts/model_reliability/pipeline.py review-queue --case lincoln
python3 scripts/model_reliability/pipeline.py report --case lincoln
```

CSV ingestion accepts the same paired files as the dedicated ingestion tool:

```bash
python3 scripts/model_reliability/pipeline.py ingest --case lincoln \
  --metadata-csv /path/to/metadata.csv \
  --items-csv /path/to/items.csv
```

The end-to-end command regenerates deterministic packets and then runs
comparison, disagreement classification, queue generation, and reporting when
at least two validated runs are available:

```bash
python3 scripts/model_reliability/pipeline.py run --case lincoln
```

With no valid submissions, or only one valid run, `run` exits successfully and
prints a clear warning that downstream stages were skipped. This is an expected
workflow state: packets can be prepared before external model review occurs.
Malformed normalized artifacts still fail rather than being mistaken for an
empty submission state.

Equivalent npm commands are available:

```bash
npm run model-reliability -- run --case lincoln
npm run model-reliability:packets -- --case lincoln
npm run model-reliability:ingest -- --case lincoln --json /path/to/submission.json
npm run model-reliability:run -- --case lincoln
```

Every command writes only beneath
`cases/<case_id>/quality/model-reliability/`. Accepted metadata, corpus,
annotation, analysis, existing human-reliability, and publication artifacts are
read-only inputs.
