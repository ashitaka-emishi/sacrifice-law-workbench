#!/usr/bin/env python3
"""Complete the American Revolution MIPVU review gate.

The American Revolution v1 corpus is large enough that the auditable artifact is
the reviewed worklist itself. This script applies conservative, case-local
first-pass decisions for high-salience republican, providential, body-politic,
bondage, and sacrifice language, then marks the remaining lexical units as
reviewed non-metaphors.
"""
from __future__ import annotations

import json
import re
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

CASE_ID = "am-rev"
ANNOTATOR = "codex-assisted-mipvu-v1"
REVIEW_BATCH = "am-rev-full-corpus-mipvu-review-v1"
REVIEW_UPDATED = "2026-06-28"

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


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def sentence_lookup() -> dict[str, str]:
    sentences: dict[str, str] = {}
    for doc in documents(CASE_ID):
        data = read_json(segmented_path_for(CASE_ID, doc), {}) or {}
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
    risk: str = "medium",
    source: str = "Webster 1828",
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
        "curated_rule_id": rule_id,
    }


def non_metaphor() -> dict[str, Any]:
    return {"decision_type": "non_metaphor", "curated_rule_id": "default-reviewed-non-metaphor"}


def in_terms(lemma: str, terms: set[str]) -> bool:
    return lemma in {norm(term) for term in terms}


def with_review_log(data: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    existing = data.get("pipeline_log", [])
    logs = [item for item in existing if isinstance(item, dict)]
    logs = [item for item in logs if item.get("stage") != "complete-am-rev-mipvu-review"]
    logs.append(
        {
            "stage": "complete-am-rev-mipvu-review",
            "script": "scripts/complete-am-rev-mipvu-review.py",
            "generated_at": generated_at,
        }
    )
    return logs


def curated_decision(unit: dict[str, Any], sentence: str) -> dict[str, Any]:
    lemma = norm(str(unit.get("lemma") or unit.get("lexical_unit") or ""))
    word = norm(str(unit.get("lexical_unit") or ""))
    sent = norm(sentence)
    doc_id = str(unit.get("document_id") or "")

    if (
        unit.get("review_status") != "pending"
        and unit.get("decision_type")
        and unit.get("review_batch") != REVIEW_BATCH
    ):
        return {
            field: unit[field]
            for field in [*RATIONALE_FIELDS, "decision_type", "curated_rule_id"]
            if field in unit
        }

    if doc_id == "am-rev-jefferson-declaration" and in_terms(
        lemma, {"bands", "connected", "dissolve"}
    ) and "political bands" in sent:
        return decision(
            "mipvu_indirect",
            "political connection with Britain is represented as a binding tie that can be dissolved",
            "physical bands bind objects or bodies; dissolving separates material cohesion",
            "The relation among peoples and states is political, not a literal band or substance.",
            "Political association is understood through material bonds and dissolution.",
            0.88,
            "Declaration opening frames separation as the dissolution of political bands.",
            "object_material",
            "political_relation",
            "high",
            'Webster 1828, "band" / "dissolve"',
            "declaration-political-bands",
        )

    if doc_id == "am-rev-jefferson-declaration" and in_terms(
        lemma, {"train", "reduce", "under", "throw", "guards"}
    ) and ("long train of abuses" in sent or "throw off such government" in sent):
        return decision(
            "mipvu_indirect",
            "abuses, despotism, and constitutional remedy are represented through procession, subjection, casting off, and guards",
            "a train follows in sequence; bodies are placed under burdens; guards physically protect",
            "Political oppression and institutional remedies are abstract but are framed through physical subjection and protection.",
            "Political danger and security are understood through bodily burden, motion, and defense.",
            0.76,
            "Republican grievance language is conventional but locally central to tyranny/security framing.",
            "body",
            "political_security",
            "medium",
            'Webster 1828, "train" / "guard"',
            "declaration-tyranny-security",
        )

    if doc_id == "am-rev-jefferson-declaration" and in_terms(
        lemma, {"injuries", "invasions", "annihilation", "exposed"}
    ):
        return decision(
            "mipvu_indirect",
            "states, powers, and rights are represented as bodies or material entities that can be injured, invaded, annihilated, or exposed",
            "bodily injury, physical invasion, destruction, or exposure to danger",
            "Legal-political entities do not literally suffer bodily injury or exposure.",
            "Political rights and institutions are understood through bodily vulnerability.",
            0.72,
            "Declaration grievance terms are period legal-political idioms; keep confidence moderate.",
            "body",
            "rights",
            "medium",
            f'Webster 1828, "{lemma or word}"',
            "declaration-injury-rights",
        )

    if doc_id == "am-rev-jefferson-declaration" and in_terms(
        lemma, {"death", "desolation", "tyranny", "head", "executioners"}
    ) and ("works of death" in sent or "head of a civilized nation" in sent):
        return decision(
            "mipvu_direct" if lemma in {"works", "head"} else "mipvu_indirect",
            "royal violence is framed as a work of death and the nation as a civilized body with a head",
            "physical works, bodily death/desolation, execution, and a bodily head",
            "Military and political actions are represented through bodily death-work and national embodiment.",
            "Enemy violence is understood through death-bearing agency and body-politic hierarchy.",
            0.86 if lemma in {"death", "head"} else 0.74,
            "High-salience enemy-as-bringer-of-death evidence in the Declaration.",
            "body",
            "enemy_as_bringer_of_death",
            "high",
            'Webster 1828, "death" / "head"',
            "declaration-works-of-death",
        )

    if doc_id == "am-rev-jefferson-declaration" and in_terms(
        lemma, {"divine", "providence", "pledge", "lives", "fortunes", "sacred", "honor"}
    ):
        return decision(
            "uncertain" if lemma in {"divine", "providence"} else "mipvu_indirect",
            "collective commitment is framed through sacred honor, providential protection, and pledged lives and fortunes",
            "religious providence, sacredness, physical life, property, and pledged surety",
            "The pledge is a real political act, but the closing formula gives it sacred and sacrificial force.",
            "Revolutionary commitment is understood through sacred obligation and sacrificial stake.",
            0.68 if lemma in {"divine", "providence"} else 0.82,
            "Preserve uncertainty for theological idiom while retaining pledge/sacred-honor evidence.",
            "religion_providence",
            "founding_sacrifice",
            "high",
            'Webster 1828, "pledge" / "sacred" / "providence"',
            "declaration-sacred-pledge",
        )

    if doc_id == "am-rev-paine-common-sense" and in_terms(
        lemma, {"fire", "sword", "face", "earth", "nature"}
    ) and "fire and sword" in sent:
        return decision(
            "mipvu_indirect",
            "imperial war is represented through fire, sword, extirpation, and the face of the earth",
            "burning fire, bladed weapons, uprooting, and a body's or surface's face",
            "The war is literal, but the phrase condenses political destruction into conventional elemental and bodily imagery.",
            "Enemy violence is understood through destructive element, weapon, and earth-body imagery.",
            0.76,
            "Paine's opening universalizes American suffering through death-bearing war imagery.",
            "war_combat",
            "enemy_as_bringer_of_death",
            "medium",
            'Webster 1828, "fire" / "sword" / "face"',
            "paine-fire-sword",
        )

    if doc_id == "am-rev-paine-common-sense" and in_terms(
        lemma, {"disease", "misfortune", "death", "perish", "die"}
    ) and "disease" in sent and "misfortune" in sent:
        return decision(
            "mipvu_direct",
            "isolated natural life is compared to sickness, misfortune, death, and perishing",
            "bodily disease, death, and perishing",
            "Paine uses physical mortality to explain the social necessity of cooperation.",
            "Social vulnerability is understood through bodily illness and death.",
            0.88,
            "Explicit explanatory analogy in Paine's account of society's origin.",
            "body",
            "society",
            "medium",
            'Webster 1828, "disease" / "death"',
            "paine-disease-death",
        )

    if doc_id == "am-rev-paine-common-sense" and in_terms(
        lemma, {"gravitating", "power", "form", "impregnable", "vice"}
    ) and ("gravitating power" in sent or "impregnable to vice" in sent):
        return decision(
            "mipvu_direct",
            "necessity forms society like physical gravity, while heaven is imagined as a fortress against vice",
            "gravitational force, shaping material form, and a fortified place that cannot be taken",
            "Social formation and moral purity are abstract but are explained through physical force and fortification.",
            "Society and virtue are understood through physical force and defense.",
            0.84,
            "Paine uses natural-force and fortress imagery to move from society to government.",
            "mechanics",
            "society",
            "medium",
            'Webster 1828, "gravitate" / "impregnable"',
            "paine-gravity-fortress",
        )

    if doc_id == "am-rev-paine-common-sense" and in_terms(
        lemma, {"body", "head", "springs", "remedy", "disordered", "repaired", "materials"}
    ):
        if any(phrase in sent for phrase in ["whole body", "head from which", "disordered", "repaired", "materials"]):
            return decision(
                "mipvu_personification" if lemma in {"body", "head"} else "mipvu_indirect",
                "government or the people are construed as a body, mechanism, or material structure",
                "a living body or head; a damaged mechanism or material that can be repaired",
                "Political collectives and constitutions are abstract institutions, not literal bodies or machines.",
                "Collective political order is understood through bodies, repair, and materials.",
                0.78,
                "Track as republican body/mechanism language without forcing later Lincoln clusters onto Paine.",
                "body",
                "government",
                "medium",
                f'Webster 1828, "{lemma or word}"',
                "paine-body-government",
            )

    if doc_id == "am-rev-paine-common-sense" and in_terms(
        lemma, {"eyes", "dazzled", "ears", "deceived", "warp", "darken", "voice", "nature", "reason"}
    ) and ("voice of nature" in sent or "darken our understanding" in sent):
        return decision(
            "mipvu_personification" if lemma in {"voice", "nature", "reason"} else "mipvu_indirect",
            "judgment and reason are represented through sight, hearing, darkness, voice, and agency",
            "bodily eyes, ears, darkness, warping, and speaking voices",
            "Abstract faculties are treated as embodied perceivers or speakers.",
            "Political judgment is understood through bodily perception and personified reason.",
            0.8,
            "Important genre marker for Paine's rationalist political rhetoric.",
            "body",
            "reason",
            "medium",
            'Webster 1828, "voice" / "darken"',
            "paine-voice-reason",
        )

    if doc_id == "am-rev-paine-common-sense" and in_terms(
        lemma, {"sacred", "majesty", "worm", "crumbling", "dust", "idolatrous", "homage", "heaven"}
    ):
        if "sacred majesty" in sent or "idolatrous homage" in sent or "king of heaven" in sent:
            return decision(
                "mipvu_direct" if lemma in {"worm", "crumbling", "dust"} else "mipvu_indirect",
                "monarchy is attacked through sacred parody, idolatry, bodily decay, and heavenly sovereignty",
                "religious worship, worms, crumbling matter, dust, and divine rule",
                "Royal authority is political, but Paine frames it through religious transgression and bodily mortality.",
                "Monarchical power is understood through false worship and mortal body imagery.",
                0.86,
                "Do not count as sacred-object support for monarchy; Paine uses sacred language polemically.",
                "religion_providence",
                "monarchy",
                "high",
                'Webster 1828, "sacred" / "worm" / "homage"',
                "paine-anti-monarchy-sacred-parody",
            )

    if doc_id == "am-rev-paine-common-sense" and in_terms(
        lemma, {"parent", "mother", "infant", "birth", "birthday", "world", "brought", "forth", "production"}
    ):
        if any(
            phrase in sent
            for phrase in [
                "parent country",
                "mother country",
                "infant state",
                "birth day",
                "birthday",
                "new world",
                "birth of this production",
                "brought it forth",
            ]
        ):
            return decision(
                "mipvu_direct",
                "colonial relation, independence, and founding are represented through parenthood, infancy, birth, and a new world",
                "family relations and bodily birth",
                "Political colonies, pamphlets, and founding moments are not literal parents, infants, worlds, or births.",
                "Revolutionary founding is understood through kinship and birth-generation.",
                0.88,
                "Paine repeatedly contests parent-country language while using birth/new-world imagery.",
                "birth_generation",
                "independence",
                "medium",
                'Webster 1828, "parent" / "birth"',
                "paine-parent-birth",
            )

    if doc_id == "am-rev-paine-common-sense" and in_terms(
        lemma, {"chain", "chains", "slave", "slaves", "slavery", "slavish", "bondage", "enslave", "enslaved", "yoke", "shackle", "shackles"}
    ):
        return decision(
            "mipvu_indirect",
            "imperial dependence or political subjection is framed as slavery, slavishness, chains, bondage, yoke, or shackles",
            "physical captivity, forced labor, restraining metal links, or animal yokes",
            "Paine applies coercive bodily restraint vocabulary to constitutional and imperial dependence.",
            "Political oppression is understood through captivity and bodily restraint.",
            0.84,
            "High-salience liberty/tyranny vocabulary; preserve historical slavery-language caution.",
            "slavery_bondage",
            "liberty",
            "high",
            'Webster 1828, "slavery" / "chain" / "yoke"',
            "paine-bondage-liberty",
        )

    if doc_id == "am-rev-paine-common-sense" and in_terms(
        lemma, {"seed", "seedtime", "root", "plant", "ripen", "harvest"}
    ):
        return decision(
            "mipvu_indirect",
            "union, independence, or political change is represented through planting, roots, growth, ripening, and harvest",
            "planting seed, growing trees or branches, and harvesting crops",
            "Political development is abstract but is construed as organic growth.",
            "Founding and union are understood through agriculture and growth.",
            0.82,
            "Useful for founding-memory and union-development clusters.",
            "agriculture",
            "union",
            "medium",
            'Webster 1828, "seed" / "root" / "harvest"',
            "paine-growth-union",
        )

    if doc_id == "am-rev-paine-common-sense" and in_terms(
        lemma, {"blood", "slain", "martyr", "martyrs", "sacrifice", "sacrifices", "sacrificed", "altar", "wound", "wounds", "offering"}
    ):
        return decision(
            "mipvu_indirect",
            "revolutionary suffering is framed through blood, slain bodies, martyrs, sacrifice, altars, or wounds",
            "bodily blood and wounds; religious martyrdom, altar, or sacrificial offering",
            "Some war deaths are literal, but Paine's rhetoric gives them sacrificial political meaning.",
            "Revolutionary commitment is understood through sacrifice and bodily injury.",
            0.84,
            "High-salience founding-sacrifice evidence; keep distinct from later CMT interpretation.",
            "sacrifice",
            "independence",
            "high",
            'Webster 1828, "blood" / "martyr" / "sacrifice"',
            "paine-blood-sacrifice",
        )

    if doc_id.startswith("am-rev-washington-orders") and in_terms(
        lemma, {"body", "head", "sinews"}
    ):
        if "body of forces" in sent or "head of a powerful body" in sent or "sinews of independence" in sent:
            return decision(
                "uncertain",
                "military force or independence is represented through body, head, or sinews language",
                "an animal or human body, its head, and connective sinews",
                "Military-register uses may be conventional unit labels, but they also preserve body-politic or force-body imagery.",
                "Military organization may be understood through bodily organization.",
                0.56,
                "Washington-document register caution: retain as uncertain rather than force a Lincoln-style body-politic reading.",
                "body",
                "army",
                "medium",
                'Webster 1828, "body" / "sinew"',
                "washington-military-body-register",
            )

    if doc_id.startswith("am-rev-washington-orders") and in_terms(
        lemma, {"glorious", "glory", "honor", "spirit", "spirited"}
    ):
        if "glorious" in sent or "highest honor" in sent or "spirited behaviour" in sent:
            return decision(
                "uncertain",
                "military conduct is evaluated through glory, honor, or spirit language",
                "radiance/fame, public esteem, or animating breath/spirit",
                "The terms may be conventional military praise, but the source-domain contrast remains plausible in this register.",
                "Military virtue is understood through honor, animation, and public radiance.",
                0.55,
                "Register-sensitive Washington decision: preserve uncertainty for later human review.",
                "light_darkness",
                "military_virtue",
                "medium",
                'Webster 1828, "glory" / "spirit"',
                "washington-honor-register",
            )

    return non_metaphor()


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
            result = curated_decision(unit, sentence)
            decision_type = str(result["decision_type"])
            unit["decision_type"] = decision_type
            unit["review_status"] = "reviewed"
            unit["review_batch"] = REVIEW_BATCH
            unit["annotator"] = unit.get("annotator") or ANNOTATOR
            unit["reviewed_at"] = now
            unit["curated_rule_id"] = result.get("curated_rule_id", "")

            for field in RATIONALE_FIELDS:
                if field in result:
                    unit[field] = result[field]
                elif decision_type not in METAPHOR_DECISIONS:
                    unit.pop(field, None)

            decision_counts[decision_type] += 1
            rule_counts[str(result.get("curated_rule_id") or "unclassified")] += 1
            doc_counts[doc_id][decision_type] += 1
            if decision_type in METAPHOR_DECISIONS and len(examples) < 60:
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
        data.setdefault("meta", {})["review_batch"] = REVIEW_BATCH
        data.setdefault("meta", {})["annotator"] = ANNOTATOR
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
            "Washington military-register body/honor terms are usually marked uncertain where source-domain contrast may be conventional.",
            "Downstream CMT and Koenigsbergian annotations should only use metaphor-related or uncertain units after separate interpretive review.",
        ],
    }
    write_json(case_dir(CASE_ID) / "quality" / "mipvu-review-summary.json", summary)


def update_status(decision_counts: Counter[str], doc_counts: dict[str, Counter[str]]) -> None:
    total_units = sum(decision_counts.values())
    document_count = len(doc_counts)
    case_status_path = case_dir(CASE_ID) / "status" / "case-status.json"
    case_status = read_json(case_status_path, {}) or {}
    case_status.update(
        {
            "case_id": CASE_ID,
            "status": "mipvu-review-complete-codex-assisted",
            "current_stage": "mipvu-review-complete",
            "updated": REVIEW_UPDATED,
            "notes": (
                "American Revolution expanded corpus has generated MIPVU worklists "
                f"for all {document_count} documents and {total_units:,} lexical units "
                "have first-pass "
                "Codex-assisted decisions. Genre/register differences are preserved "
                "through conservative uncertain decisions for contested Washington "
                "military-register body and honor language. Results remain provisional "
                "until independent human review."
            ),
            "mipvu_review_summary": {
                "review_batch": REVIEW_BATCH,
                "annotator": ANNOTATOR,
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
    print(f"Reviewed {sum(decision_counts.values())} American Revolution lexical unit(s).")
    print(json.dumps(dict(sorted(decision_counts.items())), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
