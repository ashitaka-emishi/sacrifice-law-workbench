# Current Project Status

Last audited from local files on 2026-06-28.

This page tracks volatile project state. Keep stable orientation material in
`README.md`.

## Summary

The project is no longer just a scaffold. The expanded pre-v1 corpus boundary
is frozen as of 2026-06-28. It contains six cases and 41 manifest documents:
Lincoln (5), American Revolution (11), Napoleon (11), Hitler (8), French
Revolution (2), and British World War I (4). All six cases are
rights-reviewed, acquired where rights permit, normalized, segmented, and pass
corpus verification.

The metaphor workflow now has a strict MIPVU identification layer before
CMT/Koenigsberg interpretation.

The main remaining gap before publication-ready v1 is reliability and claim
promotion rather than corpus construction. The now-frozen expansion added
targeted American Revolution, Lincoln, and Napoleon documents plus draft French
Revolution and British World War I corpora, then ran them through first-pass
Codex-assisted MIPVU review, CMT/Koenigsberg annotation where supported,
concordance, case analysis, cross-case synthesis, validation, and traceability
regeneration. These annotation-forward artifacts remain provisional until
independent human review. Lincoln retains complete model-reliability artifacts
for the prior three-document core and designed human-reliability cohorts, but
required human coder submissions are not complete and the expanded Lincoln
documents are not included in that reliability design yet. American Revolution,
Napoleon, Hitler, French Revolution, and British World War I model and human
reliability workflows remain absent or incomplete. Public support ratings and
promoted analysis claims remain draft until reliability, historical citation,
and traceability gates are satisfied.

## Case State

| Area | Current state |
|---|---|
| Lincoln | 5 manifest documents; corpus verification passes 5/5; all 16,198 lexical units have Codex-assisted first-pass MIPVU decisions; all 5 documents have generated annotation artifacts. The prior 3-document core has complete historical model-reliability artifacts and designed human reliability cohorts, but required primary coder submissions are not complete and reliability resampling is still needed for the expanded corpus. |
| American Revolution | 11 manifest documents; corpus verification passes 11/11; all 34,890 lexical units have Codex-assisted first-pass MIPVU decisions; 4 documents have generated annotation artifacts. Jefferson's rough draft and Washington's Newburgh Address have reviewed MIPVU worklists but no CMT annotations from this conservative pass because no metaphor or uncertain units were selected. |
| Napoleon | 11 manifest documents; corpus verification passes 11/11; all 23,224 lexical units have Codex-assisted first-pass source-language MIPVU decisions; 9 documents have generated annotation artifacts. The pinned Gallica/Plon 1796 Army of Italy proclamation has reviewed MIPVU worklists but no CMT annotations from this conservative pass because no metaphor or uncertain units were selected. |
| French Revolution | 2 manifest documents; corpus verification passes 2/2; all 17,123 lexical units have Codex-assisted first-pass MIPVU decisions; both documents have generated annotation artifacts. No support rating or reliability sample exists yet. |
| British World War I | 4 manifest documents; corpus verification passes 4/4; all 18,213 lexical units have Codex-assisted first-pass MIPVU decisions; all 4 documents have generated annotation artifacts. No support rating or reliability sample exists yet. |
| Hitler | 8 manifest documents; corpus verification passes 8/8; normalized, segmented, and all 86,752 lexical units have Codex-assisted first-pass source-language German MIPVU decisions. Source-derived corpus artifacts remain gitignored under fair-use constraints. Results remain provisional until independent human review. |
| Cross-case | Synthesis, mapping, and validation scaffolds exist under `cases/x-case/`; comparative protocol and moral-equivalence guardrails are defined, but findings remain draft until case-level ratings, reliability, and claim traceability are promoted. |

## Frozen Corpus Boundary

The original working corpus was the verified document set for the four initial
historical cases:

- Lincoln: 3 documents.
- American Revolution: 9 documents.
- Napoleon: 10 bulletins.
- Hitler: 8 documents.

That rule was superseded by GitHub milestone 7, `Pre-v1 corpus expansion
window`, tracked by issue #174. The expansion window is now closed for corpus
growth. The frozen pre-v1 corpus is:

- Lincoln: 5 documents.
- American Revolution: 11 documents.
- Napoleon: 11 documents.
- Hitler: 8 documents.
- French Revolution: 2 documents.
- British World War I: 4 documents.

No further cases or documents should be added before v1 except to repair a
document-specific defect that blocks verification or materially corrupts an
already admitted source. Wholesale redownload, starter-corpus replacement, and
opportunistic source growth remain out of scope.
The selection rubric for new cases and targeted document additions is recorded
in `case-selection.qmd`; the ranked candidate matrix is recorded in
`docs/corpus/pre-v1-expansion-candidate-matrix.md`; rights and provenance
decisions for proposed expansion sources are recorded in
`docs/corpus/pre-v1-expansion-rights-provenance-review.md`.
Deferred candidates, including Imperial Japan, Wilson WWI, Stalin WWII,
Mao/CCP, Napoleon's Farewell to the Old Guard, Saint-Just source additions, and
Hitler support material, are future-work candidates rather than part of the
frozen pre-v1 corpus.

## Checks Run

Most recent local checks run on 2026-06-28:

```bash
npm run status
npm run validate
npm run test:model-reliability
npm run pipeline
quarto render
npm run site:table-overflow
```

These passed in the current expansion window. JSON validation reported that
authorized local Hitler artifacts match committed integrity hashes.

Previously recorded corpus checks:

Corpus verification passes for all six cases:

```bash
python3 scripts/verify-corpus.py --case lincoln
python3 scripts/verify-corpus.py --case am-rev
python3 scripts/verify-corpus.py --case napoleon
python3 scripts/verify-corpus.py --case hitler
python3 scripts/verify-corpus.py --case fr-rev
python3 scripts/verify-corpus.py --case wwi-britain
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

- Complete the remaining reliability-sampling issue in GitHub milestone 7 and
  issue #174.
- Complete independent human review before treating Codex-assisted MIPVU
  decisions as publication-grade evidence.
- Complete Lincoln human reliability coder submissions and adjudication.
- Design model and human reliability workflows for American Revolution,
  Napoleon, Hitler, French Revolution, and British World War I if their
  findings will be promoted beyond draft status.
- Refresh or resample Lincoln reliability artifacts against the expanded
  annotation-forward corpus before promotion.
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
