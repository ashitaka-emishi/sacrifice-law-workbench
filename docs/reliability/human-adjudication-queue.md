# Human Adjudication Queue Generation

`scripts/human_reliability/generate_adjudication_queue.py` converts a validated
human disagreement log into a deterministic queue for an independent,
authorized human adjudicator:

```bash
npm run human-reliability:queue -- \
  --case lincoln \
  --cohort lincoln-en-cmt \
  --cohort-version 1.0.0
```

The command writes `adjudication-queue.json` and
`adjudication-queue.csv` beside the cohort's disagreement log. The JSON output
conforms to `schemas/human-reliability/adjudication-queue-schema.json`.

## Evidence boundary

Each entry preserves the disagreement and source-pattern IDs, both coder
values, the separately labeled reference summary, category, claim impact,
source-language risk, priority reasons, and bounded review question. Source
text and focal lexical text come only from the original blind packet after its
manifest self-hash and payload hash are verified.

Direct affected claims are linked through matching unit, sentence, or reference
IDs in an available claim-trace artifact. Broader affected-claim dimensions
such as metaphor presence, mapping, sacrifice, purification, violence,
obligation, agency/absence, and source-language interpretation remain separate
from direct claim links.

A valid model-reliability agreement artifact is optional. When present, only
matching aggregate field summaries are included. When absent, the queue records
an explicit `unavailable` status. Model summaries are diagnostic context, not
votes, and are never blended with coder values or reference evidence.

## Priority policy

The queue begins with #84's adjudication priority and then applies deterministic
increments. It promotes:

- a presence/nonpresence disagreement;
- both coders diverging from the reference;
- high claim impact or a direct claim trace;
- agency/absence, purification, and violence fields; and
- material/high source-language risk or an uncertainty split.

Ranks may change when new disagreements or claim traces are added. Queue IDs
are hashes of stable disagreement IDs, so downstream adjudication records can
refer to the same item across re-ranking.

## Safety and authority

The queue contains no adjudication decision, accepted value, or reference
update. It is marked `pending-independent-adjudication`, and decision authority
is reserved for an authorized human adjudicator. Generation writes only under
the cohort comparison directory and never modifies packets, submissions,
accepted annotations, model artifacts, claim traces, or source corpora.

Queue files reproduce packet source text and therefore inherit the cohort's
`repository_allowed` or `local_only` storage policy and rights constraints.
Local-only queues remain local and untracked with their source-derived cohort
artifacts.
