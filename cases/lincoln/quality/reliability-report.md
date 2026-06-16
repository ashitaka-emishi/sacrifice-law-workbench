# Lincoln Reliability Report

Status: Codex-assisted review gate complete; independent human double-coding
still recommended before publication-facing reliability claims.

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

Review packets are generated under `cases/lincoln/quality/review-packets/`:

- `lincoln-full-corpus-review.csv` supports full-corpus MIPVU review.
- `lincoln-reliability-v1-coder-a.csv` and
  `lincoln-reliability-v1-coder-b.csv` are independent coder templates for the
  reliability sample.
- `lincoln-reliability-v1-adjudication-template.csv` provides the adjudication
  schema for disagreements after coder comparison.

The completed v1 gate also writes:

- `cases/lincoln/quality/reliability-results.json`
- `cases/lincoln/quality/adjudication-log.csv`

The completed packets are labeled as Codex-assisted first-pass artifacts. They
support an auditable issue gate and downstream pipeline development, but they
do not replace independent human double-coding for publication claims.

## Procedure

The intended publication procedure is two human coders independently coding
every lexical unit in the reliability sample from the generated MIPVU worklist.
Coders use the same codebook and historical semantics notes, but do not inspect
one another's decisions before agreement is calculated.

For the issue #22 implementation gate, `scripts/complete-lincoln-mipvu-review.py`
produced a Codex-assisted full-corpus first pass, a second-pass coder packet
with selected borderline divergences, and an adjudication log. These artifacts
are explicitly provisional and should be human-reviewed before reliability
statistics are cited as scholarly evidence.

After both coder packets are completed, calculate agreement with:

```bash
python3 scripts/calculate-mipvu-reliability.py \
  --coder-a cases/lincoln/quality/review-packets/lincoln-reliability-v1-coder-a.csv \
  --coder-b cases/lincoln/quality/review-packets/lincoln-reliability-v1-coder-b.csv \
  --out cases/lincoln/quality/reliability-results.json
```

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

Codex-assisted issue-gate results:

| Measure | Result |
|---|---:|
| Reliability sample units | 467 |
| Binary metaphor-related percent agreement | 97.0% |
| Binary metaphor-related Cohen's kappa | 0.784 |
| Full `decision_type` percent agreement | 95.5% |
| Full `decision_type` disagreements | 21 |

All 21 disagreements are recorded in
`cases/lincoln/quality/adjudication-log.csv` and were adjudicated back to the
full-corpus first-pass decision. The most common disagreement pattern is
borderline metaphor/uncertain classification in historically controlled
phrases such as material inheritance, public memory, attachment/alienation, and
healing language.

Full-corpus first-pass MIPVU summary:

| Decision type | Units |
|---|---:|
| `non_metaphor` | 4,334 |
| `mipvu_direct` | 86 |
| `mipvu_indirect` | 78 |
| `mipvu_personification` | 26 |
| `uncertain` | 12 |

No Lincoln lexical units remain `pending`.

## Limitations

The current artifacts make the reliability workflow runnable and auditable and
complete the issue #22 review gate. They are still not a completed human
reliability study. Publication-facing claims should state that the Lincoln
MIPVU layer has a Codex-assisted first-pass review and should withhold final
inter-annotator reliability claims until independent human double-coding and
human adjudication are complete.
