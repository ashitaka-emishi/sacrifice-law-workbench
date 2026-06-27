# Lincoln Fresh Model Diagnostics: Issue 157

Status: partial fresh-provider execution for the remaining Lincoln
model-reliability layers. These diagnostics are model behavior records, not
human reliability evidence, accepted annotations, adjudication decisions, or
scholarly proof.

## Executed subset

The fresh interpretation layer was completed and ingested for both configured
providers:

- `issue157-openai-interpretation-20260627`
  (`gpt-5.5-2026-04-23`);
- `issue157-anthropic-interpretation-20260627`
  (`claude-sonnet-4-6`).

Both runs used the committed blind Lincoln packet, disabled tools, browsing,
retrieval, and memory, and supplied no accepted annotations, prior model
outputs, human-reliability submissions, adjudication records, publication
claims, or repository-derived answers in the provider prompts. Both submissions
validated with zero ingestion errors and are included in the case-local
normalized run set.

## Identification attempts

The fresh identification layer was attempted for both configured providers but
was not ingested:

- the first OpenAI identification request timed out under the runner's previous
  180-second HTTP timeout;
- an OpenAI retry with a larger output cap returned parseable JSON but dropped
  required packet identity and lexical-unit span fields, so the runner wrote an
  ignored validation-error report and refused ingestion;
- the Anthropic identification request timed out under the previous timeout;
- the Anthropic retry with the longer timeout returned malformed JSON, so no
  submission was written or ingested.

Because no identification attempt produced a valid submission that preserved
the packet identity and source-span metadata, identification remains an
attempted but excluded subset for this issue. Invalid and malformed attempts
remain local ignored runner artifacts under `reports/tmp/model-reliability/`
and are not counted in agreement, disagreement, review-queue, consensus,
status, or completion artifacts.

## Downstream artifacts

After ingesting the two valid interpretation submissions, the downstream
Lincoln model-reliability artifacts were regenerated without updating accepted
annotations:

- normalized run and validation summaries;
- agreement metrics and disagreement logs;
- model review queue;
- consensus report and public results page;
- codebook revision notes;
- case-local status and completion checklist.

The case-local status is complete for the four valid runs now present in the
Lincoln model-reliability subtree. The completion checklist remains blocked on
the repository-validation bundle because the full `npm run pipeline` command
regenerates packet manifests against the current worktree revision during
execution, which would stale the fresh-provider submissions instead of
validating the committed packet they used.
