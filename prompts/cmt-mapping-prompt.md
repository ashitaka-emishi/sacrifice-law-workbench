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

Produce the `cmt` portion of an annotation instance:

- top-level `mipvu_ids`;
- `cluster_id`;
- `source_domain`;
- `target_domain`;
- `mapping`;
- `entailments`;
- `linguistic_form`;
- `metaphoricity`;
- `is_extended_metaphor`;
- `extension_group_id`;
- `co_activated_clusters`;
- CMT-specific uncertainty notes.

## Quality Criteria

- Do not infer psychological meaning in this step.
- Do not create CMT evidence from a span that lacks MIPVU support unless the
  annotation is explicitly exploratory.
- Do not assign a cluster because it is theoretically attractive.
- Do not treat topic words as metaphor without a source-target mapping.
- Preserve weak, ambiguous, or rejected mappings as review notes when useful.
