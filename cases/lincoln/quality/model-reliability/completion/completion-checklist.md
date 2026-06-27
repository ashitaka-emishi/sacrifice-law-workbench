# Model Reliability Completion Checklist

Status: **blocked**.

This is a milestone-readiness gate, not evidence that model consensus is
correct. Accepted annotations can change only through separate human
review and authorization.

## Gate checks

- [x] **validated-runs** — 4 validated run(s); at least two are required.
- [x] **required-artifacts** — All required comparison, disagreement, queue, and report artifacts exist.
- [x] **layered-metrics** — Layered diagnostics present for: cmt, identification, interpretation
- [x] **consensus-authority** — Consensus is diagnostic and decision authority is human-only.
- [x] **review-queue-authority** — Review candidates remain pending with human-only authority.
- [x] **protected-write-guard** — Protected-write enforcement and regression tests are present.
- [x] **required-documentation** — Method, results, governance, procedures, publication, and gate documentation exist.
- [ ] **repository-validation** — Run the completion command with --run-repository-validation.

## Required repository commands

- [ ] `npm run status`
- [ ] `npm run validate`
- [ ] `npm run pipeline`
- [ ] `quarto render`

A complete report requires every artifact, authority, documentation,
protected-path, and repository-validation check to pass.
