# Human Inter-Annotator Agreement Metrics

`scripts/human_reliability/compute_agreement.py` compares validated primary
coder runs from exactly one case, source language, task layer, packet, and
cohort version. It refuses cross-cohort pooling. The JSON and CSV outputs live
under:

```text
cases/<case_id>/quality/human-reliability/comparisons/
  <cohort_id>-<cohort_version>/
    human-agreement.json
    human-agreement.csv
```

Run:

```bash
python3 scripts/human_reliability/compute_agreement.py \
  --case <case_id> \
  --cohort <cohort_id> \
  --cohort-version <version>
```

The command requires an ingestion state of `complete` and at least two
distinct validated primary coders. Synthetic fixtures exercise the command,
but no production result exists until real human submissions have completed
ingestion.

## Field-specific treatment

No overall agreement score is emitted. Each field retains its own sample size,
missingness, exact matches, metric family, undefined reason, and sparse-sample
flag. Results preserve every coder-pair table and also provide a cohort summary
across those pairwise observations when a declared cohort has more than two
coders.

The result records each input registration ID, immutable raw hash, submission
ID, and coder ID so the metric table can be reconstructed from the normalized
store without filename inference. It also records the generator script hash,
version, and Git revision.

Before computing, the command revalidates the normalized-run schema, approved
cohort and packet hashes, every submission against packet IDs and controlled
vocabulary, and the completed coder set recorded by ingestion status. A
manually altered normalized file is rejected rather than treated as evidence.
It also reparses each immutable registered JSON or CSV source and requires its
raw hash and normalized content to match the comparison input.

| Field kind | Reported treatment |
|---|---|
| Identification decision | Observed agreement, Cohen's kappa when defined, positive agreement, and negative agreement |
| Boundary response | Nominal agreement and kappa |
| Selected metaphor-related lexical-unit boundary | Jaccard overlap of selected stable lexical-unit IDs |
| CMT domains and cluster | Separate nominal agreement; no broad domain hides a target or cluster disagreement |
| CMT secondary domains and entailments | Jaccard set overlap |
| Interpretive functions and absence decision | Separate nominal agreement and kappa |
| Agents, patients, beneficiaries, excluded agents | Separate Jaccard set overlap |
| Confidence | Mean absolute distance on the declared 0–1 scale |
| Uncertainty | Mean normalized ordinal distance across `none`, `low`, `material`, and `unresolved` |
| Rationales, mappings, scopes, criteria, rival readings | Qualitative-only; exact text is retained for later disagreement review but is not presented as reliability |

Positive agreement treats the controlled MIPVU metaphor categories as
positive. `non_metaphor` and `excluded_nonlexical` are negative. `uncertain`
is excluded from the binary calculation and reported in metric notes rather
than forced into either class.

An out-of-scope response contributes to disposition agreement and missingness,
but never becomes an empty substantive set that could inflate agreement.
Confidence and uncertainty retain exact-match counts for audit, but are not
reported as nominal observed agreement.

## Boundary limits

The submission contract records stable lexical-unit IDs and categorical
boundary responses, not arbitrary replacement character offsets. Therefore
boundary reporting has two honest components:

- exact nominal agreement on `exact`, `expand`, `contract`, `split`, `merge`,
  `no_valid_span`, or `uncertain`; and
- Jaccard overlap of the lexical units independently selected as
  metaphor-related within the sentence.

The command does not fabricate character-span overlap when proposed offsets
were never collected.

## Sparse and undefined metrics

Every field with fewer than 20 comparable observations is marked `sparse`.
Kappa is undefined with fewer than two observations or when expected agreement
is one because both coders are constant. Fields with no paired observations
remain unavailable. A set overlap with two empty sets is one for that item, but
negative agreement remains the identification-specific diagnostic for shared
negative coding.

These outputs describe pre-adjudication human-human agreement only. They do
not compare coders to accepted annotations, adjudicate disagreements, prove
historical claims, or establish project-wide reliability.
