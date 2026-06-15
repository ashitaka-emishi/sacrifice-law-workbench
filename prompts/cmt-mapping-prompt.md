# CMT Mapping Prompt

## Purpose

Map metaphor annotations using Conceptual Metaphor Theory before any
Koenigsbergian interpretation is added.

## Inputs

- Sentence text and sentence ID.
- Candidate span text.
- Supporting MIPVU lexical-unit IDs and decisions.
- Case cluster list.
- Document metadata, including register and phase.
- Nearby context if needed for entailments or extended metaphor.

## Workflow

1. Confirm that the span is backed by one or more MIPVU lexical units marked
   metaphor-related or uncertain.
2. Review the MIPVU contextual meaning, basic meaning, contrast explanation,
   and comparison basis before assigning a CMT mapping.
3. Identify the source domain and target domain.
4. State the mapping as source-to-target correspondences.
5. List entailments that are directly supported by the text.
6. Classify the linguistic form.
7. Mark whether the metaphor is conventional, active, novel, extended, or part
   of a co-activated cluster pattern.
8. Select the best case cluster only when the mapping supports it. If no
   configured cluster fits, mark the annotation as provisional and explain why.
9. Assign confidence and ambiguity notes.

## Output

Produce a CMT mapping record for
`cases/<case>/corpus/cmt/cmt-mappings.json`:

- `mapping_id`;
- `case_id`;
- `document_id`;
- `sentence_id`;
- `mipvu_ids`;
- `expression`;
- `source_domain_primary`;
- `source_domain_secondary`;
- `target_domain`;
- `conceptual_metaphor`;
- `entailments`;
- `cluster_id`;
- `confidence`;
- `rival_reading`;
- `justification`;
- `mapping_status`;
- optional rhetorical, ideological, salience, and diachronic fields.

Downstream annotation instances may cite `cmt.mapping_id`, but the mapping
record itself is the durable source-target evidence table.

## Quality Criteria

- Do not infer psychological meaning in this step.
- Do not create CMT evidence from a span that lacks MIPVU support unless the
  annotation is explicitly exploratory.
- Do not assign a cluster because it is theoretically attractive.
- Do not treat topic words as metaphor without a source-target mapping.
- Preserve weak, ambiguous, or rejected mappings as review notes when useful.
