# Lincoln Reliability Report

Status: sample defined; independent double-coding pending.

## Scope

This report covers MIPVU metaphor-identification reliability for the Lincoln
pilot corpus. It does not assess CMT mapping, Koenigsbergian interpretation, or
historical corroboration.

## Samples

Training sample: `lincoln-pilot-v1`, documented in
`cases/lincoln/metadata/mipvu-pilot-sample.json`, 192 lexical units.

Reliability sample: `lincoln-reliability-v1`, documented in
`cases/lincoln/quality/reliability-sample.json`, 467 lexical units across seven
complete sentences. The sample is 10.3% of the 4,536 Lincoln lexical-unit
worklist and does not overlap the training sample.

## Procedure

Two coders independently code every lexical unit in the reliability sample from
the generated MIPVU worklist. Coders use the same codebook and historical
semantics notes, but do not inspect one another's decisions before agreement is
calculated.

The primary agreement measure is Cohen's kappa for the binary decision
`metaphor-related` versus `not metaphor-related`. For this measure,
`mipvu_indirect`, `mipvu_direct`, `mipvu_implicit`, `mipvu_personification`, and
`uncertain` count as metaphor-related.

The secondary measure is percent agreement on the full `decision_type` label.
It is reported because sparse multi-class labels make early kappa values
unstable, while full-label agreement remains useful for codebook revision.

## Adjudication

All disagreements are logged in
`cases/lincoln/quality/adjudication-log.csv`. Each disagreement receives one
primary category:

- `lexical_segmentation`
- `contextual_meaning`
- `basic_meaning`
- `metaphor_decision`
- `confidence`
- `source_domain_ambiguity`

Adjudication records the final decision, rationale, date, and any required
codebook change.

## Results

Independent coder files have not yet been produced. Do not cite reliability
statistics until this section records coder agreement, adjudication outcomes,
and post-adjudication codebook changes.

## Limitations

The current artifact makes the reliability workflow runnable and auditable, but
it is not itself a completed reliability study. Publication-facing claims should
state that reliability is pending until double-coding and adjudication are
complete.
