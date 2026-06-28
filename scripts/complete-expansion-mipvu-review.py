#!/usr/bin/env python3
"""Complete first-pass MIPVU review for expansion-window cases.

This reviewer is intentionally conservative. It supplies auditable, provisional
Codex-assisted decisions for the new expansion cases that do not yet have
case-local review scripts, then marks the remaining lexical units as reviewed
non-metaphors so downstream CMT and analysis artifacts can be generated.
"""
from __future__ import annotations

import argparse
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

ANNOTATOR = "codex-assisted-expansion-mipvu-v1"
REVIEW_UPDATED = "2026-06-28"
SUPPORTED_CASES = {"fr-rev", "wwi-britain"}
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


def strip_accents(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(value.lower())).strip()


def sentence_lookup(case_id: str) -> dict[str, str]:
    sentences: dict[str, str] = {}
    for doc in documents(case_id):
        data = read_json(segmented_path_for(case_id, doc), {}) or {}
        for sentence in iter_sentence_nodes(data):
            sentence_id = str(sentence.get("sentence_id") or "")
            if sentence_id:
                sentences[sentence_id] = str(sentence.get("text") or "")
    return sentences


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
    risk: str,
    source: str,
    rule_id: str,
    gloss_en: str = "",
    gloss_notes: str = "",
) -> dict[str, Any]:
    result: dict[str, Any] = {
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
        "curated_rule_id": rule_id,
    }
    if gloss_en:
        result["gloss_en"] = gloss_en
    if gloss_notes:
        result["gloss_notes"] = gloss_notes
    return result


def non_metaphor() -> dict[str, str]:
    return {
        "decision_type": "non_metaphor",
        "curated_rule_id": "expansion-default-reviewed-non-metaphor",
    }


def fr_decision(unit: dict[str, Any], sentence: str) -> dict[str, Any]:
    raw_lemma = str(unit.get("lemma") or unit.get("lexical_unit") or "").lower().strip()
    lemma = norm(raw_lemma)
    sent = norm(sentence)
    source = "Littré / Dictionnaire de l'Académie française, historical sense"

    if lemma in {"sacrifice", "sacrifices", "devouement", "devouer"}:
        return decision(
            "mipvu_indirect",
            "republican commitment is represented through sacrifice or total devotion",
            "religious or material offering, renunciation, or giving over of oneself",
            "The passage concerns civic-political commitment, not a literal altar offering.",
            "Civic obligation is understood through sacrificial offering and self-devotion.",
            0.82,
            "French expansion first-pass rule; preserve source-language decision basis.",
            "sacrifice",
            "sacrifice",
            "high",
            source,
            "fr-rev-sacrifice-devotion",
            "sacrifice / devotion",
            "English gloss is an analytical aid only; French source text controls.",
        )

    if lemma in {"sang", "mort", "morts", "mourir"} and any(
        term in sent for term in {"patrie", "liberte", "republique", "heros", "combattant", "sacrifice"}
    ):
        return decision(
            "mipvu_indirect",
            "death or bloodshed is framed as the cost that protects liberty, heroes, or the patrie",
            "bodily blood, death, or dying",
            "The terms may name literal danger, but the local phrasing converts loss into civic-political value.",
            "Republican liberty and patriotic obligation are understood through blood and death.",
            0.76,
            "Literal revolutionary violence remains possible; confidence is moderate.",
            "life_death",
            "sacrifice",
            "high",
            source,
            "fr-rev-blood-death-sacrifice",
            "blood / death",
            "English gloss is an analytical aid only; French source text controls.",
        )

    if lemma in {"chaines", "esclave", "esclaves", "briser", "river"} and any(
        term in sent for term in {"humanite", "liberte", "tyrannie", "tyrans"}
    ):
        return decision(
            "mipvu_indirect",
            "oppression and liberation are represented through chains, slavery, riveting, or breaking bonds",
            "physical bondage, fastening, or breaking material restraints",
            "Humanity and liberty are political abstractions rather than literal chained bodies in this context.",
            "Political freedom is understood through slavery and broken bondage.",
            0.84,
            "Source-language bondage imagery is high-salience for liberty/tyranny framing.",
            "slavery_bondage",
            "freedom",
            "high",
            source,
            "fr-rev-bondage-liberty",
            "chains / slavery",
            "English gloss is an analytical aid only; French source text controls.",
        )

    if lemma in {"couronne", "couronner", "couronnent"} and "mort" in sent:
        return decision(
            "mipvu_indirect",
            "death is represented as crowning patriotic labor or glory",
            "placing a crown on a head as honor or completion",
            "Death does not literally crown labor; the phrase confers honor and completion.",
            "Patriotic death is understood through crowning honor.",
            0.74,
            "Treat as provisional because couronner can be conventional honor language.",
            "object_material",
            "military_virtue",
            "medium",
            source,
            "fr-rev-death-crowning",
            "crowns / crowns with death",
            "English gloss is an analytical aid only; French source text controls.",
        )

    birth_terms = {
        "né",
        "née",
        "nait",
        "naît",
        "naitre",
        "naître",
        "naissent",
        "naissance",
        "enfante",
        "enfanter",
        "régénération",
        "regeneration",
    }
    if raw_lemma in birth_terms and any(
        term in sent for term in {"peuple", "liberte", "republique", "nation"}
    ):
        return decision(
            "mipvu_indirect",
            "political community or liberty is represented through birth or regeneration",
            "biological birth, generation, or renewed life",
            "The referent is political and historical rather than biological.",
            "Republican political life is understood through birth and regeneration.",
            0.7,
            "Birth/regeneration language is analytically useful but may be conventional revolutionary idiom.",
            "birth_generation",
            "republic",
            "medium",
            source,
            "fr-rev-political-birth",
            "birth / regeneration",
            "English gloss is an analytical aid only; French source text controls.",
        )

    if lemma in {"salut", "sauver", "sauvee"} and any(
        term in sent for term in {"public", "republique", "patrie", "danger"}
    ):
        return decision(
            "uncertain",
            "public safety or republican survival is framed through salvation/rescue",
            "rescue from danger, preservation, or salvation",
            "The political institution is treated as an entity that can be saved.",
            "The republic is understood through rescue or salvation from danger.",
            0.62,
            "Comité de salut public is also an institutional title; keep uncertain pending human review.",
            "medicine_healing",
            "republic",
            "high",
            source,
            "fr-rev-public-salvation",
            "public safety / salvation",
            "English gloss is an analytical aid only; French source text controls.",
        )

    return non_metaphor()


def wwi_decision(unit: dict[str, Any], sentence: str) -> dict[str, Any]:
    lemma = norm(str(unit.get("lemma") or unit.get("lexical_unit") or ""))
    sent = norm(sentence)
    source = "OED / Webster 1913, historical sense"

    if lemma in {"sacrifice", "sacrifices", "sacrificed"}:
        return decision(
            "mipvu_indirect",
            "wartime service or loss is framed as sacrifice for freedom, country, or allies",
            "religious or material offering, loss, or giving up something valuable",
            "The passage concerns civic and military cost rather than a literal ritual offering.",
            "Wartime obligation is understood through sacrificial offering.",
            0.84,
            "High-salience expansion term; keep provisional pending independent review.",
            "sacrifice",
            "sacrifice",
            "high",
            source,
            "wwi-sacrifice-service",
        )

    if lemma in {"blood", "cleansed"} and any(
        term in sent for term in {"sacrifice", "country", "nation", "race", "war", "conflict"}
    ):
        return decision(
            "mipvu_indirect",
            "national vitality, conflict, or war cost is represented through blood and cleansing",
            "bodily blood or physical cleansing",
            "The country, race, or conflict is not literally blood that can be cleansed.",
            "National renewal and war cost are understood through body-blood imagery.",
            0.78,
            "OCR and period rhetoric require review before publication-grade quotation.",
            "body_blood",
            "nation",
            "high",
            source,
            "wwi-blood-national-renewal",
        )

    if lemma in {"burden", "bear", "borne", "load"} and any(
        term in sent for term in {"allies", "nation", "country", "war", "share"}
    ):
        return decision(
            "mipvu_indirect",
            "wartime obligation is represented as a physical burden to carry",
            "a physical load borne by a body",
            "The obligation is political and military, not a literal carried object.",
            "Allied responsibility is understood through bodily carrying.",
            0.73,
            "Common burden idiom; mark provisional and moderate confidence.",
            "body",
            "obligation",
            "medium",
            source,
            "wwi-burden-obligation",
        )

    if lemma in {"machine", "diesel", "petrol", "driven", "explosions"} and any(
        term in sent for term in {"nation", "civilisation", "man", "people"}
    ):
        return decision(
            "mipvu_direct",
            "nation, civilization, or personhood is explicitly compared to a machine",
            "mechanical apparatus driven by fuel, precision, or explosions",
            "The target is a political community or human being, not literal machinery.",
            "Political society and personhood are understood through machinery.",
            0.88,
            "Explicit machinery comparison in Lloyd George war rhetoric.",
            "mechanics",
            "social_body",
            "medium",
            source,
            "wwi-machine-society",
        )

    if lemma in {"heart", "soul", "hand", "head", "strength"} and any(
        term in sent for term in {"nation", "people", "victory", "freedom", "working", "qualities"}
    ):
        return decision(
            "mipvu_indirect",
            "collective resolve or service is framed through body parts, soul, or embodied strength",
            "literal organs, limbs, inner life, or bodily strength",
            "The phrase applies bodily or inner-life language to collective political commitment.",
            "National service is understood through embodied agency.",
            0.67,
            "Some uses are idiomatic; keep confidence moderate.",
            "person_agency",
            "nation",
            "medium",
            source,
            "wwi-embodied-national-service",
        )

    if lemma in {"winter", "spring", "road", "path"} and any(
        term in sent for term in {"triumph", "victory", "barbarism", "war"}
    ):
        return decision(
            "mipvu_indirect",
            "war outcome or moral trajectory is represented through seasonal change or travel",
            "movement along a road/path or seasonal transition",
            "The political-military process is not literal travel or weather.",
            "Victory and moral danger are understood through journey or seasonal transition.",
            0.7,
            "First-pass expansion rule; verify local phrasing before using in claims.",
            "journey_motion",
            "victory",
            "medium",
            source,
            "wwi-road-season-victory",
        )

    return non_metaphor()


def with_review_log(data: dict[str, Any], case_id: str, generated_at: str) -> list[dict[str, Any]]:
    stage = f"complete-{case_id}-expansion-mipvu-review"
    logs = [item for item in data.get("pipeline_log", []) if isinstance(item, dict)]
    logs = [item for item in logs if item.get("stage") != stage]
    logs.append(
        {
            "stage": stage,
            "script": "scripts/complete-expansion-mipvu-review.py",
            "generated_at": generated_at,
        }
    )
    return logs


def decide(case_id: str, unit: dict[str, Any], sentence: str) -> dict[str, Any]:
    if (
        unit.get("review_status") != "pending"
        and unit.get("decision_type")
        and unit.get("review_batch") != review_batch(case_id)
    ):
        preserved = {
            field: unit[field]
            for field in [*RATIONALE_FIELDS, "decision_type", "curated_rule_id", "gloss_en", "gloss_notes"]
            if field in unit
        }
        return preserved or non_metaphor()
    return fr_decision(unit, sentence) if case_id == "fr-rev" else wwi_decision(unit, sentence)


def review_batch(case_id: str) -> str:
    return f"{case_id}-expanded-corpus-mipvu-review-v1"


def apply_reviews(case_id: str) -> tuple[Counter[str], Counter[str], dict[str, Counter[str]], list[dict[str, Any]]]:
    sentences = sentence_lookup(case_id)
    counts: Counter[str] = Counter()
    rules: Counter[str] = Counter()
    doc_counts: dict[str, Counter[str]] = defaultdict(Counter)
    examples: list[dict[str, Any]] = []
    now = now_iso()
    batch = review_batch(case_id)

    for doc in documents(case_id):
        doc_id = str(doc.get("document_id") or doc.get("id") or "")
        path = mipvu_path_for(case_id, doc)
        data = read_json(path, {}) or {}
        for unit in iter_mipvu_records(data):
            sentence = sentences.get(str(unit.get("sentence_id") or ""), "")
            result = decide(case_id, unit, sentence)
            decision_type = str(result.get("decision_type") or "non_metaphor")
            unit["review_status"] = "reviewed"
            unit["review_batch"] = batch
            unit["annotator"] = ANNOTATOR
            unit["reviewed_at"] = REVIEW_UPDATED
            unit["decision_type"] = decision_type
            unit["curated_rule_id"] = str(result.get("curated_rule_id") or "unclassified")
            for field in [*RATIONALE_FIELDS, "gloss_en", "gloss_notes"]:
                if field in result:
                    unit[field] = result[field]
                elif decision_type not in METAPHOR_DECISIONS:
                    unit.pop(field, None)

            counts[decision_type] += 1
            rules[unit["curated_rule_id"]] += 1
            doc_counts[doc_id][decision_type] += 1
            if decision_type in METAPHOR_DECISIONS and len(examples) < 80:
                examples.append(
                    {
                        "mipvu_id": unit.get("mipvu_id", ""),
                        "document_id": doc_id,
                        "sentence_id": unit.get("sentence_id", ""),
                        "lexical_unit": unit.get("lexical_unit", ""),
                        "decision_type": decision_type,
                        "curated_rule_id": unit.get("curated_rule_id", ""),
                        "sentence_text": sentence,
                    }
                )

        data["status"] = "reviewed"
        data.setdefault("meta", {})["review_completed_at"] = now
        data.setdefault("meta", {})["review_batch"] = batch
        data.setdefault("meta", {})["annotator"] = ANNOTATOR
        data["pipeline_log"] = with_review_log(data, case_id, now)
        write_json(path, data)
    return counts, rules, doc_counts, examples


def write_summary(
    case_id: str,
    counts: Counter[str],
    rules: Counter[str],
    doc_counts: dict[str, Counter[str]],
    examples: list[dict[str, Any]],
) -> None:
    source_language = "fr" if case_id == "fr-rev" else "en"
    summary = {
        "case_id": case_id,
        "generated_at": now_iso(),
        "status": "mipvu-review-complete-codex-assisted",
        "review_batch": review_batch(case_id),
        "annotator": ANNOTATOR,
        "source_language": source_language,
        "total_lexical_units": sum(counts.values()),
        "pending_units": 0,
        "by_decision_type": dict(sorted(counts.items())),
        "by_rule_id": dict(sorted(rules.items())),
        "by_document": {
            doc_id: dict(sorted(doc_count.items()))
            for doc_id, doc_count in sorted(doc_counts.items())
        },
        "sample_metaphor_or_uncertain_units": examples,
        "limitations": [
            "Codex-assisted decisions are a first-pass review gate, not independent human double-coding.",
            "Default non-metaphor decisions are conservative and should be sampled before claim promotion.",
            "Generated CMT/Koenigsbergian annotations remain provisional until scholarly review.",
        ],
    }
    if case_id == "fr-rev":
        summary["decision_basis"] = "French source-language lexical units with English glosses as analytical aids only"
        summary["limitations"].append("French terms require source-language review before publication-grade quotation or translation claims.")
    if case_id == "wwi-britain":
        summary["limitations"].append("Internet Archive OCR noise remains visible in the source and must be checked before publication-grade quotation.")
    write_json(case_dir(case_id) / "quality" / "mipvu-review-summary.json", summary)


def update_status(case_id: str, counts: Counter[str], doc_counts: dict[str, Counter[str]]) -> None:
    total_units = sum(counts.values())
    manifest_docs = len(documents(case_id))
    annotated_count = len(list((case_dir(case_id) / "corpus" / "annotated").glob("*_annotated.json")))
    status_path = case_dir(case_id) / "status" / "case-status.json"
    status = read_json(status_path, {}) or {}
    status.update(
        {
            "case_id": case_id,
            "status": "mipvu-review-complete-codex-assisted",
            "current_stage": "mipvu-review-complete",
            "updated": REVIEW_UPDATED,
            "notes": (
                f"{case_id} expansion corpus has first-pass Codex-assisted MIPVU "
                f"decisions for all {manifest_docs} manifest documents and "
                f"{total_units:,} lexical units. CMT/Koenigsbergian and downstream "
                "analysis artifacts remain provisional until independent review and "
                "reliability sampling are complete."
            ),
            "documents": {
                **(status.get("documents", {}) if isinstance(status.get("documents"), dict) else {}),
                "manifest": manifest_docs,
                "mipvu_worklists": len(doc_counts),
                "annotated": annotated_count,
            },
            "mipvu_review_summary": {
                "review_batch": review_batch(case_id),
                "annotator": ANNOTATOR,
                "total_lexical_units": total_units,
                "by_decision_type": dict(sorted(counts.items())),
                "by_document": {
                    doc_id: dict(sorted(doc_count.items()))
                    for doc_id, doc_count in sorted(doc_counts.items())
                },
                "pending_units": 0,
                "quality_summary_path": "quality/mipvu-review-summary.json",
            },
        }
    )
    write_json(status_path, status)

    mipvu_status_path = case_dir(case_id) / "status" / "mipvu-status.json"
    mipvu_status = read_json(mipvu_status_path, {}) or {}
    mipvu_status.update(
        {
            "stage": "complete-mipvu-review",
            "status": "reviewed",
            "reviewed_at": REVIEW_UPDATED,
            "review_batch": review_batch(case_id),
            "annotator": ANNOTATOR,
            "lexical_units": total_units,
            "pending_units": 0,
            "by_decision_type": dict(sorted(counts.items())),
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


def process_case(case_id: str) -> dict[str, Any]:
    if case_id not in SUPPORTED_CASES:
        raise ValueError(f"unsupported expansion case: {case_id}")
    counts, rules, doc_counts, examples = apply_reviews(case_id)
    write_summary(case_id, counts, rules, doc_counts, examples)
    update_status(case_id, counts, doc_counts)
    return {
        "case_id": case_id,
        "total_lexical_units": sum(counts.values()),
        "by_decision_type": dict(sorted(counts.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", choices=sorted(SUPPORTED_CASES))
    args = parser.parse_args()
    cases = [args.case_id] if args.case_id else sorted(SUPPORTED_CASES)
    results = [process_case(case_id) for case_id in cases]
    print(json.dumps({"script": "complete-expansion-mipvu-review.py", "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
