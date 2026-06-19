# Multi-Model Consensus and Instability Report

`scripts/model_reliability/generate_consensus_report.py` combines the layered
agreement results, classified disagreement log, and human review queue:

```bash
python3 scripts/model_reliability/generate_consensus_report.py --case lincoln
```

It writes `consensus-report.json` and `consensus-report.md` beneath the
case-local `quality/model-reliability/comparisons/` directory.

The report keeps model-to-model stability separate from model-to-reference
alignment. A field is stable only when every defined model-pair metric is
perfect; any defined non-perfect pair makes it unstable. Fields with no defined
pair metric remain `insufficient-data` rather than being treated as stable.

Reference diagnostics are reported independently as support, mixed alignment,
divergence, explicit challenge, or insufficient data. A unanimous challenge
overrides any support label and remains an explicit human-review question.
Neither support nor challenge is scholarly evidence: shared model behavior can
reflect shared bias, prompt effects, or common training-data artifacts.

Risk rollups identify documents, clusters, and source languages with the most
disagreements, unanimous reference challenges, and high-priority queue items.
The priority list carries only diagnostic context and bounded review questions;
every item retains `decision_authority: "human-only"`.

The generator rejects stale or mismatched run IDs, untrusted upstream
generators, unreconciled summaries, and review queues that do not cover exactly
the classified disagreements. It writes only within the case-local
`model-reliability` subtree and never modifies accepted annotations.
