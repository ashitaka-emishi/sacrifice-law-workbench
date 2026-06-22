# Human Coder to Reference Comparison

`scripts/human_reliability/compare_references.py` compares each validated human
coder separately with accepted or reviewable project reference fields. This is
not human-human agreement and is never folded into the metrics produced by
`compute_agreement.py`.

Run:

```bash
python3 scripts/human_reliability/compare_references.py \
  --case <case_id> \
  --cohort <cohort_id> \
  --cohort-version <version>
```

Outputs are written beside the cohort agreement artifacts:

```text
cases/<case_id>/quality/human-reliability/comparisons/
  <cohort_id>-<cohort_version>/
    reference-comparison.json
    reference-patterns.csv
```

The command requires complete #81 ingestion, verifies immutable raw
registrations and the approved cohort/packet, hashes every reference source,
and preserves packet item IDs separately from sentence, lexical-unit, or
annotation reference IDs.

## Reference authority and availability

Accepted or reviewed MIPVU units provide identification categories and their
accepted lexical boundaries. Annotated instances provide only fields actually
present in their CMT or Koenigsberg records. An annotation without an explicit
accepted/reviewed marker is labeled `reviewable_reference`; it is not silently
promoted to ground truth.

Current interpretation normalization is deliberately narrow. Boolean
`violence_logic` and `obligatory_frame` values map to controlled
`present`/`absent` judgments. The command does not infer sacred objects,
sacrificial bodies, purification, agency, or absence from neighboring fields.
Missing fields are `reference_unavailable`.

Free-text rationales, conceptual mappings, scopes, criteria, and rival readings
remain `not_comparable` and feed qualitative adjudication rather than exact
accuracy scoring.

Out-of-scope dispositions remain visible as reference-unavailable process
records; they do not disappear or become substantive reference mismatches.

## Neutral patterns

For each coder pair, item, lexical unit when applicable, and field, the command
emits one stable pattern:

| Pattern | Meaning |
|---|---|
| `both_with_reference` | Both coders share the reference value. |
| `both_against_reference` | Both coders agree with each other but differ from the reference. |
| `split_with_reference` | Coders differ and exactly one shares the reference value. |
| `split_against_both` | Coders differ and neither shares the reference value. |
| `uncertain_vs_confident` | One coder selects an uncertain identification value or `material`/`unresolved` uncertainty while the other records a non-uncertain or `none`/`low` value. |
| `reference_unavailable` | No accepted or reviewable field exists for the comparison. |

These are alignment descriptions, not correctness decisions. Shared coder
divergence may expose a stale or underspecified reference; reference alignment
may identify a coder disagreement without resolving it. Every substantive
split or both-against-reference pattern is marked for later adjudication.

## Post-adjudication comparison

The library accepts an optional adjudicated result carrying an
`adjudication_id`, matching cohort identity, and response array. Its comparison
appears in a separate `adjudicated_comparisons` section. It never replaces the
original coder comparisons or pre-adjudication agreement. Issues #86 and #87
will define and ingest the authoritative adjudication contract.
