# Multi-Model Reliability Completion Checklist

This is the final milestone gate for a case-level multi-model annotation stress
test. It is intentionally stricter than `designed` or `partial` execution
status. A case is complete only when its artifact chain, authority boundaries,
documentation, protected paths, and repository validation all pass.

Run the machine-evaluated gate with:

```bash
npm run model-reliability:completion -- \
  --case <case_id> --run-repository-validation --write
```

The command writes JSON and Markdown reports beneath
`cases/<case_id>/quality/model-reliability/completion/`. It exits nonzero while
any required item is absent or invalid. A blocked report is an honest execution
state, not a pipeline defect.

## Artifact gate

- [ ] At least two validated model runs use the current packet and prompt
  provenance.
- [ ] Agreement diagnostics preserve explicit task-layer fields for every
  measured annotation layer.
- [ ] Model-to-model stability remains separate from model-to-reference
  divergence.
- [ ] Machine-readable and reviewable disagreement logs exist.
- [ ] The human-review queue covers classified disagreements.
- [ ] Consensus/instability and codebook-revision reports exist in JSON and
  Markdown.

## Authority and protected-path gate

- [ ] Consensus records `consensus_is_evidence: false` and
  `decision_authority: human-only`.
- [ ] Every review-queue entry remains `pending-human-review`, contains no
  accepted value or automatic adjudication, and assigns authority to a human.
- [ ] Protected-write enforcement and its regression tests remain present.
- [ ] Model-reliability commands write only beneath the dedicated case-local
  `quality/model-reliability/` subtree.
- [ ] No model majority, unanimity, metric, or reference challenge changes an
  accepted annotation automatically.

Accepted corrections remain a separate human-authorized workflow. Completion
means that the diagnostic chain is auditable; it does not mean that model
agreement proves correctness, human reliability, or scholarly reproducibility.

## Documentation gate

- [ ] Public methodology and results pages distinguish model diagnostics from
  human inter-annotator reliability.
- [ ] External review procedures document blind execution, leakage controls,
  run metadata, and rights restrictions.
- [ ] Governance documentation preserves accepted annotations and prior human
  review as immutable inputs.
- [ ] Publication disclosure explains diagnostic authority, reproducibility
  limits, and restricted-span handling.

## Repository validation gate

All four commands must pass in the same repository state used for the
completion report:

```bash
npm run status
npm run validate
npm run pipeline
quarto render
```

The completion command runs them in this order when
`--run-repository-validation` is supplied and records each exit code. It stops
after the first failure. Known or rights-related local omissions must remain
visible as failures until the required lawful source state or an explicit
project validation policy resolves them.

## Completion meaning

The generated report is `complete` only when every check passes. The report is
`blocked` when submissions are missing, fewer than two runs are valid,
diagnostics are incomplete, authority fields are unsafe, documentation is
missing, protected-write controls are absent, or any repository command fails.
