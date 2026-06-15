# Lincoln Historical Semantics Notes

Status: draft reference apparatus for MIPVU and CMT review.

These notes identify terms in the Lincoln pilot corpus that require
nineteenth-century semantic control before metaphor decisions or conceptual
mappings are treated as publication-grade. The notes are not final dictionary
entries. They are a working apparatus for deciding which basic meanings,
period sources, and rival readings must be checked during annotation.

## Reference Apparatus

Use period and domain-appropriate references before assigning high-confidence
MIPVU or CMT decisions for the terms below:

- Noah Webster, *An American Dictionary of the English Language* (1828).
- John Bouvier, *A Law Dictionary* (1856 edition or another period-near
  edition), for legal and constitutional terms.
- King James Bible and nineteenth-century Protestant biblical idiom, for
  judgment, offense, providence, blood, and atonement-adjacent language.
- Roy P. Basler, ed., *The Collected Works of Abraham Lincoln*, for textual
  variants, date notes, and immediate rhetorical context.
- Lincoln scholarship or historically grounded rhetorical criticism where
  ordinary dictionary meaning is not enough to resolve register, genre, or
  theological usage.

## Term Controls

| Term | Main documents | Preliminary period-control note | Semantic shift risk | Reference source to check | Annotation use |
|---|---|---|---|---|---|
| bond / bondsman | Second Inaugural | May invoke legal obligation, enslaved status, debt, and binding relation. In "bondsman's ... toil," avoid flattening the term into modern metaphor alone; the enslaved legal condition is literal while debt/accounting entailments may become relevant nearby. | high | Webster 1828; Bouvier 1856; slavery-law scholarship | Distinguish literal slavery reference from debt/binding mappings in adjacent "wealth," "toil," "sunk," and repayment language. |
| compact | Lincoln corpus and contextual Union rhetoric | "Compact" may refer to agreement, covenant-like political relation, or constitutional theory. Do not assume modern "small" meaning. | high | Webster 1828; Bouvier 1856; constitutional history | Use for Union/legal mappings only when the local text supports agreement or obligation. |
| experiment | Lyceum Address | In republican political rhetoric, an "experiment" may be a trial of self-government whose success remains historically uncertain. It is not merely laboratory science. | medium | Webster 1828; republican rhetoric scholarship | Source domain may be trial/proof rather than modern scientific method. |
| proposition | Gettysburg Address; Lyceum Address | "Proposition" may mean a statement advanced for proof or a political principle. In Gettysburg, it links equality to a founding claim under trial. | medium | Webster 1828; Declaration and republican rhetoric scholarship | Consider experiment/proof and law/political-principle readings. |
| judgment | Second Inaugural | May be legal, moral, and theological. In providential context, "judgments of the Lord" should be controlled by biblical idiom. | high | King James Bible; Webster 1828; Protestant sermon rhetoric | Do not reduce to ordinary opinion; track providential judgment separately from human legal judgment. |
| offense | Second Inaugural | In "offenses" and "offense," biblical usage can mean stumbling block, sin, or cause of transgression. Modern "insult" is too narrow. | high | King James Bible, Matthew 18:7; Webster 1828 | Required control for Providence/guilt mappings. |
| house | Lincoln contextual rhetoric | In Lincoln's broader "house divided" usage, "house" can mean household, lineage, polity, or constructed dwelling. | medium | Webster 1828; biblical and political rhetoric scholarship | Use body/building/family readings only when local evidence supports them. |
| Union | Second Inaugural and broader Lincoln corpus | "Union" is a constitutional-political entity and a sacred collective object candidate. Avoid treating it as a generic synonym for nation without context. | high | Bouvier 1856; constitutional history; Lincoln scholarship | Track whether Union is legal object, national body, sacred object, or reconciliation endpoint. |
| sacrifice | Lyceum Address and Gettysburg/war context | "Sacrifice" may be literal religious offering, costly loss, patriotic death, or moralized expenditure. The term can be explicit or structurally present without the word appearing. | high | Webster 1828; biblical idiom; Civil War commemoration scholarship | Use for sacrificial-body dimension only with traceable death, offering, payment, consecration, or obligation evidence. |
| birth / conceived / brought forth | Gettysburg Address | Birth language maps political founding and renewal through generation. "Conceived" and "brought forth" require family/generation controls. | medium | Webster 1828; CMT mapping notes; Lincoln scholarship | Candidate mapping: political founding or renewal is generation/birth. Record rival legal/founding-formula reading. |
| blood | Lyceum Address; Second Inaugural | Blood may be literal bodily substance, kinship/descent, guilt, violence, payment, or biblical-moral accounting. | high | Webster 1828; King James Bible; Civil War religious rhetoric | Separate literal bloodshed from moral accounting and sacrificial entailments. |
| Providence / Almighty / God | Second Inaugural | Providence language may signal theological causality, judgment, humility before divine purpose, or rhetorical constraint on human agency. | high | King James Bible; Protestant sermon rhetoric; Lincoln scholarship | Track Providence as target/source carefully; avoid private-belief claims unless independently supported. |
| consecrate / hallow / dedicate | Gettysburg Address | These terms carry religious and ritual-register force but may also be conventional ceremonial language. | high | Webster 1828; biblical/liturgical usage; cemetery dedication rhetoric | Use for sacralization only with attention to ceremony, battlefield death, and rival conventional reading. |

## Annotation Guidance

- Record `basic_meaning_source` with enough specificity for review, such as
  `Webster 1828, "conceive"` or `KJV Matthew 18:7 / Webster 1828, "offense"`.
- Use `semantic_shift_risk` from `config/controlled-vocabularies.json` when a
  term requires period control.
- If a term is both literal and metaphorically active, preserve both roles in
  `review_notes`; do not force the lexical unit into a purely figurative
  reading.
- If legal, biblical, or ceremonial register explains an expression better
  than CMT mapping, record that rival reading rather than inflating the
  metaphor evidence.
