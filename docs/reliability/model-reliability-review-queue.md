# Model Reliability Human Review Queue

`scripts/model_reliability/generate_review_queue.py` turns the classified
disagreement log into a deterministic, self-contained human review bundle:

```bash
python3 scripts/model_reliability/generate_review_queue.py --case lincoln
```

It writes `model-review-queue.json` and `model-review-queue.csv` beneath the
case-local `quality/model-reliability/review-queue/` directory.

Each queue entry includes stable identifiers, source sentence and English gloss
when available, focal span text, risk and rights metadata, reference and model
values, value groups, category, priority reasons, matched claim-audit entries,
cross-case impact tags, and the bounded review question. This allows a reviewer
to triage the disagreement without opening the packet, annotation, comparison,
and claim-audit artifacts separately.

Priority is deterministic. It begins with the classifier priority and increases
for unanimous reference challenges, claim-audit impact, cross-case impact,
methodologically sensitive fields, and possible codebook ambiguity. Cross-case
impact—including sacrifice, purification, obligation, agency/absence, and
language/reference instability—promotes a medium classifier item to the high
queue tier. Ties are resolved by stable identifiers.

The queue is not an adjudication form. It contains no accepted value, automatic
decision, or majority-vote recommendation. Every entry has
`decision_authority: "human-only"` and remains `pending-human-review`.

Source text inherits document rights and storage constraints. A queue generated
from local-only material remains local-only and must not be committed merely
because the queue format itself is public.
