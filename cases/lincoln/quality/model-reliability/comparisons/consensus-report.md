# Multi-Model Consensus and Instability Report: lincoln

> Multi-model consensus is a diagnostic stress-test result, not scholarly evidence, validation, or authority to alter accepted annotations.

- Compared runs: 2
- Stable model-to-model fields: 1
- Unstable model-to-model fields: 7
- Fields with insufficient model-to-model data: 26
- Fields supporting the reference: 0
- Fields diverging from the reference: 3
- Unanimous model challenges to the reference: 11
- Pending human-review items: 37

## Model-to-model field stability

| layer | field | status | minimum | maximum | comparable |
|---|---|---|---:|---:|---:|
| `cmt` | `cmt.cluster_id` | stable | 1.000 | 1.000 | 7 |
| `cmt` | `cmt.conceptual_metaphor` | unstable | 0.000 | 0.000 | 7 |
| `cmt` | `cmt.entailments` | unstable | 0.000 | 0.000 | 7 |
| `cmt` | `cmt.source_domain_primary` | unstable | 0.714 | 0.714 | 7 |
| `cmt` | `cmt.source_domain_secondary` | unstable | 0.345 | 0.345 | 7 |
| `cmt` | `cmt.target_domain` | unstable | 0.714 | 0.714 | 7 |
| `cmt` | `confidence` | unstable | 0.071 | 0.071 | 7 |
| `cmt` | `uncertainty.status` | unstable | 0.857 | 0.857 | 7 |
| `identification` | `confidence` | insufficient-data | — | — | 0 |
| `identification` | `identification.basic_meaning` | insufficient-data | — | — | 0 |
| `identification` | `identification.boundary_decision` | insufficient-data | — | — | 0 |
| `identification` | `identification.boundary_span` | insufficient-data | — | — | 0 |
| `identification` | `identification.comparison_basis` | insufficient-data | — | — | 0 |
| `identification` | `identification.contextual_meaning` | insufficient-data | — | — | 0 |
| `identification` | `identification.contrast_explanation` | insufficient-data | — | — | 0 |
| `identification` | `identification.decision` | insufficient-data | — | — | 0 |
| `identification` | `uncertainty.status` | insufficient-data | — | — | 0 |
| `interpretation` | `confidence` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.absence.displacement_mechanism` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.absence.expected_presence` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.absence.possible_absence` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.absence.status` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.agency.agents` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.agency.beneficiaries` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.agency.excluded_agents` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.agency.patients` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.agency.sacrificial_subjects` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.enemy_as_bringer_of_death` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.obligatory_frame` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.purification` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.sacred_object` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.sacrificial_body` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.violence_logic` | insufficient-data | — | — | 0 |
| `interpretation` | `uncertainty.status` | insufficient-data | — | — | 0 |

## Reference diagnostics

| layer | field | status | minimum | maximum | comparable |
|---|---|---|---:|---:|---:|
| `cmt` | `cmt.cluster_id` | challenged-reference | 0.429 | 0.429 | 14 |
| `cmt` | `cmt.conceptual_metaphor` | diverges-from-reference | 0.000 | 0.000 | 14 |
| `cmt` | `cmt.entailments` | diverges-from-reference | 0.000 | 0.000 | 14 |
| `cmt` | `cmt.source_domain_primary` | challenged-reference | 0.286 | 0.571 | 14 |
| `cmt` | `cmt.source_domain_secondary` | challenged-reference | 0.000 | 0.000 | 14 |
| `cmt` | `cmt.target_domain` | challenged-reference | 0.286 | 0.429 | 14 |
| `cmt` | `confidence` | diverges-from-reference | 0.036 | 0.091 | 14 |
| `cmt` | `uncertainty.status` | insufficient-data | — | — | 0 |
| `identification` | `confidence` | insufficient-data | — | — | 0 |
| `identification` | `identification.basic_meaning` | insufficient-data | — | — | 0 |
| `identification` | `identification.boundary_decision` | insufficient-data | — | — | 0 |
| `identification` | `identification.boundary_span` | insufficient-data | — | — | 0 |
| `identification` | `identification.comparison_basis` | insufficient-data | — | — | 0 |
| `identification` | `identification.contextual_meaning` | insufficient-data | — | — | 0 |
| `identification` | `identification.contrast_explanation` | insufficient-data | — | — | 0 |
| `identification` | `identification.decision` | insufficient-data | — | — | 0 |
| `identification` | `uncertainty.status` | insufficient-data | — | — | 0 |
| `interpretation` | `confidence` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.absence.displacement_mechanism` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.absence.expected_presence` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.absence.possible_absence` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.absence.status` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.agency.agents` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.agency.beneficiaries` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.agency.excluded_agents` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.agency.patients` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.agency.sacrificial_subjects` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.enemy_as_bringer_of_death` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.obligatory_frame` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.purification` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.sacred_object` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.sacrificial_body` | insufficient-data | — | — | 0 |
| `interpretation` | `interpretation.functions.violence_logic` | insufficient-data | — | — | 0 |
| `interpretation` | `uncertainty.status` | insufficient-data | — | — | 0 |

## Document risk

| document_id | disagreements | unanimous challenges | high priority |
|---|---:|---:|---:|
| `lincoln-lyceum-address` | 21 | 5 | 12 |
| `lincoln-gettysburg-address` | 11 | 3 | 7 |
| `lincoln-second-inaugural` | 5 | 3 | 3 |

## Cluster risk

| cluster_id | disagreements | unanimous challenges | high priority |
|---|---:|---:|---:|
| `unassigned` | 21 | 6 | 13 |
| `lincoln-01-body-organism` | 11 | 5 | 6 |
| `lincoln-08-sacrificial-death-gift` | 5 | 0 | 3 |

## Language risk

| source_language | disagreements | unanimous challenges | high priority |
|---|---:|---:|---:|
| `en` | 37 | 11 | 22 |

## Human-review priorities

- `review-0001` (high) — `cmt` / `cmt.cluster_id` / `lincoln-lyceum-address`: Do the unanimous model values for `cmt.cluster_id` on `lincoln-ann-003` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0002` (high) — `cmt` / `cmt.target_domain` / `lincoln-lyceum-address`: Do the unanimous model values for `cmt.target_domain` on `lincoln-ann-003` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0003` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-lyceum-address`: Do the unanimous model values for `cmt.source_domain_primary` on `lincoln-ann-017` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0004` (high) — `cmt` / `cmt.target_domain` / `lincoln-lyceum-address`: Do the unanimous model values for `cmt.target_domain` on `lincoln-ann-017` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0005` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-second-inaugural`: Do the unanimous model values for `cmt.source_domain_primary` on `lincoln-ann-064` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0006` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-second-inaugural`: Do the unanimous model values for `cmt.source_domain_secondary` on `lincoln-ann-064` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0007` (high) — `cmt` / `cmt.target_domain` / `lincoln-second-inaugural`: Do the unanimous model values for `cmt.target_domain` on `lincoln-ann-064` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0008` (high) — `cmt` / `cmt.cluster_id` / `lincoln-gettysburg-address`: Do the unanimous model values for `cmt.cluster_id` on `lincoln-ann-051` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0009` (high) — `cmt` / `cmt.cluster_id` / `lincoln-gettysburg-address`: Do the unanimous model values for `cmt.cluster_id` on `lincoln-ann-054` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0010` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-gettysburg-address`: Do the unanimous model values for `cmt.source_domain_primary` on `lincoln-ann-054` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0011` (high) — `cmt` / `cmt.cluster_id` / `lincoln-lyceum-address`: Do the unanimous model values for `cmt.cluster_id` on `lincoln-ann-043` expose a reference error, a codebook ambiguity, or shared model bias?
- `review-0012` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-lyceum-address`: Which value for `cmt.source_domain_secondary` on `lincoln-ann-003` best follows the codebook and source context?
- `review-0013` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-lyceum-address`: Which value for `cmt.source_domain_secondary` on `lincoln-ann-017` best follows the codebook and source context?
- `review-0014` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-gettysburg-address`: Which value for `cmt.source_domain_secondary` on `lincoln-ann-051` best follows the codebook and source context?
- `review-0015` (high) — `cmt` / `cmt.target_domain` / `lincoln-gettysburg-address`: Which value for `cmt.target_domain` on `lincoln-ann-051` best follows the codebook and source context?
- `review-0016` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-gettysburg-address`: Which value for `cmt.source_domain_secondary` on `lincoln-ann-054` best follows the codebook and source context?
- `review-0017` (high) — `cmt` / `uncertainty.status` / `lincoln-gettysburg-address`: Which value for `uncertainty.status` on `lincoln-ann-054` best follows the codebook and source context?
- `review-0018` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-lyceum-address`: Which value for `cmt.source_domain_primary` on `lincoln-ann-016` best follows the codebook and source context?
- `review-0019` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-lyceum-address`: Which value for `cmt.source_domain_secondary` on `lincoln-ann-016` best follows the codebook and source context?
- `review-0020` (high) — `cmt` / `cmt.target_domain` / `lincoln-lyceum-address`: Which value for `cmt.target_domain` on `lincoln-ann-016` best follows the codebook and source context?
- `review-0021` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-lyceum-address`: Which value for `cmt.source_domain_primary` on `lincoln-ann-043` best follows the codebook and source context?
- `review-0022` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-lyceum-address`: Which value for `cmt.source_domain_secondary` on `lincoln-ann-043` best follows the codebook and source context?
- `review-0023` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-lyceum-address`: Which value for `cmt.conceptual_metaphor` on `lincoln-ann-003` best follows the codebook and source context?
- `review-0024` (medium) — `cmt` / `cmt.entailments` / `lincoln-lyceum-address`: Which value for `cmt.entailments` on `lincoln-ann-003` best follows the codebook and source context?
- `review-0025` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-lyceum-address`: Which value for `cmt.conceptual_metaphor` on `lincoln-ann-017` best follows the codebook and source context?
- `review-0026` (medium) — `cmt` / `cmt.entailments` / `lincoln-lyceum-address`: Which value for `cmt.entailments` on `lincoln-ann-017` best follows the codebook and source context?
- `review-0027` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-second-inaugural`: Which value for `cmt.conceptual_metaphor` on `lincoln-ann-064` best follows the codebook and source context?
- `review-0028` (medium) — `cmt` / `cmt.entailments` / `lincoln-second-inaugural`: Which value for `cmt.entailments` on `lincoln-ann-064` best follows the codebook and source context?
- `review-0029` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-gettysburg-address`: Which value for `cmt.conceptual_metaphor` on `lincoln-ann-051` best follows the codebook and source context?
- `review-0030` (medium) — `cmt` / `cmt.entailments` / `lincoln-gettysburg-address`: Which value for `cmt.entailments` on `lincoln-ann-051` best follows the codebook and source context?
- `review-0031` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-gettysburg-address`: Which value for `cmt.conceptual_metaphor` on `lincoln-ann-054` best follows the codebook and source context?
- `review-0032` (medium) — `cmt` / `cmt.entailments` / `lincoln-gettysburg-address`: Which value for `cmt.entailments` on `lincoln-ann-054` best follows the codebook and source context?
- `review-0033` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-lyceum-address`: Which value for `cmt.conceptual_metaphor` on `lincoln-ann-016` best follows the codebook and source context?
- `review-0034` (medium) — `cmt` / `cmt.entailments` / `lincoln-lyceum-address`: Which value for `cmt.entailments` on `lincoln-ann-016` best follows the codebook and source context?
- `review-0035` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-lyceum-address`: Which value for `cmt.conceptual_metaphor` on `lincoln-ann-043` best follows the codebook and source context?
- `review-0036` (medium) — `cmt` / `cmt.entailments` / `lincoln-lyceum-address`: Which value for `cmt.entailments` on `lincoln-ann-043` best follows the codebook and source context?
- `review-0037` (low) — `cmt` / `confidence` / `lincoln-lyceum-address`: Which value for `confidence` on `lincoln-ann-017` best follows the codebook and source context?

## Interpretation limits

- Consensus may reflect shared model bias or shared prompt effects.
- Reference support is diagnostic alignment, not independent evidence.
- Reference challenges require human source and codebook review.
- Undefined or sparse metrics are reported as insufficient data.
- Invalid submissions remain visible but are not pooled into agreement metrics.

No count, metric, consensus pattern, or reference-alignment result in this report may update an accepted annotation without human review.
