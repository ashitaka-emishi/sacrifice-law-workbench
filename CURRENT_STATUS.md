# Current Project Status

Last audited from local files on 2026-06-14.

This page tracks volatile project state. Keep stable orientation material in
`README.md`.

## Summary

The project is no longer just a scaffold. The four historical case corpora are
rights-reviewed, acquired, normalized, segmented, and pass corpus verification.
The metaphor workflow now has a strict MIPVU identification layer before
CMT/Koenigsberg interpretation.

The main remaining gap before v1 is annotation: Lincoln now has generated
MIPVU lexical-unit worklists, but lexical decisions are still pending and no
`cases/*/corpus/annotated/*_annotated.json` files are present yet. Concordance
and analysis artifacts remain structural rather than evidence-backed findings.

## Case State

| Area | Current state |
|---|---|
| Lincoln | 3 manifest documents; corpus verification passes 3/3; normalized, segmented, and MIPVU worklisted. |
| American Revolution | 9 manifest documents; corpus verification passes 9/9; normalized and segmented. |
| Napoleon | 10 manifest bulletins; corpus verification passes 10/10; normalized and segmented from Gallica OCR. |
| Hitler | 8 manifest documents; corpus verification passes 8/8; normalized and segmented; actual source URLs are recorded in manifest and derived corpus metadata. |
| Cross-case | Synthesis, mapping, and validation scaffolds exist under `cases/x-case/`; findings remain draft until annotations exist. |

## Checks Run

Corpus verification passes for all four historical cases:

```bash
python3 scripts/verify-corpus.py --case lincoln
python3 scripts/verify-corpus.py --case am-rev
python3 scripts/verify-corpus.py --case napoleon
python3 scripts/verify-corpus.py --case hitler
```

JSON validation passes:

```bash
python3 scripts/validate-json.py
```

Lincoln MIPVU worklist generation passes:

```bash
python3 scripts/generate-mipvu-worklist.py --case lincoln
```

## Known Blockers

- Complete source-language MIPVU lexical-unit decisions for generated worklists.
- Produce first-pass CMT/Koenigsberg annotations under `cases/*/corpus/annotated/`.
- Rebuild concordance and analysis artifacts after annotation.
- Promote only validated, traceable claims from draft to reviewed or finding
  status.

## Status Page Generation

`scripts/generate-project-status.py` generates `project-status.qmd` from the
status JSON files and corpus artifact counts:

```bash
python3 scripts/generate-project-status.py
```

The generated page is useful for local status inspection. This hand-maintained
page records the audit notes and unresolved decisions that the generator cannot
infer.
