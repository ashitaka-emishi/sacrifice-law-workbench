# Pre-v1 Expansion Rights and Provenance Review

Status: rights/provenance gate for GitHub issue #177.

This review applies the corpus rights policy to the candidate set selected in
`docs/corpus/pre-v1-expansion-candidate-matrix.md`. It is a working project
rights decision, not formal legal advice. No raw text should enter
`cases/*/corpus/raw/` unless the relevant source below is marked
`approved-for-ingestion` and the later case/document manifests preserve the
source URL, citation, rights rationale, storage policy, and verification
anchors.

## Summary Decision

Proceed with a compact expansion, but only from sources with clear public-domain
or rights-safe provenance:

- **Approve for #178:** French Revolution / Jacobin Republic, limited to
  Robespierre source-language French texts from Project Gutenberg's public
  domain French edition. Saint-Just remains metadata-only until a clean
  public-domain source edition is selected.
- **Approve for #179:** British World War I / Lloyd George wartime leadership,
  using pre-1929 Internet Archive source editions as committed public-domain
  raw text after document-level verification.
- **Approve for #180:** Jefferson rough draft, Washington Newburgh Address,
  Lincoln First Inaugural, Lincoln 4 July 1861 Special Message, and Napoleon's
  1796 Army of Italy proclamation if a Gallica source-edition path is pinned.
- **Defer:** Napoleon Farewell to the Old Guard, Imperial Japan, Stalin WWII,
  Mao/CCP, Wilson WWI, and Hitler support material.

## Source Registry Decisions

The provisional registry entries are recorded in
`docs/corpus/pre-v1-expansion-source-registry.json`. When a case or document is
actually added, copy the relevant entry into the case-local source registry and
replace any broad collection URL with the exact document or edition URL used.

| Source ID | Candidate | Decision | Storage | Rationale |
|---|---|---|---|---|
| `fr-rev-src-01-robespierre-discours-pg` | Robespierre speeches, 1792-1794 | approved-for-ingestion | committed | Project Gutenberg hosts the French edition as a U.S. public-domain ebook. Use only the French source text; translations are analytical aids only. |
| `fr-rev-src-02-saint-just-public-safety` | Saint-Just Convention/Public Safety report | metadata-only-deferred | metadata-only | The candidate remains analytically valuable, but this review did not pin a clean source edition and URL. Do not ingest until #178 or follow-up work selects a public-domain edition. |
| `wwi-britain-src-01-through-terror-to-triumph` | Lloyd George, `Through Terror to Triumph` | approved-for-ingestion | committed | Internet Archive has 1915 scans. U.S. public-domain status follows publication before 1929, subject to exact-edition verification. |
| `wwi-britain-src-02-great-crusade` | Lloyd George, `The Great Crusade` | approved-for-ingestion | committed | Internet Archive has 1918 scans. U.S. public-domain status follows publication before 1929, subject to exact-edition verification. |
| `am-rev-src-04-jefferson-rough-draft` | Jefferson rough draft of Declaration | approved-for-ingestion | committed | Founders Online/National Archives source was already cited in the existing registry. Use as a document-level expansion only after anchors are set. |
| `am-rev-src-05-washington-newburgh` | Washington Newburgh Address | approved-for-ingestion | committed | Founders Online/National Archives source URL is identified, but browser/CAPTCHA workflows may be needed for acquisition. |
| `lincoln-src-04-first-inaugural` | Lincoln First Inaugural | approved-for-ingestion | committed | Lincoln's 1861 presidential text is public-domain. Pin one transcription source before ingestion; Library of Congress is preferred where accessible. |
| `lincoln-src-05-special-message-1861-07-04` | Lincoln Special Message to Congress | approved-for-ingestion | committed | Lincoln's 1861 presidential text is public-domain. Pin one transcription source before ingestion; Library of Congress or a public-domain presidential text collection is acceptable. |
| `napoleon-src-03-army-of-italy-proclamation` | Napoleon 1796 Army of Italy proclamation | conditional-approval | committed if Gallica/French source is pinned | The French text is public-domain by age, but ingestion must pin the exact Gallica or equivalent public-domain edition. Do not use unsourced web quotations. |
| `napoleon-src-04-farewell-old-guard` | Napoleon Farewell to Old Guard | metadata-only-deferred | metadata-only | Short, useful phase-closure evidence, but not necessary for the expansion window and no exact source edition is pinned here. |
| `imperial-japan-src-01-rescripts` | Imperial Japan reserve source set | metadata-only-deferred | metadata-only | High comparative value, but source-language, official-translation, and storage policies require a dedicated review. |
| `hitler-src-03-support-material` | Goebbels/Goering support layer | metadata-only-deferred | metadata-only/gitignored-local TBD | Existing open decision on support-material limits is unresolved; do not add in #180. |

## Rights and Provenance Notes

### French Revolution / Jacobin Republic

Use a compact Robespierre-centered source base for #178. Project Gutenberg
ebook 29887, `Discours par Maximilien Robespierre -- 17 Avril 1792-27 Juillet
1794`, is suitable as a starting source edition because it is a U.S.
public-domain ebook and contains French source-language speeches in the target
period.

Approved target documents:

- Robespierre, report/speech on political morality, 5 February 1794.
- Robespierre, report/speech on religious and moral ideas, 7 May 1794.

Policy:

- Annotate French source text.
- Add English glosses only as analytical aids.
- Do not commit modern English translations unless separately rights-cleared.
- Keep Saint-Just metadata-only until the exact public-domain source edition is
  selected.

### British World War I / Lloyd George

Use pre-1929 Lloyd George editions found on Internet Archive. The highest-value
source editions for #179 are:

- `Through Terror to Triumph` (1915), speeches and pronouncements since the
  beginning of the war.
- `The Great Crusade` (1918), extracts from wartime speeches.

Policy:

- Commit English source text only after exact edition selection and local
  verification.
- Prefer complete source-edition transcription or extracted OCR with manual
  correction over unattributed speech snippets.
- Do not add Wilson WWI if Lloyd George clears review; Wilson remains a backup
  to avoid over-weighting English-language democratic wartime cases.

### Existing-Case Additions

Approved for #180 review and ingestion:

- Jefferson rough draft of the Declaration, from Founders Online/National
  Archives.
- Washington Newburgh Address, from Founders Online/National Archives.
- Lincoln First Inaugural Address, from a pinned public-domain presidential or
  Library of Congress source.
- Lincoln Special Message to Congress, 4 July 1861, from a pinned
  public-domain presidential or Library of Congress source.

Conditional or deferred:

- Napoleon's 1796 Army of Italy proclamation is approved only after #180 pins a
  Gallica or equivalent public-domain French source edition.
- Napoleon's Farewell to the Old Guard is deferred as metadata-only.
- Hitler support material is deferred until the support-material boundary is
  resolved.

## Data Availability Implications

- Public-domain English and French source texts approved here may be committed
  if the selected edition permits repository storage and verification anchors
  are recorded.
- Source-language French texts must preserve gloss notes where translation
  choices affect metaphor identification or CMT mapping.
- Metadata-only/deferred sources may appear in source registries but should not
  be copied to `corpus/raw/`.
- Any later local-only source must have a public-safe reference index before
  public artifacts cite derived IDs or annotations.

## Sources Checked

- Project Gutenberg ebook 29887:
  `https://www.gutenberg.org/ebooks/29887`
- Project Gutenberg permissions policy:
  `https://www.gutenberg.org/policy/permission.html`
- Internet Archive `Through Terror to Triumph` records:
  `https://archive.org/details/throughterrortot00lloyuoft`
- Internet Archive `The Great Crusade` records:
  `https://archive.org/details/greatcrusadeextr00lloy`
- Cornell public-domain term reference:
  `https://guides.library.cornell.edu/copyright/publicdomain`
- Founders Online Jefferson rough draft URL already used by the project:
  `https://founders.archives.gov/documents/Jefferson/01-01-02-0176`
- Founders Online Washington Newburgh Address URL identified for review:
  `https://founders.archives.gov/documents/Washington/99-01-02-10840`
- Library of Congress Lincoln resources should be preferred where accessible:
  `https://www.loc.gov/collections/abraham-lincoln-papers/`
