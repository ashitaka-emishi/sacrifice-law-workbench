# Model Reliability Completion Checklist

Status: **complete**.

This is a milestone-readiness gate, not evidence that model consensus is
correct. Accepted annotations can change only through separate human
review and authorization.

## Gate checks

- [x] **validated-runs** — 2 validated run(s); at least two are required.
- [x] **required-artifacts** — All required comparison, disagreement, queue, and report artifacts exist.
- [x] **layered-metrics** — Layered diagnostics present for: cmt, identification, interpretation
- [x] **consensus-authority** — Consensus is diagnostic and decision authority is human-only.
- [x] **review-queue-authority** — Review candidates remain pending with human-only authority.
- [x] **protected-write-guard** — Protected-write enforcement and regression tests are present.
- [x] **required-documentation** — Method, results, governance, procedures, publication, and gate documentation exist.
- [x] **repository-validation** — All required repository validation commands passed.

## Required repository commands

- [x] `npm run status`
- [x] `npm run validate`
- [x] `npm run pipeline`
- [x] `quarto render`

A complete report requires every artifact, authority, documentation,
protected-path, and repository-validation check to pass.
