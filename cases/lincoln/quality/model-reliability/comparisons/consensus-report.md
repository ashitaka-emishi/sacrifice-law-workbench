# Multi-Model Consensus and Instability Report: lincoln

> Multi-model consensus is a diagnostic stress-test result, not scholarly evidence, validation, or authority to alter accepted annotations.

- Compared runs: 4
- Stable model-to-model fields: 2
- Unstable model-to-model fields: 23
- Fields with insufficient model-to-model data: 9
- Fields supporting the reference: 0
- Fields diverging from the reference: 8
- Unanimous model challenges to the reference: 0
- Pending human-review items: 160

## Model-to-model field stability

| layer | field | status | minimum | maximum | comparable |
|---|---|---|---:|---:|---:|
| `cmt` | `cmt.cluster_id` | stable | 1.000 | 1.000 | 7 |
| `cmt` | `cmt.conceptual_metaphor` | unstable | 0.000 | 0.000 | 7 |
| `cmt` | `cmt.entailments` | unstable | 0.000 | 0.000 | 7 |
| `cmt` | `cmt.source_domain_primary` | unstable | 0.714 | 0.714 | 7 |
| `cmt` | `cmt.source_domain_secondary` | unstable | 0.345 | 0.345 | 7 |
| `cmt` | `cmt.target_domain` | unstable | 0.714 | 0.714 | 7 |
| `cmt` | `confidence` | unstable | 0.070 | 0.174 | 35 |
| `cmt` | `uncertainty.status` | unstable | 0.143 | 0.857 | 35 |
| `identification` | `confidence` | insufficient-data | — | — | 0 |
| `identification` | `identification.basic_meaning` | insufficient-data | — | — | 0 |
| `identification` | `identification.boundary_decision` | insufficient-data | — | — | 0 |
| `identification` | `identification.boundary_span` | insufficient-data | — | — | 0 |
| `identification` | `identification.comparison_basis` | insufficient-data | — | — | 0 |
| `identification` | `identification.contextual_meaning` | insufficient-data | — | — | 0 |
| `identification` | `identification.contrast_explanation` | insufficient-data | — | — | 0 |
| `identification` | `identification.decision` | insufficient-data | — | — | 0 |
| `identification` | `uncertainty.status` | insufficient-data | — | — | 0 |
| `interpretation` | `confidence` | unstable | 0.107 | 0.107 | 7 |
| `interpretation` | `interpretation.absence.displacement_mechanism` | unstable | 0.000 | 0.000 | 7 |
| `interpretation` | `interpretation.absence.expected_presence` | unstable | 0.000 | 0.000 | 7 |
| `interpretation` | `interpretation.absence.possible_absence` | unstable | 0.000 | 0.000 | 7 |
| `interpretation` | `interpretation.absence.status` | stable | 1.000 | 1.000 | 7 |
| `interpretation` | `interpretation.agency.agents` | unstable | 0.226 | 0.226 | 7 |
| `interpretation` | `interpretation.agency.beneficiaries` | unstable | 0.250 | 0.250 | 7 |
| `interpretation` | `interpretation.agency.excluded_agents` | unstable | 0.000 | 0.000 | 7 |
| `interpretation` | `interpretation.agency.patients` | unstable | 0.000 | 0.000 | 7 |
| `interpretation` | `interpretation.agency.sacrificial_subjects` | unstable | 0.393 | 0.393 | 7 |
| `interpretation` | `interpretation.functions.enemy_as_bringer_of_death` | unstable | 0.714 | 0.714 | 7 |
| `interpretation` | `interpretation.functions.obligatory_frame` | unstable | 0.857 | 0.857 | 7 |
| `interpretation` | `interpretation.functions.purification` | unstable | 0.714 | 0.714 | 7 |
| `interpretation` | `interpretation.functions.sacred_object` | unstable | 0.571 | 0.571 | 7 |
| `interpretation` | `interpretation.functions.sacrificial_body` | unstable | 0.857 | 0.857 | 7 |
| `interpretation` | `interpretation.functions.violence_logic` | unstable | 0.714 | 0.714 | 7 |
| `interpretation` | `uncertainty.status` | unstable | 0.571 | 0.571 | 7 |

## Reference diagnostics

| layer | field | status | minimum | maximum | comparable |
|---|---|---|---:|---:|---:|
| `cmt` | `cmt.cluster_id` | diverges-from-reference | 0.429 | 0.429 | 14 |
| `cmt` | `cmt.conceptual_metaphor` | diverges-from-reference | 0.000 | 0.000 | 14 |
| `cmt` | `cmt.entailments` | diverges-from-reference | 0.000 | 0.000 | 14 |
| `cmt` | `cmt.source_domain_primary` | diverges-from-reference | 0.143 | 0.429 | 14 |
| `cmt` | `cmt.source_domain_secondary` | diverges-from-reference | 0.000 | 0.000 | 14 |
| `cmt` | `cmt.target_domain` | diverges-from-reference | 0.143 | 0.286 | 14 |
| `cmt` | `confidence` | diverges-from-reference | 0.048 | 0.088 | 14 |
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
| `interpretation` | `confidence` | diverges-from-reference | 0.034 | 0.127 | 14 |
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
| `lincoln-lyceum-address` | 91 | 0 | 71 |
| `lincoln-gettysburg-address` | 46 | 0 | 36 |
| `lincoln-second-inaugural` | 23 | 0 | 18 |

## Cluster risk

| cluster_id | disagreements | unanimous challenges | high priority |
|---|---:|---:|---:|
| `unassigned` | 92 | 0 | 72 |
| `lincoln-01-body-organism` | 45 | 0 | 35 |
| `lincoln-08-sacrificial-death-gift` | 23 | 0 | 18 |

## Language risk

| source_language | disagreements | unanimous challenges | high priority |
|---|---:|---:|---:|
| `en` | 160 | 0 | 125 |

## Human-review priorities

- `review-0001` (high) — `interpretation` / `interpretation.absence.displacement_mechanism` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.displacement_mechanism` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0002` (high) — `interpretation` / `interpretation.absence.expected_presence` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.expected_presence` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0003` (high) — `interpretation` / `interpretation.absence.possible_absence` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.possible_absence` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0004` (high) — `interpretation` / `interpretation.absence.status` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.status` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0005` (high) — `interpretation` / `interpretation.agency.agents` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.agents` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0006` (high) — `interpretation` / `interpretation.agency.beneficiaries` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.beneficiaries` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0007` (high) — `interpretation` / `interpretation.agency.excluded_agents` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.excluded_agents` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0008` (high) — `interpretation` / `interpretation.agency.patients` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.patients` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0009` (high) — `interpretation` / `interpretation.agency.sacrificial_subjects` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.sacrificial_subjects` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0010` (high) — `interpretation` / `interpretation.functions.obligatory_frame` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.obligatory_frame` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0011` (high) — `interpretation` / `interpretation.absence.displacement_mechanism` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.displacement_mechanism` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0012` (high) — `interpretation` / `interpretation.absence.expected_presence` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.expected_presence` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0013` (high) — `interpretation` / `interpretation.absence.possible_absence` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.possible_absence` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0014` (high) — `interpretation` / `interpretation.absence.status` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.status` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0015` (high) — `interpretation` / `interpretation.agency.agents` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.agents` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0016` (high) — `interpretation` / `interpretation.agency.beneficiaries` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.beneficiaries` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0017` (high) — `interpretation` / `interpretation.agency.excluded_agents` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.excluded_agents` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0018` (high) — `interpretation` / `interpretation.agency.patients` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.patients` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0019` (high) — `interpretation` / `interpretation.agency.sacrificial_subjects` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.sacrificial_subjects` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0020` (high) — `interpretation` / `interpretation.functions.obligatory_frame` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.obligatory_frame` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0021` (high) — `interpretation` / `interpretation.absence.displacement_mechanism` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.absence.displacement_mechanism` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0022` (high) — `interpretation` / `interpretation.absence.expected_presence` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.absence.expected_presence` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0023` (high) — `interpretation` / `interpretation.absence.possible_absence` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.absence.possible_absence` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0024` (high) — `interpretation` / `interpretation.absence.status` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.absence.status` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0025` (high) — `interpretation` / `interpretation.agency.agents` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.agency.agents` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0026` (high) — `interpretation` / `interpretation.agency.beneficiaries` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.agency.beneficiaries` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0027` (high) — `interpretation` / `interpretation.agency.excluded_agents` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.agency.excluded_agents` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0028` (high) — `interpretation` / `interpretation.agency.patients` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.agency.patients` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0029` (high) — `interpretation` / `interpretation.agency.sacrificial_subjects` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.agency.sacrificial_subjects` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0030` (high) — `interpretation` / `interpretation.functions.obligatory_frame` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.functions.obligatory_frame` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0031` (high) — `cmt` / `uncertainty.status` / `lincoln-lyceum-address`: Which value for `uncertainty.status` on `lincoln-ann-003` best follows the codebook and source context?
- `review-0032` (high) — `cmt` / `uncertainty.status` / `lincoln-second-inaugural`: Which value for `uncertainty.status` on `lincoln-ann-064` best follows the codebook and source context?
- `review-0033` (high) — `cmt` / `cmt.cluster_id` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.cluster_id` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0034` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.source_domain_primary` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0035` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.source_domain_secondary` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0036` (high) — `cmt` / `cmt.target_domain` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.target_domain` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0037` (high) — `interpretation` / `interpretation.functions.purification` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.purification` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0038` (high) — `interpretation` / `interpretation.functions.sacred_object` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.sacred_object` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0039` (high) — `interpretation` / `interpretation.functions.sacrificial_body` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.sacrificial_body` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0040` (high) — `cmt` / `cmt.cluster_id` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.cluster_id` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0041` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.source_domain_primary` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0042` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.source_domain_secondary` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0043` (high) — `cmt` / `cmt.target_domain` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.target_domain` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0044` (high) — `interpretation` / `interpretation.functions.purification` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.purification` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0045` (high) — `interpretation` / `interpretation.functions.sacred_object` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.sacred_object` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0046` (high) — `interpretation` / `interpretation.functions.sacrificial_body` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.sacrificial_body` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0047` (high) — `cmt` / `cmt.cluster_id` / `lincoln-second-inaugural`: Why did one or more runs omit `cmt.cluster_id` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0048` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-second-inaugural`: Why did one or more runs omit `cmt.source_domain_primary` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0049` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-second-inaugural`: Why did one or more runs omit `cmt.source_domain_secondary` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0050` (high) — `cmt` / `cmt.target_domain` / `lincoln-second-inaugural`: Why did one or more runs omit `cmt.target_domain` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0051` (high) — `interpretation` / `interpretation.functions.purification` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.functions.purification` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0052` (high) — `interpretation` / `interpretation.functions.sacred_object` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.functions.sacred_object` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0053` (high) — `interpretation` / `interpretation.functions.sacrificial_body` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.functions.sacrificial_body` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0054` (high) — `interpretation` / `interpretation.absence.displacement_mechanism` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.absence.displacement_mechanism` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0055` (high) — `interpretation` / `interpretation.absence.expected_presence` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.absence.expected_presence` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0056` (high) — `interpretation` / `interpretation.absence.possible_absence` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.absence.possible_absence` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0057` (high) — `interpretation` / `interpretation.absence.status` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.absence.status` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0058` (high) — `interpretation` / `interpretation.agency.agents` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.agency.agents` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0059` (high) — `interpretation` / `interpretation.agency.beneficiaries` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.agency.beneficiaries` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0060` (high) — `interpretation` / `interpretation.agency.excluded_agents` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.agency.excluded_agents` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0061` (high) — `interpretation` / `interpretation.agency.patients` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.agency.patients` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0062` (high) — `interpretation` / `interpretation.agency.sacrificial_subjects` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.agency.sacrificial_subjects` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0063` (high) — `interpretation` / `interpretation.functions.obligatory_frame` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.obligatory_frame` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0064` (high) — `interpretation` / `interpretation.absence.displacement_mechanism` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.absence.displacement_mechanism` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0065` (high) — `interpretation` / `interpretation.absence.expected_presence` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.absence.expected_presence` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0066` (high) — `interpretation` / `interpretation.absence.possible_absence` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.absence.possible_absence` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0067` (high) — `interpretation` / `interpretation.absence.status` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.absence.status` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0068` (high) — `interpretation` / `interpretation.agency.agents` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.agency.agents` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0069` (high) — `interpretation` / `interpretation.agency.beneficiaries` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.agency.beneficiaries` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0070` (high) — `interpretation` / `interpretation.agency.excluded_agents` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.agency.excluded_agents` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0071` (high) — `interpretation` / `interpretation.agency.patients` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.agency.patients` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0072` (high) — `interpretation` / `interpretation.agency.sacrificial_subjects` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.agency.sacrificial_subjects` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0073` (high) — `interpretation` / `interpretation.functions.obligatory_frame` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.obligatory_frame` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0074` (high) — `interpretation` / `interpretation.absence.displacement_mechanism` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.displacement_mechanism` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0075` (high) — `interpretation` / `interpretation.absence.expected_presence` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.expected_presence` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0076` (high) — `interpretation` / `interpretation.absence.possible_absence` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.possible_absence` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0077` (high) — `interpretation` / `interpretation.absence.status` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.status` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0078` (high) — `interpretation` / `interpretation.agency.agents` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.agents` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0079` (high) — `interpretation` / `interpretation.agency.beneficiaries` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.beneficiaries` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0080` (high) — `interpretation` / `interpretation.agency.excluded_agents` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.excluded_agents` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0081` (high) — `interpretation` / `interpretation.agency.patients` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.patients` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0082` (high) — `interpretation` / `interpretation.agency.sacrificial_subjects` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.sacrificial_subjects` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0083` (high) — `interpretation` / `interpretation.functions.obligatory_frame` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.obligatory_frame` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0084` (high) — `interpretation` / `interpretation.absence.displacement_mechanism` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.displacement_mechanism` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0085` (high) — `interpretation` / `interpretation.absence.expected_presence` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.expected_presence` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0086` (high) — `interpretation` / `interpretation.absence.possible_absence` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.possible_absence` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0087` (high) — `interpretation` / `interpretation.absence.status` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.absence.status` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0088` (high) — `interpretation` / `interpretation.agency.agents` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.agents` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0089` (high) — `interpretation` / `interpretation.agency.beneficiaries` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.beneficiaries` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0090` (high) — `interpretation` / `interpretation.agency.excluded_agents` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.excluded_agents` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0091` (high) — `interpretation` / `interpretation.agency.patients` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.patients` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0092` (high) — `interpretation` / `interpretation.agency.sacrificial_subjects` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.agency.sacrificial_subjects` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0093` (high) — `interpretation` / `interpretation.functions.obligatory_frame` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.obligatory_frame` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0094` (high) — `cmt` / `uncertainty.status` / `lincoln-gettysburg-address`: Which value for `uncertainty.status` on `lincoln-ann-051` best follows the codebook and source context?
- `review-0095` (high) — `cmt` / `uncertainty.status` / `lincoln-gettysburg-address`: Which value for `uncertainty.status` on `lincoln-ann-054` best follows the codebook and source context?
- `review-0096` (high) — `cmt` / `uncertainty.status` / `lincoln-lyceum-address`: Which value for `uncertainty.status` on `lincoln-ann-016` best follows the codebook and source context?
- `review-0097` (high) — `cmt` / `uncertainty.status` / `lincoln-lyceum-address`: Which value for `uncertainty.status` on `lincoln-ann-043` best follows the codebook and source context?
- `review-0098` (high) — `cmt` / `cmt.cluster_id` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.cluster_id` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0099` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.source_domain_primary` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0100` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.source_domain_secondary` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0101` (high) — `cmt` / `cmt.target_domain` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.target_domain` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0102` (high) — `interpretation` / `interpretation.functions.purification` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.purification` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0103` (high) — `interpretation` / `interpretation.functions.sacred_object` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.sacred_object` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0104` (high) — `interpretation` / `interpretation.functions.sacrificial_body` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.sacrificial_body` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0105` (high) — `cmt` / `cmt.cluster_id` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.cluster_id` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0106` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.source_domain_primary` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0107` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.source_domain_secondary` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0108` (high) — `cmt` / `cmt.target_domain` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.target_domain` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0109` (high) — `interpretation` / `interpretation.functions.purification` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.purification` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0110` (high) — `interpretation` / `interpretation.functions.sacred_object` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.sacred_object` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0111` (high) — `interpretation` / `interpretation.functions.sacrificial_body` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.sacrificial_body` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0112` (high) — `cmt` / `cmt.cluster_id` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.cluster_id` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0113` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.source_domain_primary` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0114` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.source_domain_secondary` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0115` (high) — `cmt` / `cmt.target_domain` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.target_domain` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0116` (high) — `interpretation` / `interpretation.functions.purification` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.purification` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0117` (high) — `interpretation` / `interpretation.functions.sacred_object` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.sacred_object` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0118` (high) — `interpretation` / `interpretation.functions.sacrificial_body` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.sacrificial_body` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0119` (high) — `cmt` / `cmt.cluster_id` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.cluster_id` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0120` (high) — `cmt` / `cmt.source_domain_primary` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.source_domain_primary` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0121` (high) — `cmt` / `cmt.source_domain_secondary` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.source_domain_secondary` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0122` (high) — `cmt` / `cmt.target_domain` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.target_domain` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0123` (high) — `interpretation` / `interpretation.functions.purification` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.purification` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0124` (high) — `interpretation` / `interpretation.functions.sacred_object` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.sacred_object` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0125` (high) — `interpretation` / `interpretation.functions.sacrificial_body` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.sacrificial_body` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0126` (medium) — `interpretation` / `interpretation.functions.violence_logic` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.violence_logic` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0127` (medium) — `interpretation` / `interpretation.functions.violence_logic` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.violence_logic` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0128` (medium) — `interpretation` / `interpretation.functions.violence_logic` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.functions.violence_logic` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0129` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.conceptual_metaphor` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0130` (medium) — `cmt` / `cmt.entailments` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.entailments` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0131` (medium) — `interpretation` / `interpretation.functions.enemy_as_bringer_of_death` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.enemy_as_bringer_of_death` for `lincoln-ann-003`, and is the packet or submission guidance incomplete?
- `review-0132` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.conceptual_metaphor` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0133` (medium) — `cmt` / `cmt.entailments` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.entailments` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0134` (medium) — `interpretation` / `interpretation.functions.enemy_as_bringer_of_death` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.enemy_as_bringer_of_death` for `lincoln-ann-017`, and is the packet or submission guidance incomplete?
- `review-0135` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-second-inaugural`: Why did one or more runs omit `cmt.conceptual_metaphor` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0136` (medium) — `cmt` / `cmt.entailments` / `lincoln-second-inaugural`: Why did one or more runs omit `cmt.entailments` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0137` (medium) — `interpretation` / `interpretation.functions.enemy_as_bringer_of_death` / `lincoln-second-inaugural`: Why did one or more runs omit `interpretation.functions.enemy_as_bringer_of_death` for `lincoln-ann-064`, and is the packet or submission guidance incomplete?
- `review-0138` (medium) — `interpretation` / `interpretation.functions.violence_logic` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.violence_logic` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0139` (medium) — `interpretation` / `interpretation.functions.violence_logic` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.violence_logic` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0140` (medium) — `interpretation` / `interpretation.functions.violence_logic` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.violence_logic` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0141` (medium) — `interpretation` / `interpretation.functions.violence_logic` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.violence_logic` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0142` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.conceptual_metaphor` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0143` (medium) — `cmt` / `cmt.entailments` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.entailments` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0144` (medium) — `interpretation` / `interpretation.functions.enemy_as_bringer_of_death` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.enemy_as_bringer_of_death` for `lincoln-ann-051`, and is the packet or submission guidance incomplete?
- `review-0145` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.conceptual_metaphor` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0146` (medium) — `cmt` / `cmt.entailments` / `lincoln-gettysburg-address`: Why did one or more runs omit `cmt.entailments` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0147` (medium) — `interpretation` / `interpretation.functions.enemy_as_bringer_of_death` / `lincoln-gettysburg-address`: Why did one or more runs omit `interpretation.functions.enemy_as_bringer_of_death` for `lincoln-ann-054`, and is the packet or submission guidance incomplete?
- `review-0148` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.conceptual_metaphor` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0149` (medium) — `cmt` / `cmt.entailments` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.entailments` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0150` (medium) — `interpretation` / `interpretation.functions.enemy_as_bringer_of_death` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.enemy_as_bringer_of_death` for `lincoln-ann-016`, and is the packet or submission guidance incomplete?
- `review-0151` (medium) — `cmt` / `cmt.conceptual_metaphor` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.conceptual_metaphor` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0152` (medium) — `cmt` / `cmt.entailments` / `lincoln-lyceum-address`: Why did one or more runs omit `cmt.entailments` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0153` (medium) — `interpretation` / `interpretation.functions.enemy_as_bringer_of_death` / `lincoln-lyceum-address`: Why did one or more runs omit `interpretation.functions.enemy_as_bringer_of_death` for `lincoln-ann-043`, and is the packet or submission guidance incomplete?
- `review-0154` (low) — `cmt` / `confidence` / `lincoln-lyceum-address`: Which value for `confidence` on `lincoln-ann-003` best follows the codebook and source context?
- `review-0155` (low) — `cmt` / `confidence` / `lincoln-lyceum-address`: Which value for `confidence` on `lincoln-ann-017` best follows the codebook and source context?
- `review-0156` (low) — `cmt` / `confidence` / `lincoln-second-inaugural`: Which value for `confidence` on `lincoln-ann-064` best follows the codebook and source context?
- `review-0157` (low) — `cmt` / `confidence` / `lincoln-gettysburg-address`: Which value for `confidence` on `lincoln-ann-051` best follows the codebook and source context?
- `review-0158` (low) — `cmt` / `confidence` / `lincoln-gettysburg-address`: Which value for `confidence` on `lincoln-ann-054` best follows the codebook and source context?
- `review-0159` (low) — `cmt` / `confidence` / `lincoln-lyceum-address`: Which value for `confidence` on `lincoln-ann-016` best follows the codebook and source context?
- `review-0160` (low) — `cmt` / `confidence` / `lincoln-lyceum-address`: Which value for `confidence` on `lincoln-ann-043` best follows the codebook and source context?

## Interpretation limits

- Consensus may reflect shared model bias or shared prompt effects.
- Reference support is diagnostic alignment, not independent evidence.
- Reference challenges require human source and codebook review.
- Undefined or sparse metrics are reported as insufficient data.
- Invalid submissions remain visible but are not pooled into agreement metrics.

No count, metric, consensus pattern, or reference-alignment result in this report may update an accepted annotation without human review.
