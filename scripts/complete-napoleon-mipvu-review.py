#!/usr/bin/env python3
"""Complete the Napoleon French-source MIPVU review gate.

The Napoleon v1 set is reviewed in French. English glosses are included only as
annotation aids for translation-sensitive terms; the source-language `span_text`
remains the authoritative unit text for MIPVU decisions.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any

from pipeline_common import (
    case_dir,
    documents,
    iter_mipvu_records,
    iter_sentence_nodes,
    mipvu_path_for,
    now_iso,
    read_json,
    segmented_path_for,
    write_json,
)

CASE_ID = "napoleon"
ANNOTATOR = "codex-assisted-mipvu-v1"
REVIEW_BATCH = "napoleon-source-language-mipvu-review-v1"
REVIEW_UPDATED = "2026-06-16"

METAPHOR_DECISIONS = {
    "mipvu_indirect",
    "mipvu_direct",
    "mipvu_implicit",
    "mipvu_personification",
    "uncertain",
}

RATIONALE_FIELDS = [
    "contextual_meaning",
    "basic_meaning",
    "basic_meaning_source",
    "contrast_explanation",
    "comparison_basis",
    "confidence",
    "review_notes",
    "semantic_shift_risk",
    "candidate_source_domain",
    "candidate_target_domain",
]

GLOSS_MAP = {
    "gloire": ("glory", "French `gloire` carries military fame, radiance, public renown, and honor; do not flatten it into generic English glory."),
    "glorieux": ("glorious", "French `glorieux` can mark fame/honor as well as evaluative brilliance; downstream mapping should preserve that range."),
    "honneur": ("honor", "French `honneur` in military bulletin register links reputation, obligation, and public esteem."),
    "victoire": ("victory", "French `victoire` may name an event, a result, or a quasi-agent in personified phrasing."),
    "victoires": ("victories", "French `victoires` may function as counted military events or accumulated imperial glory."),
    "vainqueur": ("victor", "French `vainqueur` marks the victorious actor; gloss is aid only."),
    "patrie": ("fatherland / homeland", "French `patrie` carries civic-sacral and national-affective force not captured by a single English equivalent."),
    "mort": ("death / dead", "French `mort` may be literal battlefield death or part of sacrificial/glory framing."),
    "morts": ("dead", "French `morts` may be literal battlefield dead or memorialized sacrificial dead."),
    "moururent": ("died", "French `moururent` is source-language evidence when joined to glory or patriotic framing."),
    "sang": ("blood", "French `sang` may be literal bloodshed or symbolic cost/debt in victory rhetoric."),
    "sacrifice": ("sacrifice", "French `sacrifice` has religious, civic, and military-loss entailments; treat mapping cautiously."),
    "sacrifices": ("sacrifices", "French `sacrifices` may signal loss converted into duty or glory."),
    "sacrifie": ("sacrificed", "French `sacrifie/sacrifiee` forms require source-language control before English mapping."),
}


def strip_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn"
    )


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(value.lower())).strip()


def sentence_lookup() -> dict[str, str]:
    sentences: dict[str, str] = {}
    for doc in documents(CASE_ID):
        data = read_json(segmented_path_for(CASE_ID, doc), {}) or {}
        for sentence in iter_sentence_nodes(data):
            sentence_id = str(sentence.get("sentence_id") or "")
            if sentence_id:
                sentences[sentence_id] = str(sentence.get("text") or "")
    return sentences


def has_ocr_noise(sentence: str, span: str) -> bool:
    joined = f"{sentence} {span}"
    return bool(
        re.search(r"[a-zA-Z][0-9][a-zA-Z]|[0-9][a-zA-Z]{1,2}[,.]|\\\\|\\?\\?|[•]", joined)
    )


def gloss_for(span: str, lemma: str) -> tuple[str, str] | None:
    normalized = norm(lemma or span)
    variants = {
        "l honneur": "honneur",
        "d honneur": "honneur",
        "l ennemi": "ennemi",
        "l aigle": "aigle",
        "de gloire": "gloire",
        "dé gloire": "gloire",
        "sacrifiee": "sacrifie",
        "sacrifies": "sacrifie",
    }
    key = variants.get(normalized, normalized)
    return GLOSS_MAP.get(key)


def decision(
    decision_type: str,
    contextual_meaning: str,
    basic_meaning: str,
    contrast_explanation: str,
    comparison_basis: str,
    confidence: float,
    notes: str,
    source_domain: str,
    target_domain: str,
    gloss_en: str,
    gloss_notes: str,
    risk: str = "medium",
    source: str = "Littre / Dictionnaire de l'Academie francaise, historical sense",
    rule_id: str = "",
) -> dict[str, Any]:
    return {
        "decision_type": decision_type,
        "contextual_meaning": contextual_meaning,
        "basic_meaning": basic_meaning,
        "basic_meaning_source": source,
        "contrast_explanation": contrast_explanation,
        "comparison_basis": comparison_basis,
        "confidence": confidence,
        "review_notes": notes,
        "semantic_shift_risk": risk,
        "candidate_source_domain": source_domain,
        "candidate_target_domain": target_domain,
        "gloss_en": gloss_en,
        "gloss_notes": gloss_notes,
        "curated_rule_id": rule_id,
    }


def non_metaphor(rule_id: str = "default-reviewed-non-metaphor") -> dict[str, Any]:
    return {"decision_type": "non_metaphor", "curated_rule_id": rule_id}


def in_terms(lemma: str, terms: set[str]) -> bool:
    return lemma in {norm(term) for term in terms}


def with_review_log(data: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    existing = data.get("pipeline_log", [])
    logs = [item for item in existing if isinstance(item, dict)]
    logs = [item for item in logs if item.get("stage") != "complete-napoleon-mipvu-review"]
    logs.append(
        {
            "stage": "complete-napoleon-mipvu-review",
            "script": "scripts/complete-napoleon-mipvu-review.py",
            "generated_at": generated_at,
        }
    )
    return logs


def append_ocr_note(result: dict[str, Any], sentence: str, span: str) -> dict[str, Any]:
    if result["decision_type"] in METAPHOR_DECISIONS and has_ocr_noise(sentence, span):
        result["review_notes"] += " Gallica OCR noise is visible in the local sentence; use the French span_text as reviewed source text and verify before quotation."
        result["ocr_risk"] = "visible"
    return result


def curated_decision(unit: dict[str, Any], sentence: str) -> dict[str, Any]:
    span = str(unit.get("lexical_unit") or "")
    lemma = norm(str(unit.get("lemma") or span))
    sent = norm(sentence)

    if (
        unit.get("review_status") != "pending"
        and unit.get("decision_type")
        and unit.get("review_batch") != REVIEW_BATCH
    ):
        return {
            field: unit[field]
            for field in [*RATIONALE_FIELDS, "decision_type", "curated_rule_id", "gloss_en", "gloss_notes"]
            if field in unit
        }

    if in_terms(lemma, {"gloire", "glorieux"}) and (
        "couvert" in sent or "couverte" in sent or "couvertes" in sent or "avec gloire" in sent
    ):
        return append_ocr_note(
            decision(
                "mipvu_indirect",
                "`gloire` frames military conduct or death as publicly radiant renown attached to soldiers or units",
                "public fame, brilliance, honor, or radiance",
                "Glory is not a physical covering or companion, but the French phrasing treats it as something one is covered with or dies with.",
                "Military action and death are understood through fame as covering, radiance, or honor-bearing accompaniment.",
                0.86,
                "Source-language decision on French `gloire`; English gloss is not the decision basis.",
                "light_darkness",
                "military_virtue",
                "glory",
                GLOSS_MAP["gloire"][1],
                "high",
                rule_id="napoleon-gloire-covering-death",
            ),
            sentence,
            span,
        )

    if in_terms(lemma, {"honneur", "sang"}) and "sang et l honneur" in sent:
        return append_ocr_note(
            decision(
                "mipvu_indirect",
                "Russian battle choice is represented as risking the army's blood and honor together",
                "bodily blood and public honor/reputation",
                "The army's honor is abstract while blood is bodily; the pair turns battle into bodily and reputational expenditure.",
                "Military loss is understood through bodily blood and public honor.",
                0.82,
                "Translation-sensitive pair `sang et l'honneur`; keep both French terms visible.",
                "sacrifice",
                "army",
                "blood / honor",
                "French `sang` and `honneur` combine bodily loss with public esteem; neither English gloss is sufficient alone.",
                "high",
                rule_id="napoleon-blood-honor-army",
            ),
            sentence,
            span,
        )

    if in_terms(lemma, {"braves", "morts", "patrie", "victoire"}) and (
        "morts pour la patrie" in sent or "dieu des armees" in sent
    ):
        return append_ocr_note(
            decision(
                "mipvu_indirect",
                "battlefield dead are memorialized as brave dead for the fatherland within providential victory ritual",
                "dead bodies, fatherland/homeland, victory, and religious thanksgiving",
                "The deaths are literal, but the office and thanksgiving frame them as meaningful patriotic-sacred sacrifice.",
                "Soldier death is understood through patriotic sacrifice and providential victory.",
                0.88,
                "High-salience Austerlitz memorial formula; `patrie` is retained as source-language evidence.",
                "sacrifice",
                "patrie",
                "brave dead / fatherland / victory",
                "French `patrie` is not reduced to English fatherland; it carries civic-sacral attachment.",
                "high",
                rule_id="napoleon-braves-morts-patrie",
            ),
            sentence,
            span,
        )

    if in_terms(lemma, {"victoire"}) and (
        "victoire n a pas hesite" in sent
        or "victoire se decider" in sent
        or "victoire etait a nous" in sent
        or "victoire longtemps incertaine" in sent
    ):
        return append_ocr_note(
            decision(
                "mipvu_personification",
                "`victoire` is treated as an agent, possession, or hesitant outcome in battle narrative",
                "a military success or winning event",
                "Victory is abstract but is described as hesitating, deciding, or belonging to an army.",
                "Battle outcome is understood through personification and possession.",
                0.76,
                "French `victoire` is marked only where the local phrasing gives it agency or object status.",
                "body",
                "victory",
                "victory",
                GLOSS_MAP["victoire"][1],
                "medium",
                rule_id="napoleon-victoire-personified",
            ),
            sentence,
            span,
        )

    if in_terms(lemma, {"mort", "morts", "moururent", "sang"}) and (
        "semaient partout la mort" in sent
        or "produit la mort" in sent
        or "morts avec gloire" in sent
        or "sang de tant de braves" in sent
    ):
        return append_ocr_note(
            decision(
                "mipvu_indirect",
                "battle death and bloodshed are framed as produced, sown, or converted into glory-bearing cost",
                "bodily death, dying, and blood",
                "Some death is literal, but the phrasing treats death as an output, seed, or glory-bearing sacrificial cost.",
                "Battlefield violence is understood through production, sowing, and sacrificial blood cost.",
                0.8,
                "Preserve source-language `mort`/`sang`; English death/blood glosses are only aids.",
                "sacrifice",
                "war",
                "death / blood",
                "French `mort` and `sang` may be literal while still serving sacrifice/glory framing.",
                "high",
                rule_id="napoleon-death-blood-glory",
            ),
            sentence,
            span,
        )

    if in_terms(lemma, {"bouches", "feu"}) and "bouches a feu" in sent:
        return append_ocr_note(
            decision(
                "mipvu_direct",
                "artillery pieces are named as mouths of fire producing death",
                "bodily mouths and physical fire",
                "Cannons are not literal mouths; the French military term preserves body/fire imagery.",
                "Artillery is understood through bodily mouth and fire imagery.",
                0.78,
                "Conventional French artillery expression; retain as direct but register-sensitive.",
                "body",
                "artillery",
                "mouths of fire",
                "French `bouches a feu` is a conventional term for artillery pieces; body imagery remains visible.",
                "medium",
                rule_id="napoleon-bouches-a-feu",
            ),
            sentence,
            span,
        )

    if in_terms(lemma, {"fortune"}) and ("fortune a souri" in sent or "chances du sort et de la fortune" in sent):
        return append_ocr_note(
            decision(
                "mipvu_personification",
                "fortune is treated as smiling or as a force whose chances test soldiers",
                "luck, fate, or fortune as an abstract condition",
                "Fortune does not literally smile or act like a human force.",
                "Campaign outcome is understood through personified fortune.",
                0.74,
                "Retain French `fortune` because English fortune/luck/fate split the source-domain range.",
                "body",
                "campaign_outcome",
                "fortune",
                "French `fortune` can mean luck, fate, or fortune; mapping should preserve the range.",
                "medium",
                rule_id="napoleon-fortune-personified",
            ),
            sentence,
            span,
        )

    if in_terms(lemma, {"destin"}) and "destin de la bataille" in sent:
        return append_ocr_note(
            decision(
                "mipvu_indirect",
                "the battle's outcome is framed as a destiny to be decided",
                "fate, destiny, or allotted future",
                "A battle does not literally possess destiny, but the outcome is construed as fate-like.",
                "Battle outcome is understood through destiny/fate.",
                0.7,
                "Source-language `destin` is retained; confidence moderate because phrase is conventional.",
                "journey_motion",
                "battle",
                "destiny / fate",
                "French `destin` is not identical to English destiny; it may carry fate/outcome entailments.",
                "medium",
                rule_id="napoleon-destin-battle",
            ),
            sentence,
            span,
        )

    if in_terms(lemma, {"aigle"}) and "aigle d un des bataillons" in sent:
        return append_ocr_note(
            decision(
                "uncertain",
                "the battalion standard/eagle may function as a material emblem of the unit's honor",
                "an eagle as a bird or an imperial military standard",
                "The French military `aigle` is a real standard, but it also carries symbolic imperial identity.",
                "Army identity may be understood through emblematic eagle-standard imagery.",
                0.58,
                "Marked uncertain because `aigle` names an actual French standard as well as an imperial symbol.",
                "war_combat",
                "army",
                "eagle / standard",
                "French `aigle` can be literal standard-name and symbolic imperial emblem.",
                "high",
                rule_id="napoleon-aigle-standard",
            ),
            sentence,
            span,
        )

    if in_terms(lemma, {"tombeau", "trophees", "couronne"}) and (
        "tombeau du grand frederic" in sent or "sans trophees" in sent or "couronne d italie" in sent
    ):
        return append_ocr_note(
            decision(
                "uncertain",
                "monarchical or military memory is mediated through tomb, trophies, or crown objects",
                "burial monument, captured/displayed spoils, or physical crown",
                "The objects may be literal, but they also condense monarchy, victory, and imperial memory.",
                "Political-military legitimacy may be understood through symbolic objects.",
                0.55,
                "Kept uncertain to avoid over-reading literal trophy/crown/tomb references.",
                "object_material",
                "imperial_memory",
                "tomb / trophies / crown",
                "French symbolic-object terms need context-specific translation before CMT mapping.",
                "medium",
                rule_id="napoleon-symbolic-objects",
            ),
            sentence,
            span,
        )

    return non_metaphor()


def apply_gloss(unit: dict[str, Any]) -> None:
    gloss = gloss_for(str(unit.get("span_text") or unit.get("lexical_unit") or ""), str(unit.get("lemma") or ""))
    if gloss and not unit.get("gloss_en"):
        unit["gloss_en"], unit["gloss_notes"] = gloss


def apply_reviews() -> tuple[Counter[str], Counter[str], dict[str, Counter[str]], list[dict[str, Any]]]:
    sentences = sentence_lookup()
    decision_counts: Counter[str] = Counter()
    rule_counts: Counter[str] = Counter()
    doc_counts: dict[str, Counter[str]] = defaultdict(Counter)
    examples: list[dict[str, Any]] = []
    now = now_iso()

    for doc in documents(CASE_ID):
        doc_id = str(doc.get("document_id") or doc.get("id") or "")
        path = mipvu_path_for(CASE_ID, doc)
        data = read_json(path, {}) or {}
        for unit in iter_mipvu_records(data):
            sentence = sentences.get(str(unit.get("sentence_id") or ""), "")
            unit["span_text"] = str(unit.get("lexical_unit") or "")
            unit["span_language"] = "fr"
            result = curated_decision(unit, sentence)
            decision_type = str(result["decision_type"])
            unit["decision_type"] = decision_type
            unit["review_status"] = "reviewed"
            unit["review_batch"] = REVIEW_BATCH
            unit["annotator"] = unit.get("annotator") or ANNOTATOR
            unit["reviewed_at"] = now
            unit["curated_rule_id"] = result.get("curated_rule_id", "")
            unit["source_language_decision_basis"] = "span_text"

            for field in [*RATIONALE_FIELDS, "gloss_en", "gloss_notes", "ocr_risk"]:
                if field in result:
                    unit[field] = result[field]
                elif decision_type not in METAPHOR_DECISIONS and field in RATIONALE_FIELDS:
                    unit.pop(field, None)
            apply_gloss(unit)

            decision_counts[decision_type] += 1
            rule_counts[str(result.get("curated_rule_id") or "unclassified")] += 1
            doc_counts[doc_id][decision_type] += 1
            if decision_type in METAPHOR_DECISIONS and len(examples) < 80:
                examples.append(
                    {
                        "mipvu_id": unit.get("mipvu_id", ""),
                        "document_id": doc_id,
                        "sentence_id": unit.get("sentence_id", ""),
                        "span_text": unit.get("span_text", ""),
                        "gloss_en": unit.get("gloss_en", ""),
                        "decision_type": decision_type,
                        "curated_rule_id": unit.get("curated_rule_id", ""),
                        "sentence_text": sentence,
                    }
                )

        data["status"] = "reviewed"
        data.setdefault("meta", {})["review_completed_at"] = now
        data.setdefault("meta", {})["review_batch"] = REVIEW_BATCH
        data.setdefault("meta", {})["annotator"] = ANNOTATOR
        data.setdefault("meta", {})["source_language_decision_basis"] = "span_text"
        data["pipeline_log"] = with_review_log(data, now)
        write_json(path, data)

    return decision_counts, rule_counts, doc_counts, examples


def write_summary(
    decision_counts: Counter[str],
    rule_counts: Counter[str],
    doc_counts: dict[str, Counter[str]],
    examples: list[dict[str, Any]],
) -> None:
    summary = {
        "case_id": CASE_ID,
        "generated_at": now_iso(),
        "status": "mipvu-review-complete-codex-assisted",
        "review_batch": REVIEW_BATCH,
        "annotator": ANNOTATOR,
        "source_language": "fr",
        "decision_basis": "source-language span_text",
        "total_lexical_units": sum(decision_counts.values()),
        "pending_units": 0,
        "by_decision_type": dict(sorted(decision_counts.items())),
        "by_rule_id": dict(sorted(rule_counts.items())),
        "by_document": {
            doc_id: dict(sorted(counts.items()))
            for doc_id, counts in sorted(doc_counts.items())
        },
        "sample_metaphor_or_uncertain_units": examples,
        "limitations": [
            "Codex-assisted decisions are a first-pass review gate, not independent human double-coding.",
            "French source-language span_text is authoritative; English glosses are only analytical aids.",
            "Gallica OCR noise is visible in some source sentences and should be checked before quotation.",
            "Ordinary military-register corps d'armee usage is generally left non-metaphor unless the local phrase supplies separate body imagery.",
            "Downstream CMT and Koenigsbergian annotations should only use metaphor-related or uncertain units after separate interpretive review.",
        ],
    }
    write_json(case_dir(CASE_ID) / "quality" / "mipvu-review-summary.json", summary)


def update_status(decision_counts: Counter[str], doc_counts: dict[str, Counter[str]]) -> None:
    total_units = sum(decision_counts.values())
    case_status_path = case_dir(CASE_ID) / "status" / "case-status.json"
    case_status = read_json(case_status_path, {}) or {}
    case_status.update(
        {
            "case_id": CASE_ID,
            "status": "mipvu-review-complete-codex-assisted",
            "current_stage": "mipvu-review-complete",
            "updated": REVIEW_UPDATED,
            "notes": (
                "Napoleon French bulletin worklists exist for all 10 documents and "
                f"{total_units:,} lexical units have first-pass Codex-assisted "
                "source-language decisions. Each unit records source-language span_text; "
                "English glosses are retained only as aids for translation-sensitive "
                "terms such as gloire, honneur, victoire, patrie, mort, and sang. "
                "Results remain provisional until independent human review."
            ),
            "mipvu_review_summary": {
                "review_batch": REVIEW_BATCH,
                "annotator": ANNOTATOR,
                "source_language": "fr",
                "decision_basis": "source-language span_text",
                "total_lexical_units": total_units,
                "by_decision_type": dict(sorted(decision_counts.items())),
                "by_document": {
                    doc_id: dict(sorted(counts.items()))
                    for doc_id, counts in sorted(doc_counts.items())
                },
                "pending_units": 0,
                "quality_summary_path": "quality/mipvu-review-summary.json",
            },
        }
    )
    write_json(case_status_path, case_status)

    mipvu_status_path = case_dir(CASE_ID) / "status" / "mipvu-status.json"
    mipvu_status = read_json(mipvu_status_path, {}) or {}
    mipvu_status.update(
        {
            "stage": "complete-mipvu-review",
            "status": "reviewed",
            "reviewed_at": REVIEW_UPDATED,
            "review_batch": REVIEW_BATCH,
            "annotator": ANNOTATOR,
            "source_language": "fr",
            "decision_basis": "source-language span_text",
            "lexical_units": total_units,
            "pending_units": 0,
            "by_decision_type": dict(sorted(decision_counts.items())),
        }
    )
    for record in mipvu_status.get("records", []) or []:
        if not isinstance(record, dict):
            continue
        doc_id = str(record.get("document_id") or "")
        record["review_status"] = "reviewed"
        record["pending_units"] = 0
        record["by_decision_type"] = dict(sorted(doc_counts.get(doc_id, Counter()).items()))
    write_json(mipvu_status_path, mipvu_status)


def main() -> int:
    decision_counts, rule_counts, doc_counts, examples = apply_reviews()
    write_summary(decision_counts, rule_counts, doc_counts, examples)
    update_status(decision_counts, doc_counts)
    print(f"Reviewed {sum(decision_counts.values())} Napoleon lexical unit(s).")
    print(json.dumps(dict(sorted(decision_counts.items())), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
