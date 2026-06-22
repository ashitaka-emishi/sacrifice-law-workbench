# Human Reliability Codebook Revision Notes

`scripts/human_reliability/generate_codebook_notes.py` converts classified
human disagreement and validated adjudication results into deterministic JSON
and Markdown recommendations.

Run:

```bash
npm run human-reliability:codebook-notes -- --case <case_id>
```

Outputs live beneath:

```text
cases/<case_id>/quality/human-reliability/codebook/
  codebook-revision-notes.json
  codebook-revision-notes.md
```

Recommendations group evidence by source language, task layer, and field while
retaining affected cohorts, disagreement and adjudication IDs, ambiguity
reasons, claim impact, codebook sections, migration implications, and explicit
re-coding requirements.

Every generated recommendation begins as `proposed`. A human methodology
reviewer may create `recommendation-decisions.json`, conforming to
`codebook-recommendation-decisions-schema.json`, to mark it `accepted`,
`rejected`, or `deferred`. Accepted and rejected dispositions require a named
reviewer, timestamp, and rationale. Every decision also records the generated
recommendation SHA-256; changed evidence or migration implications make the
decision stale and require fresh review.

The decision register is never generated or edited by the command. An accepted
recommendation authorizes only a later versioned codebook-edit workflow. It
does not edit the codebook, promote a correction candidate, alter adjudication,
or retroactively change coder or accepted decisions. Re-coding and migration
remain separately authorized operations.

If any contributing cohort is `local_only`, the detailed JSON and decision
register must remain gitignored. The Markdown output becomes a generic
withholding notice so a local Quarto render cannot expose recommendation IDs,
fields, evidence counts, or methodological dispositions.
