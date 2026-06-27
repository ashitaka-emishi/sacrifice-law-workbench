# Model Instability Report: lincoln

> Diagnostic stress-test output only. Model agreement does not validate an interpretation or alter accepted annotations.

- Compared runs: 2
- Substantive disagreements: 37
- Unanimous model challenges to the accepted reference: 11
- High-priority human review items: 11
- Possible codebook ambiguities: 36

## Layer instability

| task_layer | disagreements |
|---|---:|
| `cmt` | 37 |

## Category instability

| category | disagreements |
|---|---:|
| `confidence-instability` | 1 |
| `context-instability` | 1 |
| `domain-instability` | 8 |
| `reference-challenge` | 11 |
| `semantic-instability` | 14 |
| `target-domain-instability` | 2 |

## Document instability

| document_id | disagreements |
|---|---:|
| `lincoln-gettysburg-address` | 11 |
| `lincoln-lyceum-address` | 21 |
| `lincoln-second-inaugural` | 5 |

## Cluster instability

| cluster_id | disagreements |
|---|---:|
| `lincoln-01-body-organism` | 11 |
| `lincoln-08-sacrificial-death-gift` | 5 |
| `unassigned` | 21 |

## Language instability

| source_language | disagreements |
|---|---:|
| `en` | 37 |

## Human-review priorities

- `disagreement-0001` — **reference-challenge** on `lincoln-ann-003`: Do the unanimous model values for `cmt.cluster_id` on `lincoln-ann-003` expose a reference error, a codebook ambiguity, or shared model bias?
- `disagreement-0005` — **reference-challenge** on `lincoln-ann-003`: Do the unanimous model values for `cmt.target_domain` on `lincoln-ann-003` expose a reference error, a codebook ambiguity, or shared model bias?
- `disagreement-0013` — **reference-challenge** on `lincoln-ann-017`: Do the unanimous model values for `cmt.source_domain_primary` on `lincoln-ann-017` expose a reference error, a codebook ambiguity, or shared model bias?
- `disagreement-0015` — **reference-challenge** on `lincoln-ann-017`: Do the unanimous model values for `cmt.target_domain` on `lincoln-ann-017` expose a reference error, a codebook ambiguity, or shared model bias?
- `disagreement-0017` — **reference-challenge** on `lincoln-ann-043`: Do the unanimous model values for `cmt.cluster_id` on `lincoln-ann-043` expose a reference error, a codebook ambiguity, or shared model bias?
- `disagreement-0022` — **reference-challenge** on `lincoln-ann-051`: Do the unanimous model values for `cmt.cluster_id` on `lincoln-ann-051` expose a reference error, a codebook ambiguity, or shared model bias?
- `disagreement-0027` — **reference-challenge** on `lincoln-ann-054`: Do the unanimous model values for `cmt.cluster_id` on `lincoln-ann-054` expose a reference error, a codebook ambiguity, or shared model bias?
- `disagreement-0030` — **reference-challenge** on `lincoln-ann-054`: Do the unanimous model values for `cmt.source_domain_primary` on `lincoln-ann-054` expose a reference error, a codebook ambiguity, or shared model bias?
- `disagreement-0035` — **reference-challenge** on `lincoln-ann-064`: Do the unanimous model values for `cmt.source_domain_primary` on `lincoln-ann-064` expose a reference error, a codebook ambiguity, or shared model bias?
- `disagreement-0036` — **reference-challenge** on `lincoln-ann-064`: Do the unanimous model values for `cmt.source_domain_secondary` on `lincoln-ann-064` expose a reference error, a codebook ambiguity, or shared model bias?
- `disagreement-0037` — **reference-challenge** on `lincoln-ann-064`: Do the unanimous model values for `cmt.target_domain` on `lincoln-ann-064` expose a reference error, a codebook ambiguity, or shared model bias?

## Interpretation limits

- Consensus may reflect shared model bias.
- Reference challenges require human source and codebook review.
- Invalid submissions remain visible but are not pooled with valid-run metrics.
