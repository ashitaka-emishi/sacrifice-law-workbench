# Current Project Status

Last audited from local files on 2026-06-28.

This page tracks volatile project state. Keep stable orientation material in
`README.md`.

## Summary

The project is no longer just a scaffold. The four original historical case
corpora are rights-reviewed, acquired, normalized, segmented, and pass corpus
verification. They have functioned as the v1 working corpus, and the project
has now opened a controlled pre-v1 expansion window before publication-grade
reliability and claim promotion.

The metaphor workflow now has a strict MIPVU identification layer before
CMT/Koenigsberg interpretation.

The main remaining gap before publication-ready v1 is reliability and claim
promotion rather than original-corpus construction. All four original cases now
have Codex-assisted first-pass MIPVU lexical decisions. The expansion window has
added French Revolution and British World War I as draft corpora with manifests,
raw text, normalized text, segmentation, and MIPVU worklists, but no reviewed
annotations, support ratings, or reliability samples yet. Lincoln has a complete
model reliability workflow and designed human reliability cohorts, but required
human coder submissions are not complete. American Revolution, Napoleon, Hitler,
French Revolution, and British World War I model and human reliability workflows
remain absent or incomplete. First-pass CMT/Koenigsberg annotation artifacts are
present for much of the original corpus, but public support ratings and analysis
outputs remain draft until reliability, historical citation, and traceability
gates are satisfied.

## Case State

| Area | Current state |
|---|---|
| Lincoln | 3 manifest documents; corpus verification passes 3/3; normalized, segmented, and all 4,536 lexical units have Codex-assisted first-pass MIPVU decisions. Model reliability is complete. Human reliability cohorts are designed but await required primary coder submissions. |
| American Revolution | 9 manifest documents; corpus verification passes 9/9; normalized, segmented, and all 33,025 lexical units have Codex-assisted first-pass MIPVU decisions. Results remain provisional until independent human review. |
| Napoleon | 10 manifest bulletins; corpus verification passes 10/10; normalized, segmented from Gallica OCR, and all 23,005 lexical units have Codex-assisted first-pass source-language French MIPVU decisions. Results remain provisional until independent human review. |
| French Revolution | 2 manifest documents; corpus verification passes 2/2; normalized, segmented, and 11,905 lexical units have generated MIPVU worklists. No reviewed annotations, support rating, or reliability sample exists yet. |
| British World War I | 4 manifest documents; corpus verification passes 4/4; normalized, segmented, and 18,213 lexical units have generated MIPVU worklists. No reviewed annotations, support rating, or reliability sample exists yet. |
| Hitler | 8 manifest documents; corpus verification passes 8/8; normalized, segmented, and all 86,752 lexical units have Codex-assisted first-pass source-language German MIPVU decisions. Source-derived corpus artifacts remain gitignored under fair-use constraints. Results remain provisional until independent human review. |
| Cross-case | Synthesis, mapping, and validation scaffolds exist under `cases/x-case/`; comparative protocol and moral-equivalence guardrails are defined, but findings remain draft until case-level ratings, reliability, and claim traceability are promoted. |

## Corpus Boundary

The original working corpus is the verified document set for the four initial
historical cases:

- Lincoln: 3 documents.
- American Revolution: 9 documents.
- Napoleon: 10 bulletins.
- Hitler: 8 documents.

The previous working rule treated this set as frozen for v1. That rule has been
superseded by GitHub milestone 7, `Pre-v1 corpus expansion window`, tracked by
issue #174. The expansion window has added French Revolution and British World
War I as draft corpora. Any further cases or documents before v1 must remain
bounded, with clear selection criteria, rights review, acquisition provenance,
and an explicit freeze point before reliability and publication promotion
resume.

Wholesale redownload, starter-corpus replacement, and opportunistic source
growth remain out of scope unless a specific source defect is discovered.
The selection rubric for new cases and targeted document additions is recorded
in `case-selection.qmd`; the ranked candidate matrix is recorded in
`docs/corpus/pre-v1-expansion-candidate-matrix.md`; rights and provenance
decisions for proposed expansion sources are recorded in
`docs/corpus/pre-v1-expansion-rights-provenance-review.md`.

## Checks Run

Most recent local checks run on 2026-06-28:

```bash
npm run status
npm run validate
quarto render
```

Both passed. JSON validation reported that authorized local Hitler artifacts
match committed integrity hashes.

Previously recorded corpus checks:

Corpus verification passes for all four historical cases:

```bash
python3 scripts/verify-corpus.py --case lincoln
python3 scripts/verify-corpus.py --case am-rev
python3 scripts/verify-corpus.py --case napoleon
python3 scripts/verify-corpus.py --case hitler
```

Previously recorded JSON validation:

```bash
python3 scripts/validate-json.py
```

Previously recorded MIPVU worklist generation for all four historical cases:

```bash
python3 scripts/generate-mipvu-worklist.py --case lincoln
python3 scripts/generate-mipvu-worklist.py --case am-rev
python3 scripts/generate-mipvu-worklist.py --case napoleon
python3 scripts/generate-mipvu-worklist.py --case hitler
```

## Known Blockers

- Complete the bounded pre-v1 expansion window tracked by GitHub milestone 7
  and issue #174.
- Apply the expansion selection criteria, then define rights review
  requirements, per-case minimum viable corpus size, and a new freeze point.
- Complete independent human review before treating Codex-assisted MIPVU
  decisions as publication-grade evidence.
- Complete Lincoln human reliability coder submissions and adjudication.
- Design model and human reliability workflows for American Revolution,
  Napoleon, Hitler, French Revolution, and British World War I if their
  findings will be promoted beyond draft status.
- Audit annotation coverage and regenerate downstream concordance and analysis
  artifacts after any corpus expansion or annotation changes.
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
