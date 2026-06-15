# MIPVU Annotation Guide

This guide defines the first-pass metaphor-identification layer for the
workbench. MIPVU decisions come before CMT mapping and Koenigsbergian
interpretation.

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
