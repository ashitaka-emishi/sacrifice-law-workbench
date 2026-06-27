# External Model Review Procedures

Use this guide to run a blind packet manually in an external model system and
return the result to the workbench. No API key or programming is required.
Complete one model system and one task layer at a time.

If an API-based fresh session is appropriate for the selected source rights,
`scripts/model_reliability/run_external_model.py` can perform the same blind
handoff for OpenAI or Anthropic Claude models. The runner writes local ignored
submission JSON under `reports/tmp/model-reliability/`, validates the returned
JSON, and still requires explicit ingestion as a separate step. Use the manual
procedure below when API transmission is not permitted, when a provider UI is
the reviewed execution environment, or when you need an operator-controlled
format repair.

External model review is a diagnostic stress test. It is not human
inter-annotator reliability, human scholarly review, adjudication, or evidence
for a historical or interpretive claim. A model response can create a review
candidate; it cannot change an accepted annotation.

## Before starting

1. Install the repository dependencies with `pip install -r requirements.txt`.
2. Choose the case, model system, and one task layer: `identification`, `cmt`,
   or `interpretation`.
3. Confirm that the case packet directory contains a packet manifest, the
   layer's prompt, and the layer's JSONL payload:

   ```text
   cases/<case_id>/quality/model-reliability/packets/
     packet-manifest.json
     identification-prompt.md
     identification-packet.jsonl
     cmt-prompt.md
     cmt-packet.jsonl
     interpretation-prompt.md
     interpretive-packet.jsonl
   ```

4. Check each source document's rights and `git_tracking` status in
   `cases/<case_id>/metadata/document-manifest.json` or `source-registry.json`.
   Do not upload text to a hosted service unless third-party transmission is
   permitted. For local-only, restricted, metadata-only, or unresolved text,
   use an approved local model environment or do not run the review.

The packet manifest is the local source for `sample_id`, versions, packet and
prompt hashes, and code revision. Copy these values exactly; never calculate or
guess replacements.

## What to send

Start a new, empty model conversation for each model system, run, and task
layer. Send only:

- the matching `*-prompt.md` contents;
- every row in the matching `*-packet.jsonl` payload;
- a request to return one JSON envelope conforming to
  `schemas/model-reliability/submission-schema.json`, or the equivalent
  two-file CSV transport;
- a response template populated with packet and prompt identity from
  `packet-manifest.json`.

For JSON, request one raw JSON object with no commentary or Markdown fences.

Keep all packet rows in their original source language. An English gloss is an
aid only and must remain separate from `sentence_source_text`, lexical-unit
`source_text`, and the model's source-language decision.

## What to withhold

Do not send or reveal:

- accepted MIPVU, CMT, or interpretive annotations;
- sample labels such as negative control, ambiguous, or claim-relevant;
- human coder decisions, agreement results, adjudication logs, or review
  packets;
- earlier model responses, consensus reports, disagreement logs, or review
  queues;
- analysis files, support scores, synthesis conclusions, publication claims,
  or filenames and comments that imply an expected answer;
- API keys, access tokens, passwords, account or client identifiers, private
  URLs, or other credentials.

Use a fresh conversation with memory, retrieval, browsing, and repository
access disabled when the model interface permits. Do not correct or coach the
model after seeing an answer. If a response is malformed, request only a format
repair in the same run and preserve the model's decisions unchanged.

## Record the run

The submission envelope needs a unique `submission_id`, and its `run` object
needs a unique opaque `run_id`. Record:

- `provider`, `model`, and the exact `model_version` when exposed;
- `completed_at` as an ISO 8601 UTC timestamp;
- declared `language_capabilities` relevant to the packet;
- non-secret generation settings such as temperature, top-p, seed, reasoning
  mode, and whether tools, browsing, retrieval, or memory were disabled.

Do not put credentials, account IDs, session URLs, or personal identifiers in
`settings`. Ingestion rejects files that appear to contain such values.
`code_revision` describes the packet generator revision from the manifest, not
the external model version.

Recommended working filenames are
`<provider>-<model>-<layer>-<run_id>.json`, or matching `-metadata.csv` and
`-items.csv` files. Filenames are for operator convenience; identity comes from
the file contents.

## Minimal valid JSON example

This synthetic CMT example is schema-valid for the committed `demo` fixture.
For a real run, replace all fixture identity, source, and decision values with
the exact assigned packet and the model's output. Include every item from the
chosen layer; partial coverage is invalid.

```json
{
  "schema_version": "1.0.0",
  "submission_id": "fixture-submission-valid-json",
  "case_id": "demo",
  "sample_id": "demo-multi-model-v1",
  "sample_version": "1.0.0",
  "packet_id": "demo-multi-model-v1-packet",
  "packet_hash": "sha256:cd31a7819471631bea518e207275f6879dd24e461c57bc9e5ad386045acd636a",
  "prompt_id": "cmt-v1",
  "prompt_hash": "sha256:3454b00e86d116aba69979d668a7d74cc5ef0fe5deef1515e9832867588e3435",
  "source_language": "fr",
  "code_revision": "fixture-revision-v1",
  "run": {
    "run_id": "fixture-run-valid-json",
    "provider": "fixture-provider",
    "model": "fixture-model",
    "model_version": "fixture-v1",
    "completed_at": "2026-06-18T12:00:00Z",
    "language_capabilities": ["fr", "en"],
    "settings": {"temperature": 0}
  },
  "items": [
    {
      "item_id": "demo-multi-model-v1-packet:cmt:demo-ann-001",
      "task_layer": "cmt",
      "case_id": "demo",
      "document_id": "demo-doc-001",
      "sentence_id": "demo-doc-001_s01_p01_s01",
      "span_ids": ["demo-ann-001"],
      "source_language": "fr",
      "sentence_source_text": "La cité porte l'espoir.",
      "sentence_gloss_en": "The city carries hope.",
      "lexical_units": [
        {
          "lexical_unit_id": "demo-doc-001_s01_p01_s01_lu002",
          "span_id": "demo-ann-001",
          "source_text": "porte",
          "gloss_en": "carries",
          "char_offset_start": 8,
          "char_offset_end": 13
        }
      ],
      "source_risk_flags": ["translation-check"],
      "cmt": {
        "source_domain_primary": "carrying",
        "source_domain_secondary": [],
        "target_domain": "hope",
        "conceptual_metaphor": "HOPE IS A CARRIED OBJECT",
        "entailments": ["hope can be borne by a collective"],
        "cluster_id": "demo-carrying-hope"
      },
      "confidence": 0.8,
      "uncertainty": {
        "status": "low",
        "note": "A conventional use of porter remains possible."
      },
      "rival_reading": "The verb may conventionalize support rather than evoke physical carrying.",
      "case_fields": {}
    }
  ]
}
```

The executable copy is
`test/fixtures/model-reliability/submissions/valid-cmt.json`.

## Minimal valid CSV example

CSV transport requires exactly one metadata row and at least one item row. Save
the following as two UTF-8, comma-delimited files with LF line endings. JSON
arrays and objects stay JSON-encoded inside their CSV cells; do not replace
them with delimiter-joined text.

`metadata.csv`:

```csv
schema_version,submission_id,case_id,sample_id,sample_version,packet_id,packet_hash,prompt_id,prompt_hash,source_language,code_revision,run_id,provider,model,model_version,completed_at,language_capabilities,settings
1.0.0,fixture-submission-valid-csv,demo,demo-multi-model-v1,1.0.0,demo-multi-model-v1-packet,sha256:cd31a7819471631bea518e207275f6879dd24e461c57bc9e5ad386045acd636a,cmt-v1,sha256:3454b00e86d116aba69979d668a7d74cc5ef0fe5deef1515e9832867588e3435,fr,fixture-revision-v1,fixture-run-valid-json-csv,fixture-provider,fixture-model,fixture-v1,2026-06-18T12:00:00Z,"[""fr"",""en""]","{""temperature"":0}"
```

`items.csv`:

```csv
item_id,task_layer,case_id,document_id,sentence_id,span_ids,source_language,sentence_source_text,sentence_gloss_en,lexical_units,source_risk_flags,identification,cmt,interpretation,confidence,uncertainty,rival_reading,case_fields
demo-multi-model-v1-packet:cmt:demo-ann-001,cmt,demo,demo-doc-001,demo-doc-001_s01_p01_s01,"[""demo-ann-001""]",fr,La cité porte l'espoir.,The city carries hope.,"[{""lexical_unit_id"":""demo-doc-001_s01_p01_s01_lu002"",""span_id"":""demo-ann-001"",""source_text"":""porte"",""gloss_en"":""carries"",""char_offset_start"":8,""char_offset_end"":13}]","[""translation-check""]",,"{""source_domain_primary"":""carrying"",""source_domain_secondary"":[],""target_domain"":""hope"",""conceptual_metaphor"":""HOPE IS A CARRIED OBJECT"",""entailments"":[""hope can be borne by a collective""],""cluster_id"":""demo-carrying-hope""}",,0.8,"{""status"":""low"",""note"":""A conventional use of porter remains possible.""}",The verb may conventionalize support rather than evoke physical carrying.,{}
```

Executable copies are under
`test/fixtures/model-reliability/submissions/valid-csv/`.

## Ingest the response

Do not edit accepted corpus, analysis, reliability, or publication files. Put
the returned file in a temporary or rights-appropriate local location and run
one of these commands from the repository root:

```bash
python3 scripts/model_reliability/pipeline.py ingest \
  --case <case_id> --json /path/to/submission.json
```

```bash
python3 scripts/model_reliability/pipeline.py ingest \
  --case <case_id> \
  --metadata-csv /path/to/metadata.csv \
  --items-csv /path/to/items.csv
```

Ingestion verifies schema, packet and prompt hashes, source fields, stable IDs,
controlled vocabularies, duplicate spans, and complete layer coverage. It
stores exact source bytes under a registration directory, writes a validation
report, and adds only valid runs to `normalized/normalized-runs.json`. Invalid
attempts remain auditable but do not enter comparisons. Re-ingesting identical
bytes is idempotent.

Read the reported errors and correct transport or transcription mistakes only.
Do not silently change a substantive model decision to make validation pass.
Common failures are a stale packet hash, a prompt from the wrong layer, omitted
items, changed source text or IDs, non-JSON CSV cells, uncontrolled vocabulary
values, mixed task layers, and credentials in settings.

After at least two comparable model-system submissions are valid, run:

```bash
python3 scripts/model_reliability/pipeline.py run --case <case_id>
```

This creates diagnostics and human review candidates only. Model agreement is
not adjudication, model disagreement does not invalidate the reference, and no
model-reliability command may overwrite accepted artifacts.

## Optional API runner

The optional runner uses exported environment variables or a local `.env` file
for credentials and does not serialize secrets into submissions. The repository
root `.env` file is ignored by git and must stay local:

```dotenv
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

Exported variables take precedence over `.env` values:

```bash
export OPENAI_API_KEY=...
npm run model-reliability:external-run -- \
  --case lincoln \
  --task-layer cmt \
  --provider openai \
  --model <model-name> \
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
  --setting temperature=0 \
  --setting max_tokens=12000
```

Use `--env-file /path/to/provider.env` for an alternate local dotenv file, or
`--no-env-file` when you want to require exported environment variables only.
Use `--api-key-env CUSTOM_KEY` when a provider key is stored under a different
environment/dotenv variable name.

The runner supplies no tools, browsing, retrieval, vector stores, repository
context, accepted annotations, prior outputs, review queues, analysis files, or
publication claims. Provider APIs do not expose the same user-interface memory
controls as chat products; the runner documents this by recording non-secret
settings that tools, browsing, retrieval, and memory were not supplied.
Never put API keys, account identifiers, session URLs, or personal identifiers
in `--setting`; settings are copied into non-secret run metadata.

Before calling a provider, inspect the exact payload with:

```bash
npm run model-reliability:external-run -- \
  --case lincoln \
  --task-layer cmt \
  --provider openai \
  --model <model-name> \
  --dry-run
```

If the returned JSON validates, ingest the local output path with
`pipeline.py ingest`. If validation fails, review the `.validation-errors.txt`
file. Only transport or formatting repairs may be requested; do not edit the
model's substantive decisions to make validation pass.

## Rights and availability after ingestion

Packet payloads and raw responses inherit the source text's storage rules.
Public-domain material may be committed only when its source registry permits
it. Responses reproducing local-only, restricted, or unresolved text must stay
local and untracked, even if aggregate diagnostics are publishable. Public
reporting should prefer stable IDs, aggregate measures, and short compliant
spans.

For governing contracts, see
[`model-reliability-submission-contract.md`](model-reliability-submission-contract.md),
[`model-reliability-ingestion.md`](model-reliability-ingestion.md),
[`model-reliability-governance.md`](model-reliability-governance.md), and the
project [`CORPUS_RIGHTS_POLICY.md`](../../CORPUS_RIGHTS_POLICY.md).
