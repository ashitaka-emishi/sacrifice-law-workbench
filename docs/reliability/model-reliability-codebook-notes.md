# Model Reliability Codebook Revision Notes

`scripts/model_reliability/generate_codebook_notes.py` converts validated
agreement diagnostics and the human review queue into deterministic JSON and
Markdown notes:

```bash
python3 scripts/model_reliability/pipeline.py codebook-notes --case lincoln
```

Outputs are written beneath
`cases/<case_id>/quality/model-reliability/codebook/`. They summarize stable
categories, possible instruction ambiguity, common schema or identifier
errors, multilingual risks, proposed wording changes, and training/calibration
uses.

Every recommendation defaults to `deferred`. A human may create
`recommendation-decisions.json` in the same directory, following
`codebook-recommendation-decisions-schema.json`, to mark a recommendation
`accepted`, `rejected`, or `deferred`. Accepted and rejected decisions require
an identified reviewer, timestamp, and rationale.

The decision register is an explicit human governance record. The generator
never writes it, never edits a codebook, and never changes accepted annotations.
An accepted recommendation authorizes a later, separately reviewed codebook
edit and calibration update; it is not itself an adjudication decision.

The generated training guidance can seed human calibration by preserving
source language, task layer, field, and reviewed contrastive examples. Stable
fields may be retained as positive examples, while ambiguous instructions,
common model errors, and multilingual problems become targeted exercises.
