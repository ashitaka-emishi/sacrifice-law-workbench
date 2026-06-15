# Koenigsbergian Interpretation Prompt

## Purpose

Interpret validated CMT annotations through Koenigsbergian historical
psychology while keeping evidence, interpretation, inference, speculation, and
open questions separate.

## Inputs

- Completed CMT annotation.
- Sentence text and local document context.
- Document metadata, including register, phase, authorship, and source risks.
- Case cluster configuration and relevant case notes.

## Workflow

1. Start from the CMT mapping. Do not reinterpret a span that lacks adequate
   metaphor evidence.
2. Identify the symbolic object at stake, if supported: nation, god, leader,
   ideology, law, race, army, revolution, or another sacred object.
3. Classify supported Koenigsbergian fields:
   fantasy type, magical object, violence logic, guilt distribution,
   obligatory frame, sacrificial economy, psychic defense, projected entity,
   and exit condition.
4. Record how the metaphor organizes action: care, purification, restoration,
   punishment, sacrifice, extermination, reconciliation, or refusal.
5. Mark absence and suppression only when the searched scope is explicit.
6. State uncertainty and rival explanations, including genre, register,
   translation, formulaic language, or source-selection effects.
7. Classify each interpretive statement as evidence, interpretation, inference,
   speculation, or open question.

## Output

Produce the `koenigsberg`, `agency`, `action_orientation`, `absence`, and
interpretive note portions of an annotation instance.

## Prohibitions

- Do not diagnose historical actors.
- Do not infer private mental states from isolated metaphors.
- Do not claim monocausal explanations for war or genocide.
- Do not convert a theoretical possibility into a finding.
- Do not erase rival explanations when they remain plausible.

## Quality Criteria

The interpretation should be proportional to the annotation evidence, sensitive
to register and phase, and traceable to sentence IDs and source metadata.
