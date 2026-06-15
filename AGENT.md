# Agent Instructions

This repository is The Sacrifice Law Workbench: a comparative research
workbench for assessing evidentiary support for Koenigsberg's Law of Sacrifice.
It studies the Law through case-based corpus work, Conceptual Metaphor Theory,
LCC-style metaphor analysis, historical corroboration, and cross-case
synthesis.

Treat V1 as a near-v1, rebuildable research system with a populated and
verified corpus layer but an unfinished annotation/findings layer. Some prompts,
schemas, and pipeline scripts remain provisional. Prefer strengthening
traceability and rights controls over presenting placeholder material as
finished analysis.

## Project Shape

- `README.md`, `PROJECT_BRIEF.md`, `methodology.qmd`, `validation-protocol.qmd`,
  and related top-level `.qmd` files define the public research narrative.
- `cases/<case>/` contains case-specific `config/`, `metadata/`, `status/`,
  `corpus/`, and generated `artifacts/qmd/` materials.
- `cases/x-case/` contains cross-case inputs, mappings, validation, support
  scoring, synthesis JSON, status, and generated public-facing Quarto
  artifacts.
- `prompts/` contains reusable research prompts. Many are draft scaffolds and
  should preserve source citation, evidence/inference/speculation boundaries,
  schema-shaped outputs, and traceability.
- `schemas/` defines JSON contracts. Some schemas are placeholders; expand
  them before relying on validation as a meaningful quality gate.
- `scripts/` contains rebuild, acquisition, annotation, normalization, status,
  and synthesis commands. Placeholder scripts should remain
  explicit file-based workflows unless the repo deliberately adopts LangGraph.
- `_quarto.yml`, `custom.scss`, and `.qmd` files define the Quarto site.

## Core Commands

Run commands from the repository root.

```bash
python scripts/generate-project-status.py
quarto render
```

If `python` is unavailable in the local shell, use `python3` for the same
scripts.

Useful package scripts:

```bash
npm run status
npm run site
npm run rebuild:all
npm run xcase
```

Useful corpus acquisition commands:

```bash
python3 scripts/acquire-sources.py --case <case-id>
python3 scripts/fetch-corpus.py --case <case-id>
python3 scripts/fetch-corpus.py --doc <document-id>
python3 scripts/verify-corpus.py --case <case-id>
```

Python dependencies are listed in `requirements.txt`. Do not add heavy workflow
frameworks or runtime services unless the current task explicitly requires them.

## Research Integrity Rules

- Preserve the central research question: to what degree recurring metaphor
  systems in leader-centered political corpora, when compared with historically
  documented practices, support, complicate, or limit Koenigsberg's Law of
  Sacrifice, its body-politic corollary, and the construction of enemies as
  death.
- Separate direct evidence, interpretation, inference, speculation, and open
  questions. Do not flatten contested historical material into certainty.
- Maintain source-to-claim traceability. New claims should point back to source
  registry entries, manifests, annotations, support ratings, historical
  corroboration notes, or validation artifacts.
- Keep case-level work case-local when possible, then feed cross-case synthesis
  through `cases/x-case/` inputs, mappings, validation, support scoring,
  historical corroboration, and synthesis artifacts.
- Update `OPEN_DECISIONS.md` when a task creates or resolves a deferred research
  decision.

## Corpus Rights And Source Handling

Read `CORPUS_RIGHTS_POLICY.md` before adding or moving corpus text.

- Do not copy text into `cases/*/corpus/raw/` until the source passes the
  rights/licensing review gate.
- Preserve source registry metadata: URL, archive, citation, rights status,
  acquisition instructions, expected local path, rights rationale, and Git
  tracking status.
- Prefer `scripts/fetch-corpus.py` for supported curl-accessible sources. Use
  `/corpus-download` and the source-specific download skills for
  browser-rendered, CAPTCHA-gated, or local-only sources.
- After placing any raw corpus file, run `python3 scripts/verify-corpus.py
  --case <id>` and confirm PASS before proceeding to normalization. The verifier
  checks file presence, minimum word count, and required anchor phrases defined
  in each document's `verification` block in `document-manifest.json`.
- Respect the storage policy: use committed raw texts only when rights permit;
  otherwise use gitignored local files, metadata-only records, or unavailable
  records.
- Avoid OCR unless no clean public-domain or open-access source exists and the
  source is analytically important enough to justify quality-control work.
- Do not paste long copyrighted excerpts into prompts, docs, tests, or generated
  artifacts. Prefer citations, metadata, short compliant quotations, and
  paraphrase.

## Editing Guidance

- Prefer small, explicit edits that match the existing workflow and directory
  layout.
- Keep durable pipeline state in JSON, YAML, Markdown, or Quarto files, not chat
  history or process memory.
- When adding pipeline stages, use manifest-driven inputs/outputs and update
  relevant status files or generation scripts.
- When modifying generated Quarto artifacts, check whether a script should be
  updated instead of hand-editing generated output.
- Use existing script patterns: repository root via `Path(__file__).resolve()`,
  UTF-8 reads/writes, JSON manifests, and simple CLI arguments.
- Keep public `.qmd` prose academically cautious and readable. Avoid overstating
  V1 readiness.
- Keep file paths stable. Downstream pages and manifests often depend on the
  current case/config/status/artifact structure.

## Validation Expectations

Choose validation proportional to the change.

- For status/site changes, run:

  ```bash
  python scripts/generate-project-status.py
  quarto render
  ```

- For Python script changes, run the specific script with a realistic case or
  input, then run the smallest broader rebuild command that covers the touched
  outputs.
- For schema changes, validate at least one representative existing JSON file
  against the changed schema when practical.
- For prompt changes, test the prompt against a realistic case or source
  scenario and check for citation, traceability, and evidence-boundary behavior.
- For research-question, methodology, synthesis, or support-scoring changes,
  check consistency with `PRIMARY_RESEARCH_QUESTION.md`,
  `validation-protocol.qmd`, and `PIPELINE-UPGRADE.md`; preserve the four
  support dimensions: sacred object, sacrificial body, enemy as death, and
  historical enactment/alignment.
- If a command cannot be run locally, state that clearly in the final response
  and explain the remaining risk.

## LangGraph Compatibility

V1 does not require LangGraph or LangChain. Preserve future compatibility by
keeping stages explicit, serializable, and resumable:

- case workflows should be able to become case subgraphs later;
- `x-case` synthesis should be able to become a synthesis subgraph later;
- human review gates should map to future interrupt/resume checkpoints;
- no critical state should exist only in memory.

## Final Response Style

When reporting work back to the user, include:

- files changed;
- commands run and whether they passed;
- any generated artifacts changed as a result;
- unresolved rights, source, validation, corroboration, support-scoring, or
  research-integrity risks.
