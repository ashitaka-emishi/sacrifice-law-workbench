# Pipeline Upgrade: Credible Scholarly Method for Lincoln Metaphor Analysis

## Purpose

This document describes an upgraded scholarly analysis pipeline for the `lincoln-metaphor-analysis` project. The goal is to strengthen the project’s methodology so that its claims are credible, inspectable, and suitable for peer-reviewed scholarship.

The upgraded pipeline is designed to support a disciplined movement from:

> corpus construction → metaphor identification → conceptual mapping → discourse analysis → historical corroboration → evidentiary support scoring → publication-ready synthesis

The central methodological principle is that interpretation should be staged. The project should not move directly from Lincoln’s language to large claims about national sacrifice, sacred Union, political violence, or reconciliation. Instead, each claim should pass through a documented chain of evidence:

> scholarly claim → support dimension → metaphor cluster → conceptual mapping → metaphor-related lexical units → sentence IDs → document metadata → source text → historical corroboration where claimed

This pipeline keeps interpretive richness while making the research process auditable. It assesses the degree of evidentiary support for Koenigsberg’s Law of Sacrifice and body-politic corollary rather than claiming proof or treating the theory as settled in advance.

---

## Guiding Principles

### 1. Separate identification from interpretation

The pipeline must distinguish between:

| Layer | Purpose |
|---|---|
| MIPVU | Identifies metaphor-related lexical units |
| Conceptual Metaphor Theory | Interprets source-target mappings |
| Corpus-Assisted Discourse Studies | Examines distribution, frequency, co-occurrence, register, and chronology |
| Critical Metaphor Analysis | Explains persuasive and ideological function |
| Rhetorical criticism | Interprets occasion, audience, genre, and action |
| Historical semantics | Controls for nineteenth-century meaning |
| Systematic absence analysis | Studies agency, silence, displacement, and exclusion |
| Koenigsbergian ideological-fantasy analysis | Interprets sacrifice, sacred collective objects, enemy as death, national fantasy, violence, guilt, redemption, and reconciliation |
| Historical enactment / alignment | Corroborates whether textual-symbolic patterns align with established historical practices or outcomes |
| Evidentiary support scoring | Rates degree of support across sacred object, sacrificial body, enemy as death, and historical enactment/alignment |

MIPVU does not identify conceptual metaphors. It identifies metaphor-related words. CMT then interprets the mappings in which those words participate. Koenigsbergian analysis should come later, after the linguistic and conceptual layers have been established.

### 2. Make the corpus a scholarly object

The corpus should not be treated as a folder of Lincoln texts. It should be treated as a documented scholarly corpus.

Each included text should have:

- title
- date
- genre
- register
- source edition
- authorship confidence
- editorial status
- inclusion rationale
- periodization
- known limitations

Where possible, the project should use TEI or TEI-inspired encoding practices. Full TEI/XML implementation is not required at the outset, but the corpus should follow TEI’s scholarly logic: stable textual identity, metadata, provenance, structural segmentation, and transparent editorial practice.

### 3. Use recognized scholarly standards without overengineering

The upgraded pipeline should use recognized standards and methods where they strengthen credibility:

| Standard / Method | Role |
|---|---|
| TEI / TEI-inspired encoding | Textual provenance and structure |
| FAIR data principles | Findability, accessibility, interoperability, reusability |
| MIPVU | Metaphor-related lexical-unit identification |
| Conceptual Metaphor Theory | Source-target mapping and entailments |
| Corpus-Assisted Discourse Studies | Corpus-level distribution and patterning |
| Critical Metaphor Analysis | Ideological and persuasive function |
| Discourse Dynamics Approach | Change and interaction of metaphors across discourse |
| Historical semantics | Period-appropriate meaning controls |
| Annotation codebook | Coding consistency |
| Inter-annotator reliability | Identification credibility |
| Controlled vocabularies | Stable analytical categories |
| AI-use statement | Research-integrity transparency |

The purpose is not to turn the project into a technical exercise. The purpose is to make an interpretive project more rigorous, reviewable, and defensible.

---

## Pipeline Overview

| Stage | Name | Main Output |
|---:|---|---|
| 1 | Research design | Research protocol |
| 2 | Corpus construction and provenance | Corpus register |
| 3 | Text encoding and segmentation | Stable text units |
| 4 | Historical semantics preparation | Reference apparatus |
| 5 | MIPVU metaphor identification | Metaphor-related lexical-unit table |
| 6 | Reliability testing and adjudication | Reliability report and revised codebook |
| 7 | CMT source-target mapping | Conceptual metaphor mapping table |
| 8 | Corpus-assisted discourse analysis | Frequency, distribution, genre, and chronology findings |
| 9 | Critical Metaphor Analysis | Persuasive and ideological function profiles |
| 10 | Rhetorical and genre analysis | Occasion-sensitive close readings |
| 11 | Discourse-dynamic and diachronic analysis | Metaphor-development account |
| 12 | Systematic absence and agency analysis | Absence and agency matrix |
| 13 | Koenigsbergian evidentiary-support synthesis | Four-dimension support assessment |
| 14 | Comparative analysis | Structured comparison protocol and support-rating comparison |
| 15 | Corroboration, audit, and publication package | Peer-review-ready method appendix |

---

# Stage 1: Research Design

## Objective

Create a formal research design document before annotation begins.

## Purpose

The research design prevents the analysis from drifting into impressionistic reading. It defines the project’s scope, evidence, units of analysis, interpretive sequence, and validation plan.

## Required decisions

The project should define:

- primary research question
- secondary research questions
- evidentiary support standard
- four support dimensions
- corpus boundaries
- inclusion and exclusion rules
- units of analysis
- annotation procedures
- interpretive frameworks
- reliability plan
- validation plan
- publication outputs

## Recommended research-design structure

```markdown
# Research Design

## Project Aim

## Primary Research Question

## Secondary Research Questions

## Corpus Scope

## Inclusion Criteria

## Exclusion Criteria

## Units of Analysis

## Methodological Frameworks

## Annotation Sequence

## Validation Strategy

## AI-Use Policy

## Expected Outputs
```

## Key methodological commitment

The project should state clearly:

> This study uses MIPVU to identify metaphor-related lexical units, Conceptual Metaphor Theory to interpret source-target mappings, corpus-assisted discourse methods to examine distribution and patterning, historical corroboration to assess enactment or alignment, and Koenigsbergian ideological-fantasy analysis to evaluate the degree to which recurring metaphor systems support, complicate, or limit Koenigsberg’s Law of Sacrifice, its body-politic corollary, and the construction of enemies as death.

---

# Stage 2: Corpus Construction and Provenance

## Objective

Create a defined, documented, historically controlled Lincoln corpus.

## Purpose

A publishable metaphor study needs a transparent corpus. Reviewers should be able to see what texts were included, what texts were excluded, and why.

## Corpus metadata fields

Each text should include:

| Field | Description |
|---|---|
| `text_id` | Stable project identifier |
| `title` | Standard title |
| `date` | Date of composition or delivery |
| `period` | Project periodization category |
| `genre` | Speech, debate, letter, fragment, message, address, legal document, etc. |
| `register` | Public ceremonial, public political, private, legal, administrative, military, etc. |
| `source_edition` | Edition or archive used |
| `source_url` | Link, if available |
| `authorship_confidence` | High, medium, low |
| `editorial_notes` | Known textual issues |
| `inclusion_rationale` | Why this text is in the corpus |
| `risk_flags` | Authorship uncertainty, editorial mediation, fragmentary status, etc. |

## Suggested periodization

| Period | Approximate Range | Analytical Significance |
|---|---:|---|
| Early republican rhetoric | 1838–1854 | Law, liberty, republican inheritance |
| Slavery-extension crisis | 1854–1860 | Slavery, Union, sectional conflict |
| Secession and early war | 1860–1862 | Union preservation, oath, constitutional obligation |
| Emancipation and sacrifice | 1862–1864 | War aims, death, freedom, national rebirth |
| Providence and reconciliation | 1864–1865 | Judgment, guilt, healing, reconciliation |

## Output

`corpus-register.csv` or `corpus-register.md`

---

# Stage 3: Text Encoding and Segmentation

## Objective

Prepare texts as stable, citable units for annotation and interpretation.

## Purpose

Every interpretive claim should be traceable to a specific passage, sentence, and lexical unit.

## Recommended structure

Each text should be segmented into:

| Unit | Purpose |
|---|---|
| Document | Historical and bibliographic identity |
| Section | Major rhetorical divisions |
| Paragraph | Argument movement |
| Sentence | Local context |
| Lexical unit | MIPVU coding |
| Passage | Close-reading unit |

## Stable identifiers

The project should use stable IDs:

```text
LIN-GA-1863-S003
```

Example meaning:

- `LIN` = Lincoln corpus
- `GA` = Gettysburg Address
- `1863` = year
- `S003` = sentence 3

For lexical units:

```text
LIN-GA-1863-S003-LU007
```

## TEI-inspired encoding fields

Even if the project does not use full TEI/XML, each text should have:

- header metadata
- source information
- structural divisions
- paragraph IDs
- sentence IDs
- editorial notes
- variant or uncertainty notes where needed

## Output

- normalized text files
- segmented text files
- sentence table
- lexical-unit table

---

# Stage 4: Historical Semantics Preparation

## Objective

Control for nineteenth-century meanings before metaphor identification.

## Purpose

MIPVU requires comparison between contextual meaning and more basic meaning. For Lincoln, this must be historically controlled. Words such as “bond,” “compact,” “experiment,” “proposition,” “judgment,” “offense,” “house,” and “Union” may carry meanings shaped by nineteenth-century law, theology, republican rhetoric, and biblical idiom.

## Required reference resources

The project should build a reference apparatus using:

| Resource Type | Use |
|---|---|
| Nineteenth-century dictionaries | Basic period meanings |
| Legal dictionaries | Compact, oath, bond, title, obligation |
| Biblical concordances | Judgment, offense, atonement, birth, blood |
| Political rhetoric comparison texts | Conventional republican language |
| Antislavery and proslavery texts | Shared metaphor fields |
| Lincoln scholarship | Historical and rhetorical context |

## Historical semantics note

For difficult lexical units, annotators should record:

| Field | Purpose |
|---|---|
| `period_basic_meaning` | More basic meaning in Lincoln’s period |
| `modern_basic_meaning` | Modern meaning, if different |
| `semantic_shift_risk` | Low, medium, high |
| `reference_source` | Dictionary, legal source, biblical source, etc. |
| `note` | Explanation |

## Output

`historical-semantics-notes.md` or `historical-semantics.csv`

---

# Stage 5: MIPVU Metaphor Identification

## Objective

Identify metaphor-related lexical units using MIPVU.

## Purpose

This stage creates the disciplined linguistic evidence base for the entire project.

MIPVU should answer:

> Is this lexical unit metaphor-related in this context?

It should not yet answer:

> What ideology does this metaphor express?

## Simplified MIPVU procedure

For each lexical unit:

1. Read the full text or passage for general meaning.
2. Identify lexical units.
3. Determine the contextual meaning of each lexical unit.
4. Determine whether the lexical unit has a more basic meaning in other contexts.
5. Decide whether the contextual meaning contrasts with the basic meaning.
6. Decide whether the contextual meaning can be understood in comparison with the basic meaning.
7. If yes, mark the lexical unit as metaphor-related.
8. Record confidence and notes.

## Annotation fields

| Field | Description |
|---|---|
| `lu_id` | Stable lexical-unit ID |
| `text_id` | Source text |
| `sentence_id` | Sentence ID |
| `lexical_unit` | Word or phrase |
| `contextual_meaning` | Meaning in the Lincoln passage |
| `basic_meaning` | More basic meaning |
| `basic_meaning_source` | Dictionary or reference source |
| `contrast` | Yes / no |
| `comparison` | Yes / no |
| `mipvu_decision` | Metaphor-related / not metaphor-related / uncertain |
| `confidence` | High / medium / low |
| `annotator` | Annotator ID |
| `note` | Explanation or ambiguity |

## Example

| Field | Example |
|---|---|
| `lexical_unit` | wounds |
| `contextual_meaning` | damage to the nation caused by war |
| `basic_meaning` | injuries to a living body |
| `contrast` | Yes |
| `comparison` | Yes |
| `mipvu_decision` | Metaphor-related |
| `confidence` | High |
| `note` | Body-domain term applied to nation |

## Output

`mipvu-annotations.csv`

---

# Stage 6: Reliability Testing and Adjudication

## Objective

Test whether metaphor identification is stable across annotators.

## Purpose

A publishable pipeline should demonstrate that metaphor identification is not purely idiosyncratic.

## Recommended procedure

1. Create a training sample.
2. Have annotators jointly code a small set of passages.
3. Revise the codebook.
4. Select a reliability sample, ideally 10–20% of the corpus.
5. Have at least two annotators code the sample independently.
6. Calculate agreement.
7. Review disagreements.
8. Adjudicate final decisions.
9. Revise the codebook again.

## Agreement measures

Possible measures include:

- percent agreement
- Cohen’s kappa
- Krippendorff’s alpha

The project should explain whichever measure it uses.

## Disagreement categories

Disagreements should be classified:

| Category | Description |
|---|---|
| lexical segmentation | Annotators disagreed on the unit |
| contextual meaning | Annotators interpreted local meaning differently |
| basic meaning | Annotators selected different basic meanings |
| metaphor decision | One coded metaphor-related, another did not |
| confidence | Same decision, different certainty |
| source-domain ambiguity | Later-stage mapping disagreement |

## Output

- `annotation-codebook.md`
- `reliability-report.md`
- `adjudication-log.csv`

---

# Stage 7: CMT Source-Target Mapping

## Objective

Interpret metaphor-related lexical units as conceptual mappings.

## Purpose

Conceptual Metaphor Theory explains how one conceptual domain is understood in terms of another.

This stage asks:

> What source domain is being mapped onto what target domain, and what entailments follow?

## Mapping fields

| Field | Description |
|---|---|
| `mapping_id` | Stable mapping ID |
| `lu_id` | Linked MIPVU lexical unit |
| `linguistic_expression` | Expression in text |
| `source_domain_primary` | Main source domain |
| `source_domain_secondary` | Optional secondary domain |
| `target_domain` | Conceptual target |
| `conceptual_metaphor` | Example: THE NATION IS A BODY |
| `entailments` | Implications carried by the mapping |
| `confidence` | High / medium / low |
| `rival_reading` | Alternative interpretation |
| `justification` | Why this mapping is assigned |

## Source-domain discipline

The pipeline should distinguish:

- primary source domain
- secondary source domain
- intertextual source
- confidence level
- rival reading
- justification

## Example

| Field | Example |
|---|---|
| `linguistic_expression` | “new birth of freedom” |
| `source_domain_primary` | birth / generation |
| `target_domain` | political renewal |
| `conceptual_metaphor` | POLITICAL RENEWAL IS BIRTH |
| `entailments` | new life, futurity, labor, vulnerability, obligation |
| `rival_reading` | conventional republican renewal formula |
| `confidence` | High |

## Output

`cmt-mappings.csv`

---

# Stage 8: Corpus-Assisted Discourse Analysis

## Objective

Examine metaphor distribution, patterning, concentration, and co-occurrence across the corpus.

## Purpose

This stage connects close reading to corpus-level claims.

It asks:

- Which metaphor-related terms are frequent?
- Which conceptual metaphors are widely distributed?
- Which metaphors are concentrated in a few famous texts?
- Which metaphors are genre-specific?
- Which metaphors change over time?
- Which metaphors co-occur?
- Which metaphors appear at rhetorically climactic moments?

## Required analyses

| Analysis | Purpose |
|---|---|
| Frequency | How often metaphor-related lexical units appear |
| Distribution | How widely they appear across documents |
| Concentration | Whether a pattern depends on a few texts |
| Collocation | Which terms tend to appear near each other |
| Co-occurrence | Which source domains cluster together |
| Genre comparison | How usage varies by register |
| Diachronic comparison | How usage changes over time |
| Salience review | Whether metaphors appear at key rhetorical moments |

## Important caution

Frequency is not the same as significance.

The pipeline should distinguish:

| Measure | Meaning |
|---|---|
| Frequency | How often something appears |
| Distribution | How widely it appears |
| Concentration | Whether it is limited to a few texts |
| Rhetorical salience | Whether it appears at climactic moments |
| Conceptual centrality | Whether it organizes other metaphors |
| Ideological force | Whether it authorizes duty, sacrifice, violence, guilt, redemption, or reconciliation |

## Output

- `corpus-analysis.md`
- `frequency-tables.csv`
- `cluster-distribution.csv`
- `genre-comparison.md`
- `diachronic-analysis.md`

---

# Stage 9: Critical Metaphor Analysis

## Objective

Analyze how metaphors persuade, naturalize, authorize, and emotionally organize political meaning.

## Purpose

Critical Metaphor Analysis bridges CMT and ideological interpretation.

It asks:

| Question | Purpose |
|---|---|
| What values does the metaphor activate? | Union, freedom, law, sacrifice, Providence |
| What emotions does it evoke? | Duty, grief, guilt, reverence, hope, fear |
| What action does it make reasonable? | War, endurance, emancipation, reconciliation |
| What moral hierarchy does it create? | Union above individual life, Providence above political calculation |
| What alternatives does it suppress? | Disunion, compromise, revenge, Black agency, civilian suffering |
| What political identity does it construct? | Citizen, soldier, nation, people, enemy, martyr |

## Cluster profile template

Each major metaphor cluster should receive a profile:

```markdown
# Cluster Profile: [Cluster Name]

## Source Domains

## Target Domains

## Major Expressions

## Corpus Distribution

## Rhetorical Contexts

## Persuasive Function

## Moral Emotions Activated

## Political Actions Authorized

## Rival Readings

## Negative Cases

## Relation to Koenigsbergian Analysis
```

## Output

`critical-metaphor-analysis.md`

---

# Stage 10: Rhetorical and Genre Analysis

## Objective

Interpret metaphors within their historical occasions, audiences, and genres.

## Purpose

Metaphors do not function in the abstract. A metaphor in a private letter does not do the same work as a metaphor in a presidential inaugural, battlefield dedication, debate, or annual message.

## Rhetorical fields

For each major metaphor instance or cluster, record:

| Field | Description |
|---|---|
| `audience` | Who is addressed? |
| `occasion` | What event or crisis prompted the text? |
| `genre` | Speech, address, letter, message, debate, etc. |
| `rhetorical_action` | What is Lincoln trying to make the audience believe, feel, accept, or do? |
| `emotional_posture` | Warning, mourning, accusation, consolation, consecration, reconciliation |
| `agency_structure` | Who acts, who suffers, who is passive, who is absent? |
| `rhetorical_salience` | Low, medium, high |

## Example questions

- Does the metaphor justify action?
- Does it console loss?
- Does it transform suffering into meaning?
- Does it sacralize an object?
- Does it convert death into obligation?
- Does it assign guilt?
- Does it enable reconciliation?

## Output

`rhetorical-genre-analysis.md`

---

# Stage 11: Discourse-Dynamic and Diachronic Analysis

## Objective

Track how metaphor systems change across Lincoln’s career and across the Civil War.

## Purpose

This stage asks whether Lincoln’s metaphor system is stable, intensifying, mutating, or reorganizing.

## Diachronic questions

| Question | Example |
|---|---|
| Does legal Union language become sacred Union language? | oath, bond, compact → sacrifice, nation, Providence |
| Does anti-slavery language shift into providential judgment? | wrong → offense → divine punishment |
| Does death become increasingly redemptive? | loss → unfinished work → new birth |
| Does reconciliation become more imaginable? | enemy as rebel → shared guilt under God |
| Do some metaphors disappear? | legal obligation giving way to healing or judgment |
| Do source domains merge? | body + sacrifice + Providence |

## Output

- `diachronic-analysis.md`
- `metaphor-timeline.csv`
- `cluster-evolution.md`

---

# Stage 12: Systematic Absence and Agency Analysis

## Objective

Study what Lincoln’s metaphor system requires, suppresses, displaces, or leaves unnamed.

## Purpose

Absence analysis should be systematic, not merely a moral critique added after interpretation.

The project should ask:

> Given Lincoln’s metaphor system, which agents, bodies, experiences, or causal forces should logically appear but are muted, displaced, or absent?

## Absence matrix

| Metaphor System | Expected Presence | Possible Absence |
|---|---|---|
| Nation as wounded body | Actual wounded bodies | Soldiers, enslaved people, civilians |
| Slavery as debt | Creditor and debtor | Who is owed? Who pays? |
| War as new birth | Laboring body, mother, child | Who gives birth? Who suffers labor? |
| Providence as judgment | Agent of judgment | Who interprets God’s will? |
| Union as sacred object | Sacrificial victims | Whose deaths preserve the object? |

## Agency fields

For each major passage, record:

| Field | Question |
|---|---|
| `agent_named` | Who acts? |
| `patient_named` | Who suffers or receives action? |
| `beneficiary_named` | Who benefits? |
| `sacrificial_subject` | Who is asked to suffer or die? |
| `excluded_agent` | Who is missing despite relevance? |
| `displacement_mechanism` | How is agency shifted or obscured? |

## Output

`absence-agency-analysis.md`

---

# Stage 13: Koenigsbergian Evidentiary-Support Synthesis

## Objective

Assess the degree to which the case supports, complicates, limits, or fails to support Koenigsberg’s Law of Sacrifice and body-politic corollary.

## Purpose

This stage should come after MIPVU, CMT, corpus analysis, rhetorical analysis, absence analysis, and historical corroboration. It is the evidentiary-support synthesis, not the identification method and not a claim of proof.

The synthesis rates support across four dimensions:

| Dimension | Guiding Question |
|---|---|
| Sacred object | Is a collective object represented as transcendent, ultimate, sacred, immortal, or worth dying/killing for? |
| Sacrificial body | Are bodies represented as meaningful offerings, payments, instruments, victims, martyrs, or material through which the sacred object is preserved or made real? |
| Enemy as death | Is the enemy represented as the agent, carrier, embodiment, or sign of death, doubt, mortality, dissolution, unreality, or collective destruction? |
| Historical enactment or alignment | Do textual-symbolic patterns align with historically documented practices, policies, institutions, mobilizations, or outcomes? |

## Core questions

| Koenigsbergian Question | Lincoln Application |
|---|---|
| What collective object becomes sacred? | Union, republic, democracy, freedom |
| What kind of body is imagined? | Wounded, divided, reborn, healing |
| What sacrifice becomes obligatory? | Soldiers dying so the republic may live |
| How is death made meaningful? | Unfinished work, new birth, divine judgment |
| How is the enemy represented as death? | Rebel, slave power, secession, or disunion as death-bearing threat to the republic |
| What historical enactment or alignment exists? | War mobilization, battlefield death, emancipation policy, reunion practice, public mourning, or other corroborated historical outcomes |
| How is guilt distributed? | Slavery, South, North, nation, Providence |
| What violence becomes legitimate? | War to preserve Union or redeem founding promise |
| What endpoint is imagined? | Reunion, healing, reconciliation |
| What is excluded from the fantasy? | Actual bodies, Black agency, civilian suffering, revenge |

## Support rating

Use anchored 0–4 dimension scores:

| Score | Rating | Meaning |
|---:|---|---|
| 0 | Unsupported | No meaningful evidence for the dimension in the case material |
| 1 | Weak support | Isolated, ambiguous, or low-confidence evidence |
| 2 | Moderate support | Repeated evidence, but limited by scope, ambiguity, or weak historical alignment |
| 3 | Strong support | Repeated, traceable, and contextually persuasive evidence |
| 4 | Very strong support | Dense, repeated, cross-textual evidence with clear historical alignment |

Calculate overall support with the weighted shifted geometric mean:

```text
overall_support = ((S + 1) * (B + 1) * (E + 1) * (H + 1)^2)^(1/5) - 1
```

Where:

- `S` = sacred object score
- `B` = sacrificial body score
- `E` = enemy as death score
- `H` = historical enactment or alignment score

Historical enactment or alignment receives double weight because it is the historical-anchoring dimension. Without historical alignment, the project can claim a strong textual reading but not strong case-level support for the Law.

Apply the historical-alignment cap:

| Historical enactment or alignment score | Maximum overall category |
|---:|---|
| 0 | Weak support |
| 1 | Weak support |
| 2 | Moderate support |
| 3 | Strong support |
| 4 | Very strong support |

## Guardrails

The synthesis must:

- cite concrete metaphor evidence
- distinguish strong claims from hypotheses
- include rival readings
- acknowledge negative cases
- report support, complication, limitation, or non-support
- separate textual-symbolic evidence from historical corroboration
- avoid moral equivalence when comparing different political systems
- avoid treating all metaphor as ideology
- avoid treating frequency as importance without rhetorical justification

## Output

`koenigsbergian-support-synthesis.md`

---

# Stage 14: Comparative Analysis

## Objective

If the project compares Lincoln with Hitler or another political figure, use a structured comparison protocol.

## Purpose

The comparison should examine rhetorical and ideological structures, not imply moral equivalence.

## Comparative dimensions

| Dimension | Lincoln | Hitler / Other Comparator |
|---|---|---|
| Sacred collective object | Union / republic / democracy | Volk / racial body / nation |
| Dominant body metaphor | Wounded, divided, healing, reborn | Diseased, contaminated, purified |
| Violence logic | Preservation, sacrifice, judgment | Purification, extermination, annihilation |
| Enemy as death | Rebel, slave power, secessionist, disunion as death-bearing threat | Parasite, contaminant, racial enemy, Jew as death-bearing threat to racial body |
| Death logic | Sacrifice for republic | Death as fuel for immortal collective body |
| Historical enactment / alignment | Mobilization, battlefield death, emancipation, reunion practice | Policy, implementation, social uptake, exterminatory outcomes |
| Overall support rating | To be scored after annotation and corroboration | To be scored after annotation and corroboration |
| Guilt structure | Shared guilt, slavery, Providence | Projected guilt, racialized blame |
| Endpoint | Reconciliation possible | Purification without stable endpoint |

## Required cautions

The comparison must state:

- structural comparison is not moral equivalence
- similarities in metaphor form do not imply equivalence in political content
- differences in enemy construction, endpoint, and violence logic are central
- each figure must be read in historical context

## Output

`comparative-analysis.md`

---

# Stage 15: Corroboration, Audit, and Publication Package

## Objective

Prepare the project for scholarly review.

## Purpose

The final stage packages the evidence, methodology, and interpretation so that reviewers can inspect the chain from claim to text.

## Required publication package

| Component | Purpose |
|---|---|
| `research-design.md` | Defines scope and method |
| `corpus-register.csv` | Documents included texts |
| `annotation-codebook.md` | Defines coding rules |
| `historical-semantics-notes.md` | Controls for period meaning |
| `mipvu-annotations.csv` | Records metaphor identification |
| `reliability-report.md` | Shows coding stability |
| `cmt-mappings.csv` | Records conceptual mappings |
| `corpus-analysis.md` | Presents frequency, distribution, genre, chronology |
| `critical-metaphor-analysis.md` | Explains ideological persuasion |
| `rhetorical-genre-analysis.md` | Interprets historical occasion and audience |
| `absence-agency-analysis.md` | Documents silence, agency, and exclusion |
| `historical-enactment-alignment.md` | Corroborates historical policies, practices, implementation, social uptake, and outcomes |
| `support-ratings.csv` | Records document-level and case-level 0–4 support scores |
| `koenigsbergian-support-synthesis.md` | Presents evidentiary-support assessment |
| `ai-use-statement.md` | Explains AI role and human responsibility |
| `data-availability.md` | Explains what can be shared and reused |

## Audit chain

Every major claim should be traceable:

```text
Claim
  → support dimension
    → support score
      → cluster
        → conceptual mapping
          → metaphor-related lexical units
            → sentence IDs
              → document metadata
                → source text
                  → historical corroboration where claimed
```

## Example audit chain

| Level | Example |
|---|---|
| Claim | Lincoln transforms battlefield death into political rebirth |
| Support dimension | Sacrificial body |
| Support score | Example: 3 = strong support, pending full-case scoring |
| Cluster | Birth / generation |
| Conceptual mapping | POLITICAL RENEWAL IS BIRTH |
| Lexical evidence | conceived, brought forth, new birth |
| Rhetorical setting | Gettysburg dedication |
| Ideological function | Sacrifice becomes obligation to complete unfinished work |
| Historical corroboration | Gettysburg battlefield death, cemetery dedication, public mourning, Civil War mobilization |
| Source text | Gettysburg Address |

---

# Controlled Vocabularies

## Source domains

Use a controlled source-domain vocabulary. Suggested initial list:

- body
- disease
- wound / injury
- medicine / healing
- birth / generation
- family / inheritance
- architecture / building
- law / contract
- debt / accounting
- religion / Providence
- sacrifice
- journey / motion
- experiment / science
- agriculture
- mechanics
- war / combat
- light / darkness
- slavery / bondage
- nature / organism

## Target domains

Suggested initial list:

- nation
- Union
- Constitution
- republic
- democracy
- freedom
- slavery
- Civil War
- emancipation
- sacrifice
- founding
- Providence
- reconciliation
- citizenship
- enemy
- people
- law
- history

## Rhetorical functions

Suggested initial list:

- exhortation
- warning
- accusation
- justification
- consolation
- mourning
- consecration
- reconciliation
- legitimation
- instruction
- memorialization
- condemnation
- prophecy
- national self-definition

## Ideological functions

Suggested initial list:

- sacralization
- obligation
- sacrifice
- guilt distribution
- redemption
- purification
- displacement
- enemy construction
- collective immortality
- moral accounting
- agency suppression
- reconciliation
- historical destiny
- providential judgment

---

# AI-Use and Research Integrity

## Principle

AI may assist the research process, but it should not be treated as an independent scholarly authority.

## Recommended AI-use policy

| Task | AI Role | Human Responsibility |
|---|---|---|
| Text preparation | Assist with formatting and segmentation | Verify against source |
| Metadata extraction | Suggest metadata | Confirm from scholarly source |
| Candidate metaphor detection | Suggest possible metaphor-related units | Apply MIPVU manually and document uncertainty |
| Historical semantics | Suggest reference needs | Confirm with period sources |
| CMT mapping | Suggest possible source-target mappings | Decide, justify, and record rival readings |
| Cluster discovery | Suggest patterns | Test against annotations |
| Corpus summaries | Assist synthesis | Check against evidence |
| Writing | Draft or revise prose | Human authorship and responsibility |
| Final claims | No authority | Scholar takes responsibility |

## AI-use statement template

```markdown
AI tools were used to assist with text preparation, candidate identification, organization of annotations, and drafting support. All metaphor-identification decisions, conceptual mappings, interpretive claims, and final scholarly conclusions were reviewed and authorized by the researcher. AI-generated suggestions were treated as provisional and were not used as independent evidence.
```

---

# Minimum Viable Scholarly Upgrade

If the full pipeline is too large for the first publication, the project should prioritize the following minimum upgrade:

1. Formal corpus register
2. Annotation codebook
3. MIPVU-based metaphor identification
4. Historical semantics notes for difficult terms
5. CMT mapping table
6. Reliability sample on 10–20% of corpus
7. Corpus-level distribution analysis
8. Rhetorical/genre controls
9. Historical enactment/alignment notes for any historical claim
10. Four-dimension support ratings
11. Rival readings and negative cases
12. Audit trail from claims to source text and historical corroboration where claimed
13. AI-use statement

This minimum version would still be substantially more credible than a purely interpretive or AI-assisted close-reading pipeline.

---

# Recommended Repository Structure

```text
lincoln-metaphor-analysis/
  docs/
    methodology/
      PIPELINE-UPGRADE.md
      research-design.md
      annotation-codebook.md
      ai-use-statement.md
      data-availability.md
    analysis/
      corpus-analysis.md
      critical-metaphor-analysis.md
      rhetorical-genre-analysis.md
      diachronic-analysis.md
      absence-agency-analysis.md
      historical-enactment-alignment.md
      support-ratings.csv
      koenigsbergian-support-synthesis.md
      comparative-analysis.md
  data/
    corpus/
      raw/
      normalized/
      segmented/
    metadata/
      corpus-register.csv
    annotations/
      mipvu-annotations.csv
      cmt-mappings.csv
      adjudication-log.csv
    outputs/
      frequency-tables.csv
      cluster-distribution.csv
      metaphor-timeline.csv
  references/
    historical-semantics-notes.md
    bibliography.md
```

---

# Final Description of the Credible Scholarly Method

A credible scholarly version of the pipeline would proceed as follows:

> A historically controlled, TEI-documented Lincoln corpus is segmented into stable textual units. Lexical units are identified and coded using MIPVU, with historical semantics controls to prevent anachronistic readings. A reliability sample is double-coded and adjudicated using a formal annotation codebook. Metaphor-related expressions are then mapped through Conceptual Metaphor Theory into source and target domains, with entailments, confidence levels, and rival readings recorded. Corpus-Assisted Discourse Studies methods examine frequency, distribution, collocation, genre variation, rhetorical salience, and diachronic change. Critical Metaphor Analysis and rhetorical criticism interpret how metaphor clusters persuade, authorize, console, accuse, sacralize, or reconcile. Systematic absence and agency analysis records who acts, who suffers, who is displaced, and who is excluded. Historical enactment/alignment analysis then asks whether textual-symbolic patterns align with documented policies, practices, implementation, social uptake, or outcomes. Only after these stages does Koenigsbergian evidentiary-support synthesis assess the degree to which the case supports, complicates, or limits Koenigsberg’s Law of Sacrifice across sacred object, sacrificial body, enemy as death, and historical enactment/alignment dimensions. All major claims are supported by an audit trail linking interpretation back to support scores, coded lexical units, sentence IDs, document metadata, source text, and historical corroboration where claimed.
