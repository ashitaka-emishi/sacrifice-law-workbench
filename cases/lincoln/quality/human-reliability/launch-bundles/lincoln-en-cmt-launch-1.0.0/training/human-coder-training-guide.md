# Human Coder Training Guide

Training version: `1.0.0`

Status: required preparation for blind human-reliability coding; this guide is
not itself a calibration packet, reliability sample, answer key, or
adjudication record.

This guide teaches qualified readers to apply the workbench's annotation method
without private project knowledge and without access to accepted decisions.
It operationalizes the
[human reliability architecture](human-reliability-architecture.md) for MIPVU
identification, lexical boundaries, CMT mapping, interpretation,
violence/obligation, agency/absence, confidence, ambiguity, rival readings,
uncertainty, and out-of-scope decisions.

All worked examples below are invented for training. They are identified with
`training-synthetic-*` IDs, contain no historical or restricted source text,
and must never be included in a blind reliability sample. After training,
coders complete the separate
[multilingual calibration packets](human-coder-calibration.md), whose
coordinator-held answer keys and completion records remain outside the blind
study.

## Training outcome

Before receiving a reliability packet, a coder should be able to:

- preserve blindness and independent decision-making;
- identify the exact unit and task layer assigned;
- make source-language MIPVU and boundary decisions;
- separate identification from CMT and interpretation;
- record violence, obligation, agency, and absence without importing a desired
  theory;
- calibrate confidence separately from the categorical decision;
- preserve ambiguity, uncertainty, and rival readings;
- use `out_of_scope` rather than guess when competence, context, rights, or the
  codebook is insufficient; and
- explain why a gloss, model output, accepted annotation, or another coder's
  judgment cannot substitute for their own source-based decision.

Training completion permits entry into language-specific calibration. It does
not qualify a coder by itself and does not authorize access to a blind study
packet.

## Required reading

Coders must read the versions declared by their cohort:

1. this training guide;
2. [`MIPVU_ANNOTATION_GUIDE.md`](../../MIPVU_ANNOTATION_GUIDE.md);
3. the relevant sections of
   [`RESEARCH_DESIGN.md`](../../RESEARCH_DESIGN.md);
4. the cohort's codebook and controlled vocabulary;
5. the case's rights and storage instructions;
6. source-language historical-semantics guidance supplied for the cohort; and
7. the packet-specific instructions, after training and calibration are
   complete.

Do not open accepted annotation files, model-reliability outputs, prior coder
submissions, or adjudication records while coding a blind packet.

## Eligibility and source-language competence

A cohort is source-language specific. A coder must have enough reading
competence to distinguish contextual meaning, basic meaning, grammar,
register, polysemy, idiom, and plausible lexical boundaries in that language.
Domain expertise and period-language preparation may also be required.

Qualification is declared before packet release and confirmed through
language-appropriate calibration. Familiarity with an English translation is
not source-language competence.

Use `out_of_scope` when:

- the item exceeds the coder's declared language competence;
- OCR, transcription, or corruption prevents a defensible decision;
- required context or a lawful reference source is unavailable;
- source access or transmission is not permitted;
- the packet omits a unit needed to answer the assigned question; or
- the codebook does not provide an authorized decision path.

An out-of-scope response is information about study coverage. It is not a
failure to be hidden and must not be converted into a low-confidence guess.

### Gloss limits

An English gloss may help orientation, but it is a separate analytical aid.
The source sentence and source lexical unit control the decision.

Do not:

- infer a metaphor merely because the gloss uses an English metaphor;
- erase a source-language metaphor because the gloss is literal;
- use English word boundaries for a French or German boundary decision;
- treat one gloss choice as proof of a source or target domain; or
- silently repair a disputed gloss while coding.

If the gloss materially influences or conflicts with the source-language
reading, record the issue in the uncertainty or rival-reading note. If the
source cannot be evaluated without the gloss, use `out_of_scope`.

## Blindness and independence

Blindness protects the study from answer leakage. During reliability coding,
the coder may use only the cohort-authorized codebook, historical-semantics
resources, lawful dictionaries or reference works, neutral packet context, and
their own reasoning.

The coder must not inspect or request:

- accepted MIPVU, CMT, interpretive, agency, or absence decisions;
- prior Codex-assisted review packets, reliability results, or adjudication;
- model packets, model outputs, disagreement reports, or consensus summaries;
- another human coder's decisions, notes, confidence, or completion state;
- sample roles such as positive, negative, ambiguous, or claim-relevant;
- support ratings, historical conclusions, claim status, or synthesis prose;
- the adjudication queue or later adjudicator decisions; or
- filenames, comments, or repository history that reveal an expected answer.

Do not discuss live study items with another coder before both submissions are
registered. Do not use an AI system to generate, revise, or check study
decisions unless the cohort is explicitly defined as assisted coding. An
assisted cohort is a different design and cannot be pooled with independent
unaided human coding.

If accidental exposure occurs, stop coding and report:

- the affected item or range;
- what information was exposed;
- when and how exposure occurred; and
- whether any decisions had already been made.

Do not attempt to compensate mentally or conceal contamination.

## Identify the assigned task

Each packet item belongs to one task layer. Answer only the assigned layer.

| Layer | Main question | Must not decide |
|---|---|---|
| Identification | Is the lexical unit metaphor-related here, and is its proposed boundary valid? | Conceptual cluster, ideological function, historical support |
| CMT | What source-target mapping and entailments best describe the supplied span? | Whether the project has accepted the metaphor; final interpretation |
| Interpretation | Which bounded functions, agency roles, and absences are supported? | Historical causation, private mental state, final theory support |

Later reasoning must not backfill an earlier layer. A compelling sacrificial
interpretation cannot turn a non-metaphorical lexical unit into a MIPVU
positive. A MIPVU-positive unit does not require a Koenigsbergian
interpretation.

## Units and context

Keep these units distinct:

| Unit | Coding use |
|---|---|
| Document | Provenance, genre, date, and broader rhetorical context |
| Paragraph/section | Local movement, contrast, or search scope |
| Sentence | Minimum citable annotation context |
| Lexical unit | MIPVU decision unit |
| Source span | Boundary for CMT or interpretive evidence |
| Mapping | Source-target relation and entailments |
| Agency/absence scope | Declared context in which presence or nonpresence is evaluated |

Code every assigned lexical unit, including ordinary negative controls. Do not
skip function words or apparently literal units because a nearby expression is
interesting. Use only the context supplied or explicitly authorized by the
packet.

## MIPVU identification procedure

MIPVU asks:

> Is this lexical unit metaphor-related in this context?

For each unit:

1. State its contextual meaning in this sentence.
2. Identify a more basic contemporary or historically appropriate meaning.
3. Cite the dictionary, lexicon, or reference used when the packet requires it.
4. Decide whether the meanings contrast.
5. Decide whether the contextual meaning can be understood by comparison with
   the basic meaning.
6. Select one controlled decision.
7. Record confidence, uncertainty, and notes independently.

### Controlled decisions

- `non_metaphor`: no metaphorically relevant basic/contextual contrast.
- `mipvu_indirect`: an indirect comparison supports the contextual meaning.
- `mipvu_direct`: an explicit metaphor, simile, analogy, or comparison.
- `mipvu_implicit`: omitted or implied material carries a metaphorical role.
- `mipvu_personification`: a nonhuman entity is construed through human body,
  agency, emotion, or action.
- `uncertain`: the evidence remains materially contested or insufficient.
- `excluded_nonlexical`: the generated token is not a lexical unit.

Theoretical importance is not a MIPVU criterion. Literal violence, death,
blood, body, nation, sacrifice, or enemy language remains `non_metaphor` when
the contextual meaning is literal.

### Required rationale

For metaphor-related or uncertain units, record:

- contextual meaning;
- basic meaning;
- basic-meaning source;
- contrast explanation;
- comparison basis;
- confidence;
- uncertainty status and note; and
- a review note explaining historical semantics, OCR, register, or rival
  concerns.

Period meaning matters. A modern English meaning or translation may be the
wrong basic meaning for an older French, German, or English source.

## Lexical and source-span boundaries

Boundary decisions are independent from category decisions. A coder can agree
that an expression is metaphor-related but disagree about its span.

Use the packet's controlled boundary response:

- `exact`: supplied offsets capture the relevant unit;
- `expand`: add adjacent source material;
- `contract`: remove material;
- `split`: one proposed span contains multiple independently coded units;
- `merge`: adjacent supplied units form one expression for the assigned task;
- `no_valid_span`: no lawful source span supports the proposed item; or
- `uncertain`: more context or tokenization guidance is required.

Preserve source character offsets. Do not calculate boundaries from the gloss.
For discontinuous or morphologically complex expressions, follow the
packet/codebook rule and explain any proposed split or merge.

## CMT mapping procedure

CMT coding begins from the supplied source span; it does not repeat the MIPVU
decision. The presence of a CMT item does not reveal that the reference accepts
the span as metaphorical.

For each item:

1. Identify the primary source domain evoked by the expression.
2. Add a secondary source domain only when separately supported.
3. Identify the target domain being understood.
4. State the conceptual mapping in a controlled, reviewable form.
5. List only entailments licensed by the local expression and authorized
   context.
6. Select a cluster only when the mapping satisfies that cluster's definition.
7. Record a rival reading that could explain the language differently.

Do not:

- copy a familiar cluster because the case is known for it;
- infer source domains from the English gloss alone;
- treat co-activation as multiple independent pieces of evidence;
- inflate a conventional expression into a novel ideological mapping; or
- use a cluster label as a substitute for source-target analysis.

## Interpretive procedure

Interpretation asks which bounded political-symbolic functions are supported
by the supplied text. It does not diagnose a speaker, prove historical
causation, or establish Koenigsberg's theory.

For each standard function, choose `present`, `absent`, `uncertain`, or
`not_applicable`:

- sacred object;
- sacrificial body;
- enemy as bringer of death;
- violence logic;
- obligatory frame; and
- purification.

`Absent` means the field was applicable and evaluated but not supported in the
declared context. `Not_applicable` means the question does not apply to this
item. `Uncertain` means applicable evidence is materially ambiguous.

### Violence and obligation

Record `violence_logic` only when the text frames violence, injury, killing, or
coercion as a means, necessity, defense, cure, payment, purification, rescue,
or other authorized process. Literal mention of violence does not itself
establish a violence logic.

Record `obligatory_frame` only when an agent or collective is represented as
bound, required, destined, commanded, owing, unable legitimately to refuse, or
morally compelled. Strong preference, prediction, or praise is not obligation.

State who is obliged, by what authority or condition, to do what, and with
what represented consequence.

### Sacred object and sacrificial body

A sacred object is represented as ultimate, transcendent, inviolable,
immortal, or worth dying/killing for. Honorific language alone is insufficient.

A sacrificial body is represented as an offering, payment, instrument, victim,
martyr, or bodily material through which an object is preserved or made real.
Literal injury without offering, exchange, obligation, or sacralization may be
violence but not sacrificial-body evidence.

### Enemy as bringer of death and purification

Enemy-as-bringer-of-death requires the enemy to be represented as agent,
carrier, embodiment, or sign of collective death, dissolution, contamination,
or unreality. Mere opposition is insufficient.

Purification requires removal of represented stain, disease, corruption,
pollution, impurity, or contaminating presence. Administrative reform or
ordinary improvement is not automatically purification.

## Agency coding

Agency coding records textual role assignment, not the coder's historical
judgment.

Identify:

- agents: actors represented as initiating or controlling action;
- patients: entities acted upon or affected;
- beneficiaries: entities represented as gaining from action;
- sacrificial subjects: bodies or groups represented as expended, offered, or
  required to suffer;
- excluded agents: plausible actors whose agency is displaced or suppressed
  in the declared scope.

Grammar can obscure agency through passive voice, nominalization, divine or
natural causation, collective abstraction, or agentless necessity. Record the
textual construction and avoid inventing an agent merely because history
suggests one.

## Absence coding

Absence is not whatever the coder wishes the text had mentioned. Before coding
absence, identify:

1. the declared search scope;
2. the expected presence;
3. what would count as that presence;
4. whether the supplied context is sufficient; and
5. a possible displacement mechanism.

Choose:

- `present`: the expected element is present;
- `absent`: the element is meaningfully absent within adequate scope;
- `uncertain`: scope or evidence does not resolve the question;
- `not_applicable`: no justified expectation exists.

Do not turn a missing packet excerpt into a substantive absence. Use
`out_of_scope` or `uncertain` when the required document, register, or
paragraph-level context is unavailable.

## Confidence, ambiguity, and uncertainty

Confidence records how strongly the available evidence supports the selected
decision. It is not the importance of the item and is not a substitute for an
uncertainty note.

Use the cohort's numeric scale consistently. As a general interpretation:

- high confidence: the decision and rationale are stable under plausible
  alternatives;
- moderate confidence: one reading is better supported, but a material rival
  remains;
- low confidence: evidence is weak, context-limited, or sensitive to language,
  boundary, OCR, or codebook uncertainty.

Ambiguity means two or more readings remain linguistically available.
Uncertainty can also arise from missing context, source quality, historical
semantics, rights restrictions, or an incomplete codebook. Record the cause,
not merely the word "uncertain."

Do not raise confidence to make the dataset look complete. Do not lower
confidence as a covert way to disagree with a controlled category.

## Rival readings

Every CMT or interpretive item requires a plausible alternative explanation.
A rival reading is not a token disclaimer. It should identify the strongest
nonpreferred account, such as:

- literal description;
- conventional idiom;
- legal formula;
- religious or ceremonial convention;
- genre expectation;
- translation or gloss artifact;
- OCR or transcription error;
- alternate source/target mapping;
- audience adaptation; or
- insufficient context.

The preferred decision should explain why it fits the supplied evidence better,
or remain `uncertain` when it does not.

## Out-of-scope protocol

Use `out_of_scope` only for a declared reason, not to avoid a difficult but
answerable item. Record one or more reasons:

- language competence;
- rights or access;
- corrupted source;
- missing context;
- invalid or unknown identifier;
- task/codebook mismatch;
- packet construction defect; or
- conflict/contamination discovered during coding.

Do not supply a substantive value alongside `out_of_scope` unless the eventual
submission schema explicitly permits a preserved provisional response. Notify
the study coordinator when the reason indicates a packet-wide defect.

## Worked synthetic examples

These examples are training-only. Their wording is invented, their IDs begin
with `training-synthetic-`, and they are excluded from sampling and
calibration.

### Example 1: English MIPVU and boundary

`training-synthetic-en-01`

> The council built a bridge between the two districts.

Assigned lexical unit: `bridge`.

- Contextual meaning: a means of connecting political communities.
- More basic meaning: a physical structure spanning an obstacle.
- Decision: `mipvu_indirect`.
- Boundary: `exact` for `bridge`; `built a bridge` may be retained as a wider
  CMT evidence span but does not change the lexical-unit decision.
- Comparison basis: social connection is understood through physical passage.
- Rival: `bridge` may be a highly conventionalized policy idiom.
- Confidence: moderate-to-high, with conventionality noted.

This identification does not establish reconciliation, sacred object,
obligation, or a historical outcome.

### Example 2: English literal negative control

`training-synthetic-en-02`

> Workers repaired the wooden bridge before sunrise.

Assigned lexical unit: `bridge`.

- Contextual meaning: a physical structure spanning an obstacle.
- Basic meaning: the same physical structure.
- Decision: `non_metaphor`.
- Boundary: `exact`.

The word's metaphorical use elsewhere is irrelevant.

### Example 3: Direct comparison and uncertainty

`training-synthetic-en-03`

> The rumor moved through the town like smoke.

Assigned span: `like smoke`.

- Decision: `mipvu_direct`.
- Candidate source domain: smoke spreading through air.
- Candidate target: circulation of a rumor.
- Entailment: diffusion can be rapid and difficult to contain.
- Rival: the comparison may foreground visibility or obscurity rather than
  diffusion.
- Confidence: moderate; preserve the entailment ambiguity.

### Example 4: French source-language judgment

`training-synthetic-fr-01`

> La réforme ouvre une voie étroite vers la paix.

Working gloss: "The reform opens a narrow path toward peace."

Assigned lexical unit: `voie`.

- Source-language contextual meaning: a figurative route or course toward a
  political condition.
- Basic meaning: a physical way, route, or passage.
- Decision: likely `mipvu_indirect`.
- Candidate mapping: ACHIEVING PEACE IS TRAVELING ALONG A PATH.
- Rival: *voie* may be conventional political vocabulary with weak image
  activation.

The French lexical and grammatical evidence controls the decision. The English
word "path" does not prove the mapping. A coder unable to evaluate *voie* and
*ouvrir une voie* in French must use `out_of_scope`.

### Example 5: German gloss conflict

`training-synthetic-de-01`

> Der Vertrag trägt die Stadt durch den Winter.

Working gloss: "The treaty sustains the city through the winter."

Assigned lexical unit: `trägt`.

- Source-language basic meaning includes physically carrying or bearing.
- Contextual meaning concerns enabling the city to endure.
- Decision: plausible `mipvu_indirect`.
- Candidate mapping: POLITICAL SUPPORT IS PHYSICAL CARRYING.
- Gloss warning: "sustains" softens the carrying image and cannot replace the
  German decision.
- Rival: *tragen* may be conventionalized as support or endurance.

### Example 6: Violence without sacrificial interpretation

`training-synthetic-en-04`

> The guards struck the gate until the lock broke.

- Violence is literally present.
- `violence_logic`: may be `present` only if the assigned interpretation field
  treats force-as-means to entry and the packet context supports that scope.
- `sacrificial_body`: `absent` or `not_applicable`; no body is represented as
  offering, payment, or sacred instrument.
- `obligatory_frame`: absent unless additional context presents the action as
  required.

Do not infer sacrifice from force alone.

### Example 7: Obligation and agency

`training-synthetic-en-05`

> By the oath, each delegate must carry the city's burden.

- `obligatory_frame`: present; the oath is represented as binding delegates.
- Agent: each delegate.
- Beneficiary or protected object: the city, if supported by context.
- Candidate source domain: physical carrying.
- Candidate target: civic responsibility.
- Rival: formulaic oath language may explain some of the force.
- Unresolved question: what the "burden" consists of; do not invent sacrifice.

### Example 8: Absence requires scope

`training-synthetic-en-06`

> The proclamation praises victory and names the commanders.

Question: Is civilian suffering absent?

- Sentence-only scope: `uncertain` or `not_applicable`; one sentence does not
  establish a meaningful proclamation-wide absence.
- Full-document scope with an explicit expectation and completed search:
  `absent` may be available if no civilian patients, losses, or consequences
  appear.

The same text can support different absence decisions under different declared
scopes. Never infer a larger search than the packet supplies.

### Example 9: Personification versus ordinary agency

`training-synthetic-en-07`

> The law remembers the forgotten claimant.

- `law` is nonhuman and is construed as remembering.
- Decision for `remembers`: plausible `mipvu_personification`.
- Agency note: the text assigns agency to law, potentially displacing
  legislators, judges, or administrators.
- Rival: conventional legal shorthand may reduce personification salience.

The coder records textual agency; they do not decide from this sentence who
actually implemented the law.

### Example 10: Out of scope

`training-synthetic-fr-02`

> [OCR fragment: "La p—rie exige ..."]

The focal word is corrupted and the packet supplies no lawful image or edition
check.

- Decision: `out_of_scope`.
- Reason: corrupted source / missing lawful verification context.
- Do not guess *patrie* from the partial string and then code obligation.

## Common coding failures

| Failure | Correction |
|---|---|
| Coding the theory instead of the word | Return to contextual/basic meaning and the assigned layer |
| Letting a gloss determine the source decision | Re-read the source; use `out_of_scope` if not competent |
| Treating all violence as sacrifice | Require offering, payment, obligation, or sacralization evidence |
| Treating all praise as sacred-object evidence | Require ultimacy, inviolability, transcendence, or death/killing-worthiness |
| Inferring absence from a short excerpt | Check the declared search scope |
| Using low confidence instead of `uncertain` | Select the category and uncertainty status independently |
| Omitting a rival because confidence is high | Record the strongest plausible alternative |
| Copying another coder or accepted reference | Stop, report contamination, and preserve independence |
| Guessing when context or access is missing | Use `out_of_scope` with a reason |
| Converting adjudication into original agreement | Preserve pre-adjudication coder values and metrics |

## Coder workflow

Before coding:

- confirm cohort, source language, task layer, packet ID, and packet hash;
- confirm training and calibration versions;
- review rights and storage requirements;
- attest source-language competence and conflicts;
- disable or avoid unauthorized AI, retrieval, and collaboration tools; and
- verify that no accepted decisions or other coder outputs are visible.

For each item:

1. verify stable IDs and source text;
2. identify the assigned unit and task layer;
3. read the authorized source context;
4. make the categorical or field decision;
5. check boundaries where assigned;
6. record rationale, confidence, uncertainty, and rival reading;
7. record agency/absence scope where assigned;
8. use `out_of_scope` if the item cannot be lawfully and competently coded;
9. save without consulting another coder; and
10. move on rather than informally adjudicating your own uncertainty.

Before submission:

- confirm every assigned item has exactly one permitted disposition;
- confirm no source text or ID was altered;
- confirm required rationales and notes are complete;
- review low-confidence and out-of-scope items for accurate reasons;
- confirm no accepted values, model outputs, or other coder decisions were
  copied into comments;
- preserve the original packet and completed response bytes; and
- submit through the cohort's registered procedure.

## Training completion attestation

Before calibration, the coder should be able to attest:

- I read the required guide and codebook versions.
- I understand that accepted annotations, model outputs, other coder values,
  and adjudication are withheld during blind coding.
- I will code only in source-language cohorts for which my competence has been
  declared and reviewed.
- I understand that English glosses are aids and do not control source-language
  identification, boundaries, or mappings.
- I can distinguish MIPVU, CMT, interpretation, agency/absence, and historical
  corroboration.
- I can use uncertainty, rival readings, and `out_of_scope` without guessing.
- I will report accidental exposure, conflicts, source defects, and rights
  problems.
- I understand that coder agreement does not prove correctness and that
  adjudication does not rewrite accepted annotations automatically.

Calibration completion and any qualification decision are recorded separately
under the versioned cohort workflow. Do not record training completion by
editing accepted corpus or annotation artifacts.
