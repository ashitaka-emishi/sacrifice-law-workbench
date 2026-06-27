# Human Coder Recruitment and Onboarding Protocol

Status: recruitment-facing protocol for blind human-reliability coding. This
document is not a calibration packet, reliability result, adjudication record,
or model-evaluation procedure.

Use this protocol before inviting a coder into a human-reliability cohort. It
defines the minimum information a coordinator must give prospective coders and
the minimum eligibility and independence checks that must be complete before a
launch packet is released.

## Plain-language task statement

Human coders perform blind coding of selected source-language passages using
the workbench's annotation rules. The task is not adjudication, not model
evaluation, and not a request to decide whether the larger historical argument
is true. A coder applies the method independently to the packet they receive,
records uncertainty where the rules require it, and returns the completed
response and declarations for validation.

## Required background

Recruit coders who can satisfy all of these requirements for the assigned
case, language, and task layer:

- source-language competence in the language of the packet;
- enough historical, rhetorical, or discourse-analysis background to follow
  the [MIPVU annotation guide](../../MIPVU_ANNOTATION_GUIDE.md) and the
  task-layer rules;
- willingness to complete training and language-appropriate calibration before
  launch-packet coding;
- no undisclosed prior exposure to the study packet, accepted annotations,
  model outputs, adjudication records, or other coder responses;
- ability to work independently, keep materials confidential according to the
  packet's rights and storage rules, and return files through the coordinator's
  approved channel.

Source-language competence means the coder can evaluate the source sentence
and lexical unit directly. Translations, glosses, dictionaries, and reference
notes can support a decision, but they cannot substitute for reading the source
language. If a coder cannot evaluate the source-language unit, they must use
the submission contract's `out_of_scope` or uncertainty fields rather than
guess.

## Estimated time

The coordinator should adapt the estimate to the packet size before
recruitment. A typical first launch should disclose:

- training guide review: 2-3 hours;
- language-specific calibration: 45-90 minutes, plus any coordinator feedback;
- launch packet coding and declarations: 60-90 minutes for a small first
  packet.

Do not recruit until the invitation states whether time is compensated,
credited, volunteered, or handled under another local arrangement.

## Compensation and credit placeholder

Coordinator placeholder to complete before recruitment:

`[Insert compensation, reimbursement, authorship, acknowledgment, course-credit,
or no-compensation language here. State who pays or grants credit, the rate or
basis if applicable, when payment or credit is issued, and whether completion
of calibration, a valid returned submission, or both are required.]`

If no compensation or credit is offered, say that directly in the recruitment
message before the coder sees any packet material.

## Independence requirements

Coders must complete the work independently. They must not discuss packet
items, uncertainty, confidence, expected answers, or task strategy with other
coders. They must not inspect accepted annotations, answer keys, prior coder
outputs, model outputs, adjudication queues, synthesis notes, or downstream
publication claims for the assigned material.

If accidental exposure happens, the coder should stop, record what they saw,
and contact the coordinator. The coordinator decides whether the coder can
continue, must be reassigned, or must be excluded from that cohort.

## Allowed resources

Allowed resources for a standard independent cohort are:

- the recruitment note, this protocol, and coordinator eligibility screen;
- the [Human Coder Training Guide](human-coder-training-guide.md);
- the assigned public method references and task-layer instructions;
- the source-language calibration packet assigned by the coordinator, excluding
  answer keys;
- the generated launch bundle and packet-specific allowed-references file;
- ordinary dictionaries, grammars, lexicons, and neutral historical references
  that do not disclose the workbench's accepted decision for the packet item.

## Prohibited resources

Prohibited resources for a standard independent cohort are:

- accepted annotations, normalized accepted decisions, or case synthesis files
  for the packet material;
- model outputs, model-reliability packets, model consensus reports, and model
  diagnostics for the packet material;
- adjudication queues, adjudication decisions, correction candidates, answer
  keys, or another coder's responses;
- AI systems used to generate, revise, validate, translate, or check coding
  decisions, unless the cohort manifest explicitly declares an assisted-AI
  condition;
- any private, restricted, or rights-incompatible source copy not provided or
  approved by the coordinator.

## What coders receive

Before coding a real packet, each coder should receive:

- the recruitment and consent/eligibility message, including time,
  compensation or credit, privacy, and AI-use terms;
- this protocol;
- the [Human Coder Training Guide](human-coder-training-guide.md);
- the relevant [Human Coder Calibration Packets](human-coder-calibration.md),
  without answer keys;
- the generated [Human Coder Launch Bundle](human-coder-launch-bundles.md),
  including packet files, response templates, allowed references, coder
  declarations, return instructions, and manifest.

For the first Lincoln cohort, the concrete generated bundle is documented in
the [Lincoln launch bundle README](../../cases/lincoln/quality/human-reliability/launch-bundles/lincoln-en-cmt-launch-1.0.0/README.md),
with a [CSV response template](../../cases/lincoln/quality/human-reliability/launch-bundles/lincoln-en-cmt-launch-1.0.0/packet/cmt-response-template.csv)
and [JSON response template](../../cases/lincoln/quality/human-reliability/launch-bundles/lincoln-en-cmt-launch-1.0.0/packet/cmt-response-template.json).

## What coders return

Coders return only through the coordinator's approved channel:

- completed coder declarations, including training, calibration, independence,
  source-language competence, AI-use, and exposure statements;
- the completed JSON or CSV response that follows the
  [Human Coder Submission Contract](human-coder-submission-contract.md);
- any uncertainty notes, out-of-scope explanations, rights/access issues, or
  coordinator questions that arose during the work;
- any required calibration completion record if the coordinator has not already
  recorded it.

The coordinator runs the preflight and ingestion process described in
[Human Coder Submission Ingestion](human-submission-ingestion.md). Preflight
errors should be resolved with the coder before formal ingestion when possible;
after ingestion, preserve the raw returned file bytes and record corrections as
separate normalized or audit artifacts.

## Uncertainty and questions

Coders should use the submission fields for uncertainty, confidence, rival
readings, and `out_of_scope` rather than forcing a confident answer. Questions
about file access, source corruption, rights limits, unclear instructions, or
possible contamination go to the coordinator only. Coders should not ask other
coders, compare answers, or search for workbench-derived answers.

The coordinator may answer procedural questions, clarify where an instruction
is located, or replace a defective packet. The coordinator must not reveal
expected answers, accepted annotations, calibration answer keys, model outputs,
or another coder's response.

## AI-use restrictions and disclosure

For a standard independent human-reliability cohort, AI assistance is
prohibited for coding decisions. Coders must not use AI to identify metaphors,
choose boundaries, translate packet text for decision-making, generate CMT
mappings, classify interpretive fields, decide uncertainty, revise answers, or
check whether responses are likely to be correct.

Coders must disclose any AI assistance, even accidental or exploratory use. If
the study intentionally runs an AI-assisted human condition, that condition
must be declared in the cohort manifest and separated from independent
human-reliability claims.

## Privacy and data handling

Use pseudonymous coder IDs in manifests, submissions, validation output, and
publication-facing summaries. Keep the mapping between real identity and coder
ID under coordinator control outside public outputs unless the coder has given
explicit written permission for a named credit.

Coder identity, eligibility declarations, AI-use disclosures, exposure reports,
and submitted files are study records. Store them only in the approved
repository or local-only location declared by the cohort and source-rights
policy. Do not publish raw submissions, identity mappings, private contact
information, or restricted source text unless the applicable rights and consent
terms allow it.

Completed responses inherit the packet's source-rights and storage limits. The
coordinator should transmit packets and returns through a secure channel,
preserve raw returned files for audit, and expose only aggregate or
pseudonymous results in public-facing reliability reports.

## Coordinator checklist

Before sending a launch bundle, confirm:

- the coder received the recruitment terms, including estimated time,
  compensation or credit, privacy, and AI-use restrictions;
- source-language competence and conflicts were screened;
- training and calibration requirements were completed or scheduled;
- the launch bundle excludes answer keys, accepted annotations, model outputs,
  adjudication records, and prior coder responses;
- the coder knows what to return and how to ask questions;
- the coordinator has a plan to run submission preflight, preserve raw returns,
  and record any exclusions or contamination events.
