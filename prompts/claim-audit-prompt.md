# Claim Audit Prompt

## Purpose

Audit a draft claim for source-to-claim traceability, evidentiary status, and
methodological overreach.

## Inputs

- Draft claim or paragraph.
- Relevant source IDs, document IDs, sentence IDs, annotations, concordance
  entries, analysis artifacts, or validation artifacts.
- Case ID and corpus scope.
- Intended public artifact or section.

## Workflow

1. Identify the claim's evidentiary status: evidence, interpretation,
   inference, speculation, or open question.
2. Trace the claim to supporting artifacts. Name missing links explicitly.
3. Check whether the claim depends on balanced-core data, extended-corpus data,
   a single document, a register subset, or exploratory notes.
4. Check confidence thresholds and ambiguity notes.
5. Identify rival explanations, including register, genre, translation, source
   selection, chronology, or prompt bias.
6. Recommend one action: keep, qualify, demote, split, request more evidence,
   or remove.

## Output

Return a concise audit record:

- claim;
- evidentiary status;
- supporting artifacts;
- missing traceability links;
- rival explanations;
- overreach risks;
- recommended revision;
- readiness status: draft, reviewed, finding, or deprecated.

## Quality Criteria

No claim should be promoted to a finding unless it is traceable, proportional,
and robust against obvious rival explanations.
