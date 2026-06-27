# Multi-Model Reliability Pipeline Commands

`scripts/model_reliability/pipeline.py` exposes every reliability stage through
one Python-first command surface. The core pipeline operates on manually
supplied files; it does not require an API key or call a model provider.
The optional external runner described below can call provider APIs to produce
those manually ingestible files.

```bash
python3 scripts/model_reliability/pipeline.py packets --case lincoln
python3 scripts/model_reliability/pipeline.py ingest --case lincoln \
  --json /path/to/submission.json
python3 scripts/model_reliability/pipeline.py compare --case lincoln
python3 scripts/model_reliability/pipeline.py disagreements --case lincoln
python3 scripts/model_reliability/pipeline.py review-queue --case lincoln
python3 scripts/model_reliability/pipeline.py report --case lincoln
python3 scripts/model_reliability/pipeline.py codebook-notes --case lincoln
```

CSV ingestion accepts the same paired files as the dedicated ingestion tool:

```bash
python3 scripts/model_reliability/pipeline.py ingest --case lincoln \
  --metadata-csv /path/to/metadata.csv \
  --items-csv /path/to/items.csv
```

The end-to-end command prepares deterministic packets and then runs comparison,
disagreement classification, queue generation, and reporting when at least two
validated runs are available. When valid normalized submissions already exist,
`run` preserves the active packet manifest and packet hash instead of
regenerating packet identity during a broad rebuild. It also generates
human-governed codebook revision notes after the report:

```bash
python3 scripts/model_reliability/pipeline.py run --case lincoln
```

Packet rotation is explicit. Use `--rotate-packets` only when reviewers should
receive a new packet identity and existing packet-bound submissions are expected
to be superseded or rejected as stale:

```bash
python3 scripts/model_reliability/pipeline.py run --case lincoln --rotate-packets
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
npm run model-reliability:completion -- --case lincoln
npm run model-reliability:external-run -- --case lincoln --task-layer cmt \
  --provider openai --model <model-name>
```

## Optional fresh-provider runner

`scripts/model_reliability/run_external_model.py` can run one existing blind
packet layer against a fresh OpenAI or Anthropic Claude API session and write
the returned submission JSON beneath ignored `reports/tmp/model-reliability/`.
It sends only the task prompt, matching JSONL packet payload, schema/format
instruction, and response template for the selected layer. It supplies no tool
definitions, retrieval, browsing, vector stores, repository context, accepted
annotations, prior model outputs, review queues, analysis files, or publication
claims.

Run a dry run first to inspect exactly what would be sent:

```bash
npm run model-reliability:external-run -- \
  --case lincoln \
  --task-layer cmt \
  --provider openai \
  --model <model-name> \
  --dry-run
```

Real provider calls read credentials from exported environment variables or
from a local `.env` file at the repository root. The `.env` file is ignored by
git and must stay local:

```dotenv
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

Exported environment variables take precedence over `.env` values:

```bash
export OPENAI_API_KEY=...
npm run model-reliability:external-run -- \
  --case lincoln \
  --task-layer cmt \
  --provider openai \
  --model <model-name> \
  --http-timeout 600 \
  --setting temperature=0 \
  --setting max_output_tokens=12000
```

```bash
export ANTHROPIC_API_KEY=...
npm run model-reliability:external-run -- \
  --case lincoln \
  --task-layer cmt \
  --provider anthropic \
  --model <model-name> \
  --http-timeout 600 \
  --setting temperature=0 \
  --setting max_tokens=12000
```

Use `--env-file /path/to/provider.env` for an alternate local dotenv file, or
`--no-env-file` to require exported environment variables only. The runner reads
only the requested key name, defaults to `OPENAI_API_KEY` or
`ANTHROPIC_API_KEY`, and still supports `--api-key-env CUSTOM_KEY`.
Use `--http-timeout <seconds>` for large packet layers whose provider response
may exceed the default 180-second HTTP read timeout.

The runner validates the returned JSON with the existing submission contract
and packet-alignment checks before reporting success. It does not ingest the
file automatically. After reviewing the local output path, ingest it explicitly:

```bash
npm run model-reliability:ingest -- --case lincoln --json reports/tmp/model-reliability/<submission>.json
```

Use `--mock-response /path/to/submission.json` for tests or rehearsals without
external API calls. Never place API keys, account identifiers, session URLs, or
personal identifiers in `--setting`; settings are copied into the submission
envelope as non-secret run metadata. The runner must not print, serialize, or
write provider credentials to prompts, dry-run templates, submissions,
validation reports, logs, or generated artifacts.

Every command writes only beneath
`cases/<case_id>/quality/model-reliability/`. Accepted metadata, corpus,
annotation, analysis, existing human-reliability, and publication artifacts are
read-only inputs.

## Final completion gate

After at least two validated runs and the full downstream artifact chain exist,
run:

```bash
npm run model-reliability:completion -- \
  --case lincoln --run-repository-validation --write
```

The gate verifies validated runs, layered metrics, disagreement logs, the
human-review queue, reports, documentation, protected-path authority, and the
four repository validation commands. It writes a blocked or complete checklist
beneath the case-local model-reliability subtree. See the
[completion checklist](model-reliability-completion-checklist.md) for the full
contract.
