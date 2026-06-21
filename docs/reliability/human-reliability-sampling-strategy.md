# Stratified Human Reliability Sampling Strategy

Strategy version: `1.0.0`

Status: approved design contract; no new human reliability sample is selected
or released by this document.

This strategy operationalizes the
[human reliability architecture](human-reliability-architecture.md) for
selecting blind double-coding samples across cases, source languages, phases,
genres/registers, task layers, ambiguity, provenance risk, and claim
importance. It defines what a case-local sample manifest must record before
issue #79 generates deterministic blind packets.

Sampling measures whether qualified coders can apply the method consistently.
It does not estimate metaphor prevalence, prove an interpretation, or turn the
accepted reference into ground truth.

## Analysis unit and cohort boundary

Sampling is declared separately for every:

```text
case × source language × task layer × sample version
```

The task layers are:

- `identification`: MIPVU category, lexical boundary, semantic rationale,
  confidence, and uncertainty;
- `cmt`: source and target domains, mapping, entailments, cluster, and rival
  reading; and
- `interpretation`: bounded Koenigsbergian functions, violence/obligation,
  agency/absence, confidence, uncertainty, and rivals.

Results remain cohort-specific. A completed English identification cohort
cannot support a French CMT claim, and an interpretation cohort cannot be
pooled with identification merely because the same sentences appear.

## Sampling frame gate

Freeze the eligible frame before selection. Its manifest records:

- stable document, sentence, lexical-unit, span, mapping, and annotation IDs;
- source language, phase, genre/register, date, and case;
- task-layer eligibility and adequate context scope;
- reference-derived design roles held only by the coordinator;
- ambiguity, provenance risk, rights/storage restriction, and claim impact;
- training, calibration, prior-exposure, and other exclusions;
- frame count and a deterministic hash; and
- codebook and source-artifact versions.

Do not select from a frame while identifiers are changing, required context is
missing, or the intended coders lack lawful source access. The public-safe
Hitler reference index can verify committed IDs, but it cannot supply the
source text needed to create or code a packet.

## Selection method

Use reproducible two-stage stratified selection:

1. Allocate minimum coverage across case-local phase and genre/register
   strata, then across documents.
2. Select within each allocation using a recorded pseudorandom seed and stable
   ID ordering.

Coordinator-held design roles may be used for allocation, but packet order is
reshuffled deterministically and roles never enter coder-facing files.
Selection code must produce the same IDs from the same frame hash, strategy
version, and seed.

### Coverage rules

- Include every eligible phase and genre/register where the frame permits.
- Include at least two documents per phase or register when two exist.
- Prevent one document from supplying more than 35% of items unless the frame
  is smaller or the deviation is justified.
- Include ordinary negative controls, reference-positive items, ambiguous
  items, provenance-risk items, and high-impact items.
- Cap high-impact items at 30% so reliability is not measured only on passages
  selected to support major claims.
- Target 15–25% ambiguous items when the frame permits.
- Target 10–20% material provenance/source-quality risk, with an explicit
  `out_of_scope` path.
- Match high-impact items with negative or rival controls from a comparable
  phase, register, or rhetorical setting when possible.

The categories overlap. An ambiguous high-impact item may satisfy both quotas,
but the manifest retains every role so coverage is not inferred from a single
label.

## Layer-specific units and sample sizes

The thresholds below are design floors, not automatic claims of statistical
power. Every report must include observed prevalence, confidence intervals or
other uncertainty appropriate to the metric, and the achieved frame/sample
counts.

### Size rationale

The floors balance diagnostic precision, sentence clustering, rare categories,
and feasible expert coding:

- With 400 independent binary decisions, the worst-case standard error for a
  raw agreement proportion is about 2.5 percentage points. Lexical units
  within a sentence are not independent, so analysis must use sentence-aware
  uncertainty or a design-effect adjustment rather than claiming that nominal
  precision.
- Thirty sentence clusters reduces dependence on a handful of unusually long
  sentences and permits a minimally useful cluster bootstrap or
  leave-one-sentence sensitivity analysis.
- Fifty positive-or-uncertain focal units has a worst-case raw-proportion
  standard error of about 7 percentage points. This is a diagnostic floor for
  rare-category agreement, not a high-precision endpoint.
- Sixty CMT or interpretive items has a worst-case raw-proportion standard
  error of about 6.5 percentage points. Smaller frames therefore use a census
  and retain visibly wider uncertainty rather than borrowing items from
  incomparable cohorts.

These calculations do not account for weighting, missingness, coder
dependence, or multi-category metrics; the final analysis must do so.

### Identification and lexical boundaries

The primary sampling unit is a complete segmented sentence. Both coders code
every lexical unit in each selected sentence. This preserves ordinary negative
controls and prevents focal-word selection from revealing expected answers.

For a normal-sized frame, target:

- at least 400 lexical units;
- at least 30 complete sentences;
- at least 50 reference-positive or uncertain focal units distributed across
  selected sentences when the frame permits; and
- at least 300 ordinary reference-negative lexical units.

Positive and ambiguous strata are deliberately enriched because rare-category
agreement cannot be assessed from a purely proportional sample. Therefore:

- do not use this sample to estimate corpus metaphor prevalence;
- report positive agreement and negative agreement separately;
- report results by design stratum as well as overall; and
- qualify kappa or similar prevalence-sensitive metrics.

No selected sentence should provide more than 10% of sampled lexical units
unless the sentence is indivisible and the deviation is recorded.

### CMT mapping

The unit is one source span with enough context to assess a mapping. Include
accepted-reference candidates, plausible negative/decoy spans, ambiguous or
rival mappings, and high-impact mappings without revealing those roles.

Target at least 60 items. If the eligible mapping frame contains fewer than 60
items, use a census plus deterministically selected negative source spans from
the same lawful case corpus where the codebook permits them. Do not invent
historical text or reuse training examples. Report the small-frame limitation;
do not manufacture a publication-grade reliability claim from an inadequate
frame.

### Interpretation, violence/obligation, agency/absence

The unit is one bounded source context with an explicit interpretation or
absence search scope. Sample fields independently rather than selecting only
passages where all expected functions are present.

Target at least 60 items, including:

- present, absent, uncertain, and not-applicable opportunities;
- literal violence without sacrificial interpretation;
- obligation and strong preference controls;
- explicit and suppressed agency;
- adequate-scope and inadequate-scope absence questions; and
- rival explanations for high-impact interpretations.

If fewer than 60 eligible contexts exist, use a census and scope the result to
the executed fields and frame.

## Small frames, censuses, and adaptive expansion

Use a census when the eligible frame is below the layer target. Do not pool
languages or task layers merely to reach a number.

After both independent submissions are frozen, a predeclared adaptive
expansion may add a second packet when:

- a required stratum has fewer than five usable items;
- out-of-scope or invalid responses remove more than 10% of the sample;
- positive or negative agreement is not estimable; or
- a metric is undefined because one category was not observed.

Expansion uses a new sample version and seed, excludes previously coded items,
and preserves the first sample's results. It cannot be chosen after inspecting
which answer would improve agreement.

## Exclusions and contamination

Always exclude:

- training and calibration examples;
- items previously shown to a coder with answer keys or accepted decisions;
- invalid, unstable, duplicate, or superseded identifiers;
- contexts too short for the assigned task;
- material the cohort cannot lawfully receive;
- source-language items outside declared coder competence; and
- packet-construction defects discovered before release.

Record exclusions by stable ID and controlled reason. Do not silently replace
an excluded item after packet release. A replacement creates a new sample and
packet version.

Prior exposure is coder-specific. Public repository availability alone does
not prove exposure, but a coder who inspected accepted decisions, prior
packets, results, or adjudication for an item cannot blind-code it.

## Lincoln continuity decision

The existing `lincoln-reliability-v1` artifact remains unchanged as an
auditable Codex-assisted prior-review sample. Its seven sentences and 467
lexical units satisfy the new lexical-unit floor but not the 30-sentence
diversity floor, and public prior-review results create a contamination risk.

For a new independent human Lincoln identification cohort:

1. Preserve the seven IDs as a declared `legacy_continuity_reserve`.
2. Reuse an ID only when both primary coders attest no prior answer exposure.
3. Otherwise select a deterministic matched replacement and record
   `prior_public_answer_exposure_risk` as the deviation reason.
4. Add enough newly selected sentences to reach the diversity and stratum
   floors.
5. Keep the four-sentence `lincoln-pilot-v1` training sample excluded.

The old Codex-assisted agreement values remain historical workflow evidence
and do not enter human-human agreement.

## Current case execution constraints

| Case | Language | Sampling implication |
|---|---|---|
| Lincoln | English | Public-domain frame is executable; retain legacy sample only under the continuity rules above. |
| American Revolution | English | Identification frame includes reviewed and pending units; final selection must freeze review status and reconcile phase/genre metadata before allocation. |
| Napoleon | French | Requires qualified French coders; the current corpus is concentrated in peak empire with one late-empire document, so claims cannot imply full diachronic coverage. |
| Hitler | German | Requires qualified German coders with authorized local access and secure storage; the public-safe ID index alone is insufficient for packet generation. |

If two qualified independent coders are unavailable for a case-language-layer,
set the cohort to `planned_not_executable`. Do not substitute English gloss
coding, model outputs, a single coder, or a coder outside the declared
competence. Reports may say that the cohort was not executed; they may not
generalize reliability from another cohort.

## Manifest and blindness contract

The access-controlled coordinator manifest conforms to
[`sample-manifest-schema.json`](../../schemas/human-reliability/sample-manifest-schema.json).
The repository also provides a
[`sample-manifest-template.json`](sampling/sample-manifest-template.json).

The manifest may record hidden design roles and reference-derived allocation
metadata. Keep that role-bearing manifest unavailable to primary coders until
both independent submissions are frozen. A public or coder-visible sample
receipt may contain only neutral IDs, versions, hashes, language, layer, and
rights instructions. Issue #79 must generate coder packets through an
allowlist that
excludes:

- design roles and stratum labels that imply an answer;
- accepted decisions, mappings, interpretations, support scores, and claim
  statuses;
- prior coder/model values, agreement results, and adjudication; and
- selection rationales naming positive, negative, ambiguous, or high-impact
  status.

Sample approval requires a coordinator who did not alter item decisions merely
to satisfy quotas. Freeze the manifest before packet generation, retain its
canonical hash (computed with `approval.manifest_sha256` set to `null`), and
report every later deviation. Publish the role-bearing manifest only after the
blind phase ends, and only when its rights policy permits publication.
