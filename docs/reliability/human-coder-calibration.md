# Human Coder Calibration Packets

Calibration version: `1.0.0`

Status: training-only preparation for source-language human-reliability
cohorts. These packets are not reliability samples, accepted annotations, or
evidence about any historical case.

Complete the [human coder training guide](human-coder-training-guide.md) before
using these packets. The invented examples have stable `calibration-synthetic-`
IDs and must never enter a reliability sample, blind study packet, accepted
annotation, model test, or adjudication queue.

## Packet set

| Source language | Coder packet | Coordinator-held key |
|---|---|---|
| English | [English packet](calibration/packets/en.md) | [English key](calibration/answer-keys/en.md) |
| French | [French packet](calibration/packets/fr.md) | [French key](calibration/answer-keys/fr.md) |
| German | [German packet](calibration/packets/de.md) | [German key](calibration/answer-keys/de.md) |

These languages cover the currently planned source-language cohorts. Before
executing a cohort in another language, add and review a packet and key in that
language. A translation of an existing packet is not sufficient evidence of
source-language calibration.

Every packet includes exercises for:

- metaphor-positive identification and boundaries;
- literal negative control identification;
- materially ambiguous identification;
- CMT mapping and rival readings;
- bounded interpretation, including violence or obligation; and
- agency and absence with an explicit search scope.

Coder-facing packets identify the assigned task but do not reveal whether an
item is a positive, negative, or ambiguous control. Those design roles appear
only in the separate answer keys.

## Administration

1. Assign only the packet matching the coder's declared source-language
   competence.
2. Record packet ID, version, training version, and codebook version.
3. Give the coder the packet without its answer key.
4. Require an independent first pass. Do not coach item-level answers.
5. Freeze or retain the first-pass responses before discussion.
6. Compare the responses with the coordinator-held key. The key defines an
   acceptable reasoning range, not hidden ground truth.
7. Discuss disagreements, gloss effects, uncertainty, and `out_of_scope`
   choices without using live reliability items.
8. Require a second explanation or targeted exercise when a critical
   distinction remains misunderstood.
9. Record the outcome using
   [`completion-register-template.json`](calibration/completion-register-template.json).
10. Release a blind reliability packet only after the registered qualification
    decision permits it.

Do not pool calibration scores across languages. Do not substitute a high
overall percentage for a failed critical control: guessing rather than using
`out_of_scope`, allowing a gloss to control a source-language decision,
conflating literal violence with sacrifice, or inferring document-wide absence
from an inadequate excerpt requires remediation.

## Completion record

The shared JSON file is a template, not an executed study record. For an
executed cohort, copy its fields into:

```text
cases/<case_id>/quality/human-reliability/calibration/completion-register.json
```

Use pseudonymous coder IDs and one immutable entry per attempt. Record:

- cohort, coder role, source language, packet and guide versions;
- completion time and retained first-pass response hash;
- item dispositions and coordinator notes;
- critical-control and remediation outcomes;
- qualification decision and authorizing coordinator; and
- contamination, conflict, access, or rights incidents.

`qualified` means prepared for the declared cohort and task layers; it is not a
claim that the coder is correct, interchangeable across languages, or entitled
to inspect accepted decisions. `remediation_required` blocks blind packet
release until a later completed attempt is registered. `not_qualified` remains
visible and must not be overwritten.

## Separation and contamination rules

- Store keys away from coder-facing packet distribution.
- Never derive these keys from accepted case annotations.
- Never reuse calibration items in reliability sampling.
- Never include another coder's response in calibration materials.
- Never edit a first-pass response after discussion; register a later attempt.
- Treat accidental key exposure as contamination and record it.
- Keep historical source text and restricted material out of this shared
  synthetic packet set.

Calibration establishes readiness to begin independent coding. It does not
contribute observations to human-human agreement, human-vs-reference
comparison, or adjudication.
