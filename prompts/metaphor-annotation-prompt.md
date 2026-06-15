# Metaphor Annotation Prompt

## Purpose

Annotate metaphor candidates in a segmented case document while preserving
traceability, uncertainty, and the distinction between CMT evidence and
Koenigsbergian interpretation.

## Inputs

- Case ID and document metadata.
- Segmented JSON with stable sentence IDs.
- MIPVU lexical-unit worklist or reviewed MIPVU decisions for the document.
- Case cluster configuration.
- Source registry or citation metadata.
- Any case-specific annotation notes.

## Workflow

1. Read the document metadata before annotating. Note register, phase,
   authorship confidence, source risk, and translation risk.
2. Review the MIPVU lexical-unit decisions before creating any CMT annotation.
   Do not create an interpretive annotation unless it is backed by one or more
   MIPVU lexical units marked metaphor-related or uncertain, unless explicitly
   marking the instance as exploratory.
3. Work sentence by sentence. Do not renumber or rewrite sentence IDs or MIPVU
   IDs.
4. Identify candidate metaphor spans from MIPVU-positive or uncertain lexical
   units using textual evidence only.
5. For each candidate, record the exact sentence ID, span text, document ID,
   case ID, and supporting `mipvu_ids`.
6. Complete the CMT layer before adding psychological interpretation:
   source domain, target domain, mapping, entailments, linguistic form,
   metaphoricity, extension group, and co-activated clusters.
7. Add Koenigsbergian fields only after the CMT evidence is clear.
8. Record absence or suppression only when the searched scope is explicit.
9. Assign confidence and ambiguity notes. Preserve uncertainty rather than
   forcing a cluster.

## Output

Return annotation JSON compatible with `schemas/annotation-schema.json`, either
embedded in the sentence's `metaphor_instances` array or as instance objects
that can be merged into the annotated document.

Each instance must include:

- `instance_id`;
- `case_id`;
- `document_id`;
- `sentence_id`;
- `span_text`;
- `mipvu_ids`;
- `cmt.cluster_id`;
- `koenigsberg` interpretation fields where supported;
- `meta.confidence`;
- ambiguity, suppression, and uncertainty notes where relevant.

## Language policy

Check `case-config.json` for `source_language` and `annotation_language_policy` before annotating.

### French-language cases (napoleon): source-with-glosses

When `annotation_language_policy` is `"source-with-glosses"`:

- Record `span_text` exactly as it appears in the French source — do not translate it.
- Reference source-language MIPVU lexical-unit IDs, not English gloss tokens.
- Add `gloss_en`: a working English rendering of the span sufficient for CMT source-domain assignment. This is an analytical aid, not a publication translation.
- Add `gloss_notes` when the translation choice materially affects the CMT mapping — particularly for: *gloire* (glory/renown), *sacrifice* (sacrifice/offering), *patrie* (fatherland/homeland), *honneur* (honor), *victoire* (victory), *mort* / *mourir* (death/to die), *sang* (blood). Note the range of plausible English renderings and which source domain each would activate.
- Proceed with CMT and Koenigsbergian fields as normal, reasoning from the French meaning anchored by the gloss.
- Do not introduce a machine translation as if it were the source text. The French is the source text.

## Quality Criteria

- Every annotation is traceable to a sentence ID and source span.
- Every normal annotation is traceable to one or more MIPVU lexical-unit IDs.
- CMT evidence is not mixed with later interpretation.
- Confidence reflects actual evidentiary strength.
- Absence claims state their scope.
- No diagnostic claim or private mental-state claim is made from isolated text.
- For French-language cases: `gloss_en` is present on every instance; `gloss_notes` is present whenever translation choice affects domain mapping.
