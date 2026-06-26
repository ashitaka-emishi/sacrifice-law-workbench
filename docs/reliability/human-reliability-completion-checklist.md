# Human Reliability and Adjudication Completion Checklist

This is the final milestone gate for human inter-annotator reliability and
adjudication. It is intentionally stricter than `designed`, `partial`, or
`awaiting-adjudication` status. A case, source language, task layer, and cohort
may support a publication-ready human reliability claim only when every relevant
artifact, authority boundary, publication disclosure, and repository validation
check below passes.

The checklist is cohort-scoped. Do not use one complete cohort to certify a
different case, language, task layer, sample, packet version, codebook version,
or coder population. Incomplete cases and languages remain draft disclosures,
not reliability evidence.

## Cohort identity and scope gate

- [ ] The cohort manifest names the case, source language, task layer, sample
  ID and version, packet ID and hash, codebook version, training version, and
  calibration requirement.
- [ ] The scope statement lists every case, language, layer, and cohort that is
  complete.
- [ ] Cases, languages, layers, or cohorts that are absent, designed, partial,
  invalid, awaiting adjudication, unresolved, local-only, or rights-withheld are
  listed separately as incomplete or limited.
- [ ] No aggregate or public sentence implies that a completed cohort covers an
  unrun case, unrun language, unrun layer, changed packet, changed codebook, or
  different coder population.
- [ ] Any cross-case, cross-language, or cross-layer summary keeps the original
  cohort rows visible and states why pooling is methodologically justified.

## Training and calibration gate

- [ ] Each primary coder completed the relevant human coder training guide
  before coding the study packet.
- [ ] Each primary coder completed the required language-specific calibration
  packet before coding the study packet.
- [ ] Calibration answer keys, completion records, and training versions are
  recorded without exposing study answers inside blind packets.
- [ ] Source-language cohorts use coders with documented source-language
  competence; English glosses are not treated as a substitute for source
  qualification.
- [ ] Conflict, independence, and AI-assistance declarations are present for
  every coder and adjudicator role.

## Sample and blind packet gate

- [ ] The sample manifest records the approved stratified design, including
  source document, source language, task layer, design role, claim impact,
  ambiguity, provenance, and rights constraints.
- [ ] Study samples exclude calibration answers and keep accepted annotations,
  model outputs, adjudication outcomes, support scores, and synthesis claims out
  of coder packets.
- [ ] Packet manifests and packet payloads validate against schema and bind all
  primary coders in a cohort to the same packet hash.
- [ ] Packet payload rights and storage policies permit the intended local,
  repository, or public handling.
- [ ] Local-only or restricted packet material is disclosed by status and
  aggregate counts rather than copied into public artifacts.

## Two-coder submission gate

- [ ] At least two qualified independent primary coders submitted the same
  approved packet for the same cohort.
- [ ] Every counted submission is validated and normalized with matching cohort
  ID, cohort version, packet ID, packet hash, source language, task layer,
  training version, calibration ID, and assigned coder identity.
- [ ] Invalid submissions remain audit records and are excluded from agreement
  metrics.
- [ ] One valid coder, one valid coder plus a reference, one valid coder plus an
  adjudicator, prior Codex-assisted review, or a model run is never counted as
  two independent primary human coders.
- [ ] Missing, invalid, withdrawn, or rights-withheld submissions are reported
  as limitations and cannot be converted into agreement.

## Metrics and reference-comparison gate

- [ ] Human-human agreement metrics exist for every declared task layer and
  preserve field-level results, undefined-metric reasons, and denominator
  counts.
- [ ] Human-vs-reference comparison exists separately from human-human
  agreement.
- [ ] Reference comparison treats accepted annotations as comparison anchors,
  not infallible answer keys.
- [ ] Metrics do not pool across cases, languages, layers, packet versions, or
  codebook versions unless an explicit pooling design and retained cohort rows
  justify the summary.
- [ ] Reports do not claim that agreement proves historical correctness,
  interpretive truth, or scholarly reproducibility.

## Disagreement, adjudication, and codebook gate

- [ ] Disagreement logs classify pair splits, shared reference challenges,
  unavailable references, uncertainty differences, out-of-scope patterns,
  codebook ambiguity signals, source-language risk, and claim impact where
  present.
- [ ] The adjudication queue covers classified disagreements and preserves
  coder values, reference summaries, affected claims, priority reasons, and
  bounded review questions.
- [ ] Validated adjudication decisions exist for every queued disagreement that
  must be resolved before publication, or the unresolved items are explicitly
  listed as claim blockers.
- [ ] Adjudication outcomes remain separate from pre-adjudication agreement
  metrics and do not rewrite agreement scores.
- [ ] Codebook revision notes record proposed, accepted, rejected, or deferred
  implications from human reliability and adjudication results.
- [ ] Correction candidates remain proposals until a separate authorized
  promotion accepts, rejects, or defers them.

## Protected-path and authority gate

- [ ] Human-reliability commands write only beneath
  `cases/<case_id>/quality/human-reliability/`.
- [ ] Protected-path tests confirm that human-reliability tooling cannot write
  accepted annotations, MIPVU artifacts, CMT artifacts, analysis outputs,
  model-reliability artifacts, prior reliability artifacts, or publication
  outputs directly.
- [ ] Adjudication can create correction candidates but cannot silently modify
  canonical corpus, reference, analysis, claim, or publication artifacts.
- [ ] Any promoted correction has a separate authorization record, promotion
  decision, regenerated downstream artifacts, and explicit audit trail.
- [ ] Human agreement, reference comparison, adjudication, model agreement, and
  historical corroboration remain distinct claim families.

## Publication package gate

- [ ] `human-reliability-methodology.qmd` explains the design, blind execution,
  cohort scoping, rights limits, correction boundary, and publication limits.
- [ ] `human-adjudication-results.qmd` reports validated adjudication state,
  unresolved work, correction-candidate counts, and publication consequences.
- [ ] The publication audit package lists human reliability methodology,
  adjudication results, tracked status artifacts, and this completion checklist.
- [ ] The publication package names exactly which cases, languages, task layers,
  and cohorts are complete.
- [ ] The publication package explicitly marks incomplete cases, languages,
  layers, cohorts, unresolved disagreements, local-only artifacts, and
  rights-withheld payloads as limitations.
- [ ] Claims with unresolved high-priority disagreements, incomplete
  adjudication, invalid submissions, missing codebook implications, or missing
  protected-path evidence remain draft.
- [ ] AI-use, data-availability, validation-gate, and public-site readiness
  materials do not conflate human agreement, model agreement, adjudication, or
  historical corroboration.

## Repository validation gate

All four commands must pass in the same repository state used for the
completion decision:

```bash
npm run status
npm run validate
npm run pipeline
quarto render
```

These commands are required even when the human reliability state is honestly
blocked. A blocked human reliability checklist with passing repository
validation means the repository reports the limitation correctly; it does not
mean the human reliability study is complete.

## Completion meaning

The milestone gate is `complete` only when every checked item above is satisfied
for the cohorts being claimed as reliable. It is `blocked` or `incomplete` when
training, calibration, samples, two qualified primary coders, validated
submissions, metrics, reference comparison, disagreements, required
adjudication, codebook notes, protected-path evidence, publication updates, or
repository validation are missing or invalid.

Current publication materials report no complete human reliability cohort rows.
Until that changes, the workbench may disclose human reliability architecture
and status, but it must not make a publication-ready human reliability claim
for any case, language, layer, or cohort.
