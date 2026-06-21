# Human Coder Submission Contract

One submission represents one primary coder's completed work for one approved
cohort and one deterministic blind packet. The canonical exchange form is
[`submission-schema.json`](../../schemas/human-reliability/submission-schema.json).
The spreadsheet transport is defined by
[`submission-csv-contract.json`](../../schemas/human-reliability/submission-csv-contract.json)
and normalizes to the same JSON shape before ingestion.

## Identity and preparation

A valid submission binds all of the following to the approved cohort:

- cohort, case, sample, packet, source language, task layer, and codebook
  identities and versions;
- the packet manifest's `packet_hash`;
- a pseudonymous primary `coder_id`;
- qualification and source-language attestations;
- training and calibration identities and completion timestamps;
- conflict status and required details for a disclosed conflict;
- independent-completion and AI-assistance declarations; and
- a completion timestamp.

The blank templates generated with a packet intentionally contain a null or
blank `packet_hash`. The coordinator supplies the final packet manifest to the
coder, and the completed submission copies the manifest's `packet_hash`. The
blank template remains a hashed packet payload, while the completed submission
is a new artifact with its own raw hash assigned during ingestion. This avoids
a circular hash between the packet manifest and its blank response template.

An `ai_assistance_used: true` declaration is preserved rather than silently
rewritten. Such a submission belongs to a separately declared assisted-coding
design and cannot be treated as an independent unassisted primary submission.

## Response shape

Every response repeats the stable packet item, document, sentence, source-span,
and lexical-unit IDs. Identification uses `lexical_unit_responses`, with exactly
one response for every lexical unit in the sampled sentence. CMT and
interpretation retain all focal lexical-unit IDs while recording one layered
response for the packet item.

Each response records a controlled disposition, confidence, uncertainty and
its note, optional notes, and an out-of-scope reason. A coded response requires
the task-layer payload. An out-of-scope response forbids a substantive payload
and confidence value so a provisional answer cannot be mistaken for completed
coding.

Case-specific additions live only in `case_fields`. Keys use
`<case_id>__<field_name>` and values are scalars or scalar arrays. The core
schema and code contain no Lincoln-only fields.

## CSV normalization

The CSV transport is one UTF-8, comma-delimited file with LF endings. Cohort
and coder metadata repeats identically on every row. Identification has one row
per lexical unit; CMT and interpretation have one row per packet item. Array
and extension columns contain compact JSON rather than delimiter-joined text.

Ingestion must reject inconsistent repeated metadata and normalize all rows to
`submission-schema.json` before registration. Blank cells represent JSON null
or an absent optional value according to the CSV contract; they are never a
third controlled-vocabulary value.

## Contextual validation

JSON Schema validates structure and closed vocabularies carried by the
contract. `scripts/human_reliability/submission_contract.py` additionally
checks the submission against the approved cohort and packet:

- identity and packet-hash equality;
- exact packet-item coverage with no duplicate or unknown item IDs;
- document, sentence, source-span, and lexical-unit binding;
- exact lexical-unit coverage for identification;
- source and target domains against the repository controlled vocabularies;
  and
- the case namespace for extension fields.

Issue #81 will use this contract to parse JSON and CSV, preserve original
bytes, register every attempt, and write a separate normalized view. Invalid
submissions remain auditable and never enter agreement metrics.
