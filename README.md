# The Sacrifice Law Workbench

A comparative research workbench for assessing evidentiary support for
Koenigsberg's Law of Sacrifice.

**[View the research site ->](https://ashitaka-emishi.github.io/sacrifice-law-workbench/)** - a browsable HTML version of the workbench, including methodology
documentation, corpus and case materials, validation artifacts, and cross-case
synthesis. The site is rebuilt automatically when changes land on `master`.

A reproducible VSCode/Codex-ready research workbench for studying Richard A.
Koenigsberg's Law of Sacrifice through case-based corpus work, Conceptual
Metaphor Theory, LCC-style metaphor analysis, and cross-case synthesis.

This repository is meant to be an auditable research system: sources move
through rights review, manifest registration, acquisition, verification,
normalization, segmentation, annotation, concordance, analysis, validation, and
public Quarto artifacts.

## Central Research Question

> To what degree do recurring metaphor systems in leader-centered political
> corpora, when compared with historically documented practices of mobilization,
> killing, dying, purification, and enemy destruction, support, complicate, or
> limit Koenigsberg's Law of Sacrifice, the body-politic corollary, and the
> construction of enemies as death across the initial pilot cases defined in the
> case-selection protocol?

The project assesses evidentiary support rather than claiming proof. Case-level
findings should be allowed to support, complicate, limit, revise, or fail to
support Koenigsberg's Law.

## Current Status

The README is intentionally stable and does not track live corpus counts,
validation state, or open blockers.

For the current project snapshot, see [CURRENT_STATUS.md](CURRENT_STATUS.md).
For generated status output, see [project-status.qmd](project-status.qmd).

## Repository Shape

- `cases/<case>/metadata/` contains document manifests and source registries.
- `cases/<case>/corpus/raw/` contains acquired raw text, where rights permit.
- `cases/<case>/corpus/text/` contains normalized Markdown corpus files.
- `cases/<case>/corpus/segmented/` contains sentence-level JSON.
- `cases/<case>/corpus/mipvu/` contains source-language MIPVU lexical-unit
  worklists and decisions.
- `cases/<case>/corpus/annotated/` is the expected location for metaphor
  annotation JSON.
- `cases/<case>/analysis/` contains generated concordance and case-analysis
  artifacts.
- `cases/x-case/` contains cross-case inputs, mappings, synthesis, and
  validation artifacts.
- `scripts/` contains acquisition, verification, normalization, segmentation,
  analysis, synthesis, validation, and site-status helpers.
- `schemas/` contains JSON contracts for manifests and pipeline artifacts.
- `prompts/` contains reusable research prompts.
- Top-level `.qmd` and `.md` files define the public Quarto site.

## Pipeline

The core workflow is manifest-driven:

```text
source registry -> document manifest -> raw corpus -> normalized text
  -> segmented JSON -> MIPVU JSON -> annotated JSON -> concordance -> analysis
  -> x-case synthesis -> validation/public artifacts
```

The downstream analysis stages are intentionally rebuildable from file-based
artifacts. LangGraph is a future orchestration option, not a requirement for
the current workbench.

## Core Commands

Run commands from the repository root.

```bash
npm run status
npm run validate
npm run rebuild:all
npm run xcase
quarto render
```

Useful case-local commands:

```bash
python3 scripts/verify-corpus.py --case <case-id>
python3 scripts/run-case-pipeline.py --case <case-id>
python3 scripts/normalize-texts.py --case <case-id>
python3 scripts/segment-texts.py --case <case-id>
python3 scripts/generate-mipvu-worklist.py --case <case-id>
```

## Corpus Acquisition

Corpus acquisition is rights-gated and manifest-driven.

Before copying, downloading, or extracting any text into
`cases/*/corpus/raw/`, complete the rights/licensing review described in
[CORPUS_RIGHTS_POLICY.md](CORPUS_RIGHTS_POLICY.md).

Use the acquisition status report before fetching:

```bash
python3 scripts/acquire-sources.py --case <case-id>
```

Use the direct fetcher for supported public or locally allowed sources:

```bash
python3 scripts/fetch-corpus.py --case <case-id>
python3 scripts/fetch-corpus.py --doc <document-id>
python3 scripts/fetch-corpus.py --dry-run --json
```

`scripts/fetch-corpus.py` handles Project Gutenberg, National Archives
Declaration text, Gallica OCR when directly accessible, and Archive.org djvu
OCR extraction for configured sources.

Some sources remain browser-assisted, CAPTCHA-gated, or local-only:

- `/corpus-download` routes to the appropriate source-specific workflow.
- `/gallica-download` handles Gallica fallback work, including manual
  full-volume `Texte (TXT)` acquisition and local extraction.
- `/founders-download` handles JavaScript-rendered Founders Online documents.
- `/ifz-download` handles local German-source extraction workflows.

After any raw corpus file is placed or refreshed, verify before normalization:

```bash
python3 scripts/verify-corpus.py --case <case-id>
```

## Research Integrity

- Separate direct evidence, interpretation, inference, speculation, and open
  questions.
- Preserve source-to-claim traceability from public claims back to manifests,
  source records, annotations, concordances, analysis files, or validation
  artifacts.
- Treat starter clusters as hypotheses until annotation and validation support
  them.
- Keep translation, OCR, source-selection, and rights limitations visible.
- Do not present stub or draft artifacts as findings.

## Site

The public site is rendered with Quarto:

```bash
quarto render
```

GitHub Actions renders and deploys the site to
<https://ashitaka-emishi.github.io/sacrifice-law-workbench/>. The research
pipeline itself is local and file-based.
