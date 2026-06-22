# Human Adjudication Decision Contract

`schemas/human-reliability/adjudication-decision-schema.json` defines the
handoff from the frozen #85 queue to the ingestion and validation work in #87.
A schema-valid example is available at
`docs/reliability/adjudication/adjudication-decision-template.json`.

## Submission and queue identity

One submission belongs to exactly one case, cohort version, source language,
and task layer. `queue_snapshot` binds the decisions to the queue's logical
path, SHA-256 digest, queue version, schema version, generator version and hash,
code revision, and freeze timestamp. Queue ranks are deliberately absent from decision
identity: `queue_id` and `disagreement_id` remain stable if a later queue
version changes priority order.

The adjudicator uses a pseudonymous identifier and an explicit authorization
record. Independence, source-language qualification, and conflict management
are mandatory. A primary coder may participate in a panel when the conflict is
managed, but cannot be the sole adjudicator for that cohort.

## Decision statuses

Each queue item supports four statuses:

- `accepted`: resolves the study disagreement to an explicit adjudicated value
  based on the left coder, right coder, reference, or a separately reasoned new
  value;
- `rejected`: rejects a proposed change, retains the current reference, records
  no change, or rejects the item as adjudicable within scope; it records no new
  adjudicated value or correction candidate;
- `deferred`: postpones the decision pending named follow-up work; and
- `unresolved`: records that the available evidence does not support a bounded
  resolution and names the required next action.

Accepted and rejected decisions require a numeric confidence from 0 through 1.
Deferred and unresolved decisions keep confidence and adjudicated value null,
use `no_resolution`, and require at least one follow-up action and owner role.
Every status requires a rationale and at least one auditable evidence record.

## Codebook and claim consequences

`codebook_need` separates no change, clarification, revision, training updates,
and unresolved guidance. Non-`none` states name affected sections; a `none`
state cannot quietly request re-coding.

Affected claims are recorded individually with `no_change`,
`review_required`, or `hold_pending_resolution`, while broader affected-claim
dimensions remain a separate controlled list. Adjudication does not silently
edit a claim, report, or publication artifact.

## Correction candidates are not promotion

An accepted adjudicated value resolves the reliability study only. It does not
become an accepted corpus value automatically.

A decision may separately mark a `correction_candidate` and identify the
canonical artifact, target ID, field, current value, proposed value, rationale,
and stable candidate ID. Every candidate is fixed to:

- `promotion_status: pending_separate_authorization`;
- `promotion_id: null`; and
- `direct_write_permitted: false`.

The schema has no canonical-write, reference-update, or accepted-artifact
field. Deferred and unresolved decisions cannot emit a ready candidate.
Promotion requires the later protected-path workflow and audit record; neither
#86 nor #87 authorizes it.

## Storage boundary

Decision submissions may repeat source-derived evidence notes and therefore
inherit the queue/cohort rights and storage policy. Local-only adjudication
submissions and correction candidates stay inside the gitignored local
human-reliability subtree.
