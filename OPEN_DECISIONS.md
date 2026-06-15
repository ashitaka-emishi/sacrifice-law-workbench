# Open Decisions

Use this document as the living record of decisions deferred during project setup and later research.

## Known open decisions

- Exact balanced-core word-count target after source discovery.
- Final case phase models after starter corpus research.
- Final shared cross-case cluster taxonomy after annotation.
- Final case-specific clusters after case-level annotation.
- Exact limits on Goebbels/Göring support material in the Hitler case.
- Translation sources and translation-risk thresholds for Hitler and Napoleon (both resolved 2026-06-14).
- Whether to introduce LangGraph after v1 stabilizes.
- Exact inter-coder reliability procedure for human review.
- Which artifacts should be treated as final, draft, or exploratory on the public site.
- Current publication-level primary research question is defined in
  `PRIMARY_RESEARCH_QUESTION.md`; revisit after scholarly review and the first
  complete annotated case.
- Final support-rating implementation details after first scored case,
  including document-weight governance, historical corroboration thresholds,
  and whether any formula adjustments are warranted.
- Final first-publication shape after the first complete annotated case:
  cross-case methods article, Lincoln-centered case study, theory-testing
  chapter, or another form.
- Final venue-specific AI-use disclosure wording, while preserving the
  commitment that AI suggestions are provisional and not independent evidence.
- Final data-availability wording for mixed rights-status corpora, especially
  where committed metadata and annotations must point to gitignored-local,
  fair-use-only, metadata-only, or unavailable source text.
- Exact artifact-readiness rules for promoting draft outputs to
  publication-facing findings after the first complete annotated case.

## Rights-review blockers (opened 2026-06-13)

### Hitler: Mein Kampf English translation copyright

Status: **resolved 2026-06-13 — proceed on German original + Murphy with caveat**

Research findings:

- **German original**: U.S. copyright held by Houghton Mifflin (purchased from U.S. government 1979, seized under Trading with the Enemy Act WWII) expired **2020** (95 years after 1925 publication). Wikisource German text is fully public domain in both Germany (2016) and the U.S. (2020). No restriction on use.
- **Murphy 1939 translation** (Hutchinson, UK): Published in the UK with no evidence of U.S. copyright registration or renewal. Under pre-1978 U.S. formalities, a foreign work published without U.S. registration did not receive U.S. copyright protection. Working conclusion: **likely U.S. public domain**. Freely hosted at Project Gutenberg Australia and hcommons.org with no recorded U.S. legal challenge. Proceed with documented caveat; formal fair-use opinion is belt-and-suspenders if required for publication.
- **Manheim 1943 translation** (Houghton Mifflin): U.S. copyright registered and renewed 1971. Under copyright until **2038**. Do not use.

**Decision**: Use German Wikisource text as primary corpus input. Use Murphy translation as documented translation aid for annotation glosses, with caveat noted per annotation that U.S. PD status is working conclusion, not formal opinion. Do not reproduce Manheim text under any circumstances.

### Hitler: Reichstag prophecy and war speeches U.S. copyright status

Status: **resolved 2026-06-13 — proceed using GPA excerpts under scholarly fair use**

Nazi government speech publications (pre-1945) were not registered in the U.S. and almost certainly did not comply with pre-1978 U.S. copyright formalities. The German originals are public domain in Germany (70 years after Hitler's death, 2015). U.S. status of originals is effectively public domain on formalities grounds, but not formally verified.

**Decision**: Proceed using the German Propaganda Archive (Calvin University) excerpts under scholarly fair use for annotation prompt inputs. Treat full speech text as metadata-only in the registry until a specific U.S. publication-with-notice instance is identified that would revive the copyright question. Do not reproduce Domarus English edition (Bolchazy-Carducci, 1990–2004), which is under U.S. copyright. Record German original passages with Domarus volume/page reference in manifest for traceability.

### Hitler: German source text and annotation language

Status: **resolved 2026-06-14 — annotate from German originals (gitignored local copies) with English glosses**

Clean machine-readable German text is not available from any open source (Wikisource has no MK text; Archive.org German scans are Fraktur OCR). The IfZ 2016 critical edition (Mein Kampf) and Domarus German edition (speeches) are used locally under scholarly fair use.

**Decision**: Annotate from German source text. Raw text files are gitignored and never committed or published. Each annotation instance records `span_text` in German. English glosses are added per instance using Murphy 1939 (MK) and GPA translations (speeches) as reference only — not as corpus text.

Key watch-list terms requiring `gloss_notes`: *Volk, Opfer, Blut, Rasse, Reinheit, Vernichtung, Ausrottung, jüdisch-bolschewistisch*. For *Vernichtung* specifically, gloss notes must address the Browning/Goldhagen historiographical debate on intentionalist vs. functionalist readings.

Files to place locally (see README.md in each raw dir for provenance header format):

- `cases/hitler/corpus/raw/hitler-src-01-mein-kampf-selected/` — 6 chapter files from IfZ edition
- `cases/hitler/corpus/raw/hitler-src-02-reichstag-war-speeches/` — 2 speech files from Domarus

After placing files, re-run `normalize-texts.py --case hitler` and `segment-texts.py --case hitler` to replace current English corpus with German text. Current English files in `corpus/text/` and `corpus/segmented/` are also gitignored.

The `case-config.json`, `document-manifest.json`, and `source-registry.json` for the Hitler case have been updated to reflect this. The annotation prompt has been updated.

### Napoleon: English translation source

Status: **resolved 2026-06-14 — annotate in French with English glosses**

French originals (Correspondance de Napoléon Ier, Bulletins de la Grande Armée) are public domain. No single authoritative English translation exists for either source set.

**Decision**: Annotate directly from the French source text. Each annotation instance records `span_text` in French as it appears in the corpus. Two optional gloss fields are added to every napoleon instance:

- `gloss_en`: a working English rendering of the span, sufficient for CMT mapping purposes
- `gloss_notes`: free-text notes on contested terms where translation choice affects source-domain assignment (particularly: *gloire*, *sacrifice*, *patrie*, *honneur*, *victoire*, *mort*)

Rationale: preserves fidelity to the source; avoids committing to an authoritative translation that does not exist; keeps translation risk visible at the instance level rather than baking it into the corpus text. Glosses are analytical aids, not publication translations.

The annotation prompt (`prompts/metaphor-annotation-prompt.md`) and annotation schema (`schemas/annotation-schema.json`) have been updated to reflect this methodology. The napoleon `case-config.json` records `"source_language": "fr"` and `"annotation_language_policy": "source-with-glosses"`.
