# Pre-v1 Expansion Candidate Matrix

Status: candidate-ranking artifact for GitHub issue #176.

This matrix applies the pre-v1 expansion rubric in `case-selection.qmd`.
It is a selection document, not a rights-clearance decision. Rights,
provenance, source-edition, and storage decisions remain follow-up work for
issue #177 before any new source text enters the corpus.

## Recommendation

Admit a small expansion set:

1. Add **French Revolution / Jacobin Republic** as the first new case.
2. Add **British World War I / Lloyd George wartime leadership** as the second
   new case.
3. Add a tightly bounded set of existing-case documents for American
   Revolution, Lincoln, and Napoleon.
4. Defer Imperial Japan as the highest-value reserve candidate unless issue
   #177 quickly resolves source-language, translation, and rights questions.

This set improves the comparative design without reopening the corpus as a
general source-harvesting project. It adds one strongly positive
revolutionary-purification case, one democratic wartime limiting/control case,
and a few document-level repairs to current cases.

## Candidate Case Ranking

| Rank | Candidate ID | Proposed layer | Primary rationale | Comparative role | Source base to review | Rights risk | Language policy | Expected corpus size | Annotation cost | Reliability impact | Comparative gain | Exclusion risk | Recommendation |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `fr-rev` | New case | Confirmatory + comparative | Positive test for republican virtue, purification, terror, sacred people, and enemy construction outside the current leader/empire/genocide set. | French originals from Robespierre/Saint-Just speeches, Convention reports, and public revolutionary texts; English translations only as aids if rights-cleared. | Medium until editions and translations are chosen; likely low for French originals. | Annotate French source text with English glosses for contested terms such as vertu, patrie, peuple, tyrannie, purification, terreur, sacrifice. | Medium: 4-6 documents or excerpts, roughly 20k-40k source words. | Medium: French source-language MIPVU and gloss review required. | Human/model reliability sampling should include at least one French revolutionary document or a targeted French-language validation sample. | Tests whether sacrifice/purification logic appears in revolutionary virtue and terror without collapsing into the Napoleon or Hitler patterns. | Can become too broad if the whole Revolution replaces a leader/movement-centered corpus. | Admit as first new case after #177 rights/provenance review. |
| 2 | `wwi-britain` | New case | Limiting/control + comparative | Democratic wartime mobilization case with sacrifice and endurance rhetoric but no genocidal enemy-destruction project. | Lloyd George wartime speeches, parliamentary speeches, war addresses, and published wartime collections; possible Asquith or royal texts only if needed for phase coverage. | Low-medium; many candidate texts are pre-1929 publications, but edition-specific rights review is still required. | English source text. No translation burden. | Medium-small: 5-7 speeches or addresses, roughly 20k-35k words. | Low-medium: English, familiar register, but wartime parliamentary rhetoric may be long. | Useful as an English-language reliability contrast for non-genocidal wartime rhetoric. | Adds non-U.S. democratic wartime comparison and tests whether sacrifice language alone predicts strong Koenigsbergian support. | May duplicate Lincoln's democratic wartime register unless documents are chosen for distinct empire, parliamentary, and total-war context. | Admit as second new case after #177 rights/provenance review. |
| 3 | `imperial-japan` | New case or reserve case | Comparative + confirmatory | Non-Western imperial-sacrificial and emperor-centered case; possible strong test for sacred object, death obligation, and body-politic loyalty. | Imperial Rescript on Education, Imperial Rescript to Soldiers and Sailors, wartime rescripts, official translations, kokutai materials, and selected wartime speeches. | Medium-high until Japanese originals, official translations, and storage policy are resolved. | Prefer Japanese source text with English glosses; official English translations may be aids only unless rights-cleared. | Medium: likely 15k-35k words for a compact core. | High: Japanese source-language annotation and translation-sensitive terms require specialist review. | Would force reliability sampling to address a non-European, non-English case. | Adds the strongest language/geographic contrast and tests sacrifice without importing Western Christian/republican assumptions. | Translation and rights risk could delay the whole expansion window. | Defer as reserve; admit only if #177 clears a compact source set quickly. |
| 4 | `wilson-wwi` | New case or backup | Control + source-availability | U.S. democratic wartime mobilization, international moral order, sacrifice, and enemy threat. | Public presidential messages and speeches, including 1917 war message and wartime addresses. | Low for U.S. government/public presidential materials, subject to edition review. | English source text. | Small-medium: 4-6 speeches, roughly 15k-30k words. | Low. | Useful reliability comparison, but adds another U.S. case. | Very easy acquisition and clean provenance. | Overweights U.S. democratic rhetoric after American Revolution and Lincoln. | Defer; use only if British WWI fails rights/provenance review. |
| 5 | `stalin-wwii` | Future case | Comparative + limiting/confirmatory | Soviet patriotic war, leader/state/people rhetoric, enemy annihilation, sacrifice, and ideological sacred object. | Russian wartime speeches, orders, radio addresses, official English translations, Soviet publications. | Medium-high; translation and edition rights need careful review. | Russian source text with English glosses if admitted. | Medium. | High. | Would require Russian-language reliability planning. | Adds communist/state-socialist contrast. | Source and translation complexity likely too high for a bounded pre-v1 window. | Defer to future milestone. |
| 6 | `mao-ccp` | Future case | Comparative | Revolutionary communist mass-mobilization and sacrifice rhetoric. | Mao selected works, party documents, speeches, and translations. | High; modern copyright and translation rights likely constrain committed corpus use. | Chinese source text with English glosses if ever admitted. | Medium-large. | High. | Would require Chinese-language reliability planning. | Adds non-Western revolutionary contrast. | Rights, translation, and corpus-boundary burden exceed current window. | Reject for pre-v1; revisit only as future metadata/context work. |

## Recommended New Case Set

### First new case: `fr-rev`

Use a compact Jacobin-centered corpus rather than the whole French Revolution.
The candidate core should privilege public speeches and Convention reports
that test virtue, terror, sacred people/nation, purification, enemies, and
republican sacrifice.

Candidate target documents for issue #177 review:

- Robespierre, speech/report on political morality, 5 February 1794.
- Robespierre, report on the relationship of religious and moral ideas to
  republican principles, 7 May 1794.
- Saint-Just, selected Convention report on imprisoned persons or public safety.
- A short revolutionary declaration, decree, or public address only if needed
  for genre contrast.

Boundary rule: do not let `fr-rev` become a general Revolution corpus. The
case should be Jacobin-centered, phase-bounded, and source-language French with
glosses.

### Second new case: `wwi-britain`

Use Lloyd George-centered wartime leadership as the main layer. The corpus
should test whether sacrifice, endurance, civilization, duty, and enemy-threat
language in a democratic wartime setting produces strong, limited, or
complicated support for the Law.

Candidate target documents for issue #177 review:

- Lloyd George wartime speeches from 1914-1918, selected for phase coverage.
- One early-war mobilization speech.
- One mid-war endurance or sacrifice speech.
- One late-war victory, reconstruction, or war-aims speech.
- Add Asquith or royal material only if Lloyd George alone cannot provide
  phase or genre coverage.

Boundary rule: keep the case non-genocidal and democratic-war focused. It
should function as a limiting/control case, not as another maximal positive
case.

## Existing-case Targeted Additions

| Priority | Case | Candidate document | Proposed layer | Rationale | Source base to review | Rights risk | Annotation cost | Recommendation |
|---:|---|---|---|---|---|---|---|---|
| 1 | `am-rev` | Jefferson rough draft of the Declaration | Existing-case balanced core or extended corpus | The source registry already identifies the draft as analytically important for editorial suppression and substitution of sacrifice language. | Founders Online / National Archives materials already referenced in `cases/am-rev/metadata/source-registry.json`. | Low, pending source-record confirmation. | Low-medium. | Admit if #177 confirms source path and storage policy. |
| 2 | `am-rev` | Washington's Newburgh Address, 15 March 1783 | Existing-case extended corpus | Adds crisis-of-army, sacrifice, debt, honor, and civil-military restraint after military service. | Founders Online or National Archives transcription to verify. | Low-medium. | Low-medium. | Admit if it does not duplicate existing 1783 circular/order material. |
| 3 | `lincoln` | First Inaugural Address, 4 March 1861 | Existing-case balanced core | Adds prewar union, constitutional oath, sacred bond, coercion/force limits, and disunion before battlefield sacrifice. | Library of Congress / Miller Center / public-domain presidential text to verify. | Low. | Low. | Admit; it fills a phase gap before Lyceum, Gettysburg, and Second Inaugural. |
| 4 | `lincoln` | Special Message to Congress, 4 July 1861 | Existing-case extended corpus | Adds war-authorization, democracy-as-experiment, rebellion, sacrifice, and constitutional crisis rhetoric. | Public-domain presidential message sources to verify. | Low. | Medium due length. | Admit only if the expanded Lincoln case can tolerate one long war-message document. |
| 5 | `napoleon` | Proclamation to the Army of Italy, 1796 | Existing-case extended corpus | Adds non-bulletin leader-to-army address from the rise phase and tests glory, destiny, poverty/plunder, and army-body rhetoric. | French original in Napoleon correspondence or public historical collections to verify. | Low-medium. | Medium: French glosses needed. | Admit if source text is clean enough; otherwise defer. |
| 6 | `napoleon` | Farewell to the Old Guard, 1814 | Existing-case metadata-only or extended corpus | Adds defeat/abdication, loyalty, glory, and body-politic residue after imperial collapse. | French original and edition status to verify. | Low-medium. | Low due short text. | Defer unless phase-closure evidence is needed; it may distort the current battle-bulletin design. |
| 7 | `hitler` | Goebbels or Goering support material | Existing-case support layer | Could test whether non-Hitler Nazi rhetoric strengthens or shifts the existing Hitler-centered findings. | German originals and translation/storage policy unresolved. | Medium-high. | High. | Defer; do not add until the existing open decision on support-material limits is resolved. |

## Explicit Exclusions For This Window

- Do not add a broad "all French Revolution" corpus.
- Do not add a broad "all World War I Britain" corpus.
- Do not add Wilson if `wwi-britain` clears rights review; doing both would
  overweight English democratic wartime cases.
- Do not add Imperial Japan unless #177 resolves a compact, source-language
  corpus with manageable translation and storage policies.
- Do not add Mao/CCP materials in this window because modern rights and
  translation constraints are too likely to slow the milestone.
- Do not add new Hitler support texts until the support-material boundary is
  decided.
- Do not redownload or replace current verified corpora except to repair a
  documented source defect.

## Issue Routing

- #177 should rights-review the recommended `fr-rev`, `wwi-britain`, and
  existing-case additions before acquisition.
- #178 should add `fr-rev` if #177 clears its compact source set.
- #179 should add `wwi-britain` if #177 clears its compact source set.
- #180 should add only the approved targeted documents for existing cases.
- #183 should update reliability sampling after the expansion set is confirmed.
