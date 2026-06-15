# MIPVU Annotation Guide

This guide defines the first-pass metaphor-identification layer for the
workbench. MIPVU decisions come before CMT mapping and Koenigsbergian
interpretation.

MIPVU answers a narrow question:

> Is this lexical unit metaphor-related in this context?

It does not answer whether the passage supports Koenigsberg's Law of Sacrifice,
what conceptual metaphor is active, or whether a historical practice has been
enacted. Those are downstream questions.

## Workflow

1. Generate a source-language worklist:

   ```bash
   python3 scripts/generate-mipvu-worklist.py --case <case-id>
   ```

2. Review every lexical unit in
   `cases/<case>/corpus/mipvu/<document_id>_mipvu.json`.
3. Assign one `decision_type` to every lexical unit.
4. Add detailed rationale for metaphor-related or uncertain decisions.
5. Create CMT/Koenigsbergian annotations only from MIPVU-positive or uncertain
   lexical units.

For a pilot, training, or reliability sample, review complete sentences rather
than isolated exciting words. Every lexical unit in the sampled sentence should
receive a decision. Non-metaphor decisions may remain brief; metaphor-related
and uncertain decisions require the full rationale fields below.

## Decision Types

- `non_metaphor`: contextual meaning does not contrast with a more basic
  meaning in a metaphorically relevant way.
- `mipvu_indirect`: contextual meaning contrasts with a more basic meaning and
  can be understood by comparison with it.
- `mipvu_direct`: direct metaphor, simile, analogy, or explicit comparison.
- `mipvu_implicit`: omitted or implied lexical material is metaphor-related.
- `mipvu_personification`: nonhuman entity is construed through human agency,
  emotion, body, or action.
- `uncertain`: evidence is insufficient or contested; preserve the uncertainty.
- `excluded_nonlexical`: generated item should not have been treated as a
  lexical unit.

Do not use `mipvu_indirect`, `mipvu_direct`, `mipvu_implicit`, or
`mipvu_personification` merely because a term is theoretically interesting.
The contextual meaning must contrast with a more basic meaning and be
understandable by comparison with it. If that contrast is plausible but not
settled, use `uncertain`.

## Required Rationale

For `mipvu_indirect`, `mipvu_direct`, `mipvu_implicit`,
`mipvu_personification`, and `uncertain`, fill in:

- `contextual_meaning`
- `basic_meaning`
- `basic_meaning_source`
- `contrast_explanation`
- `comparison_basis`
- `confidence`
- `review_notes`

Manual dictionary/source citation is the v1 policy. The citation can name a
dictionary, critical edition note, scholarly lexicon, or other basic-meaning
source used by the annotator.

When a term is listed in
`cases/lincoln/references/historical-semantics-notes.md`, also fill:

- `semantic_shift_risk`
- a `review_notes` explanation of how the period-control note affected the
  decision

Candidate source/target domain hints may be recorded for later CMT review, but
they do not replace the MIPVU decision. CMT mappings should still be made in
their own layer.

## Review Status

- `pending`: lexical unit has not been reviewed.
- `needs_review`: annotator has flagged the unit for later review but has not
  accepted a decision.
- `reviewed`: annotator has made a first-pass decision.
- `accepted`: decision has passed adjudication or final human review.
- `rejected`: prior decision was reviewed and rejected.

Validation treats any non-`pending` unit as intentionally reviewed. Reviewed,
accepted, rejected, or needs-review units must have a valid `decision_type`.
Metaphor-related and uncertain decisions must also have all required rationale
fields.

## Lincoln Pilot Sample

The current Lincoln pilot sample is documented in
`cases/lincoln/metadata/mipvu-pilot-sample.json`.

It reviews full sentences from:

- the Lyceum Address live/die/suicide national survival formulation;
- the Gettysburg Address burial/sacrifice/national life sentence;
- the Gettysburg Address final dedication/new birth sentence;
- the Second Inaugural blood repayment/divine judgment sentence.

This sample demonstrates the workflow and creates a future reliability target.
It does not complete MIPVU review for the Lincoln corpus.

## Language Policy

German and French documents are annotated in the source language. Add
`gloss_en` only as an analytical aid. Do not make the MIPVU decision on an
English gloss when the source text is German or French.

Use `gloss_notes` when translation choices affect the source-domain mapping,
especially for politically loaded words such as *Volk*, *Opfer*, *Vernichtung*,
*gloire*, *patrie*, *honneur*, or *sacrifice*.

## Uncertainty

Use `uncertain` when:

- basic and contextual meanings are difficult to separate;
- OCR or translation risk affects the lexical unit;
- the unit may be conventional but still politically active;
- multiple source-domain readings remain plausible.

Uncertain MIPVU decisions may support exploratory CMT annotations, but aggregate
claims should report rates with and without uncertain units.
