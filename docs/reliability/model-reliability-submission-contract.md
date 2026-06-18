# Model Reliability Submission Contract

Status: schema version `1.0.0` defined; ingestion not yet implemented.

This contract defines the model/run metadata and item-level decisions exchanged
by the blind multi-model stress test. The canonical representation is JSON under
[`submission-schema.json`](../../schemas/model-reliability/submission-schema.json).
Manual CSV submissions use the two-file transport described by
[`submission-csv-contract.json`](../../schemas/model-reliability/submission-csv-contract.json)
and normalize to the same JSON shape before registration.

## Contract boundaries

- A submission represents exactly one model run against one immutable packet.
- `packet_id` and `packet_hash` must match the packet manifest exactly. Hashes
  use lowercase `sha256:<64 hexadecimal characters>` notation.
- Case, document, sentence, packet-item, span, and lexical-unit IDs are
  references, not free text. The contract validator rejects values absent from
  the packet and repository context and checks their parent relationships.
- Every item preserves `sentence_source_text` and lexical-unit `source_text`.
  Optional English renderings occupy only the separate `sentence_gloss_en` and
  `gloss_en` fields; they never replace source-language text.
- `lexical_units` is an array so one sentence-level item can carry multiple
  lexical-unit and boundary decisions without collapsing their stable IDs.
- Confidence, uncertainty, and rival reading are required independently. A high
  confidence value therefore cannot erase an uncertainty note or alternative
  interpretation.
- CMT source and target domains must resolve against
  `config/controlled-vocabularies.json`. Identification, boundary,
  interpretation, agency, and absence values are closed by the JSON schema.
- Case-specific extensions belong only in `case_fields`. Keys use
  `<case_id>__<field_name>` and values are scalars or arrays of scalars so they
  survive JSON/CSV round trips. Extensions cannot replace standard fields.

## Task layers

`identification` records contextual meaning, basic meaning, contrast, and the
comparison basis. Each lexical unit independently records its MIPVU and boundary
decision. CMT and interpretive submissions preserve the same lexical-unit IDs
and source spans but do not repeat identification decisions.

`cmt` records primary and secondary source domains, target domain, conceptual
mapping, entailments, and cluster. Controlled domain IDs remain machine-stable
even when labels change.

`interpretation` records six standard Koenigsbergian function judgments plus
explicit agency and absence structures. Each function uses `present`, `absent`,
`uncertain`, or `not_applicable`; empty strings are not decisions.

## CSV transport

A CSV submission consists of one metadata CSV with exactly one row and one item
CSV with at least one row. Array and object columns contain compact JSON. This
avoids ambiguous delimiter-joined lists and preserves multiple lexical units,
agency lists, uncertainty structures, and case extensions. Blank optional object
columns normalize to absent properties. Both files are UTF-8 with headers, comma
delimiters, and LF line endings.

CSV is a transport only. After parsing, the normalized envelope must satisfy the
canonical JSON schema and the same packet, ID, vocabulary, duplicate-span, and
parent-reference checks as a native JSON submission.

## Validation API

`scripts/model_reliability/submission_contract.py` exposes
`validate_submission`, which returns every detected violation, and
`assert_valid_submission`, which raises with the complete violation list. The
caller supplies a `SubmissionContext` built from the packet manifest and current
case artifacts. The validator is read-only; ingestion, immutable raw-submission
registration, normalization, and validation reports remain the responsibility
of issue #60.
