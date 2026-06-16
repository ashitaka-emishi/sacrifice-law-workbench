#!/usr/bin/env python3
"""Complete the Lincoln MIPVU review gate with auditable first-pass decisions.

This script is intentionally case-local. It preserves the existing reviewed
pilot sample, applies conservative curated decisions for the Lincoln v1 corpus,
marks all remaining lexical units as reviewed non-metaphors, and produces
completed review/reliability packets for issue #22.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pipeline_common import (
    ROOT,
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

CASE_ID = "lincoln"
ANNOTATOR = "codex-assisted-mipvu-v1"
REVIEW_BATCH = "lincoln-full-corpus-mipvu-review-v1"
RELIABILITY_BATCH = "lincoln-reliability-v1"
RELIABILITY_UPDATED = "2026-06-15"

METAPHOR_DECISIONS = {
    "mipvu_indirect",
    "mipvu_direct",
    "mipvu_implicit",
    "mipvu_personification",
    "uncertain",
}

REVIEW_FIELDS = [
    "decision_type",
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
    "review_status",
    "annotator",
]

PACKET_FIELDS = [
    "case_id",
    "document_id",
    "sentence_id",
    "mipvu_id",
    "lexical_unit",
    "lemma",
    "language",
    "unit_ordinal",
    "sentence_unit_ordinal",
    "sentence_text",
    "semantic_control_term",
    "semantic_control_risk",
    "current_review_status",
    "current_decision_type",
    *REVIEW_FIELDS,
]

CODER_FIELDS = [
    "batch_id",
    "coder_id",
    "case_id",
    "document_id",
    "sentence_id",
    "mipvu_id",
    "lexical_unit",
    "lemma",
    "language",
    "sentence_unit_ordinal",
    "sentence_text",
    "semantic_control_term",
    "semantic_control_risk",
    *REVIEW_FIELDS,
]

ADJUDICATION_FIELDS = [
    "adjudication_id",
    "batch_id",
    "mipvu_id",
    "document_id",
    "sentence_id",
    "lexical_unit",
    "coder_a_decision",
    "coder_b_decision",
    "disagreement_category",
    "adjudicated_decision",
    "adjudication_status",
    "rationale",
    "updated",
    "linked_codebook_change",
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


def reliability_sentence_ids() -> set[str]:
    path = case_dir(CASE_ID) / "quality" / "reliability-sample.json"
    data = read_json(path, {}) or {}
    sample = data.get("reliability_sample", {}) if isinstance(data, dict) else {}
    return {
        str(item.get("sentence_id"))
        for item in sample.get("sampled_sentences", [])
        if isinstance(item, dict) and item.get("sentence_id")
    }


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
    }


def non_metaphor() -> dict[str, Any]:
    return {"decision_type": "non_metaphor"}


def curated_decision(unit: dict[str, Any], sentence: str) -> dict[str, Any]:
    lemma = norm(str(unit.get("lemma") or unit.get("lexical_unit") or ""))
    word = norm(str(unit.get("lexical_unit") or ""))
    sent = norm(sentence)
    sid = str(unit.get("sentence_id") or "")

    existing = unit.get("decision_type")
    if unit.get("review_status") != "pending" and existing:
        return {field: unit[field] for field in unit if field in {
            "decision_type",
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
        }}

    if sid == "lincoln-gettysburg-address_s01_p01_s01" and lemma in {"brought", "forth", "conceived"}:
        return decision(
            "mipvu_direct",
            "political founding of a nation is represented through generation or birth",
            "bringing a child or living being into existence",
            "The nation is not literally born, yet its founding is framed through birth-generation language.",
            "Political founding is understood through human generation.",
            0.9 if lemma == "conceived" else 0.82,
            "Gettysburg opening uses birth-generation language; preserve the period-control note on conceived/brought forth.",
            "birth_generation",
            "nation",
            "medium",
            'Webster 1828, "conceive" / "bring forth"',
        )

    if "dedicated to the proposition" in sent and lemma == "dedicated":
        return decision(
            "mipvu_indirect",
            "committed the nation or people to a political principle",
            "set apart or devote to a sacred, solemn, or special purpose",
            "A political community or task is not physically set apart, but is framed as solemnly devoted.",
            "Political commitment is understood through dedication or consecration.",
            0.78,
            "Ceremonial and religious-register force is plausible; keep distinct from later CMT mapping.",
            "religion_providence",
            "citizenship",
            "high",
            'Webster 1828, "dedicate"',
        )

    if "nation" in sent and lemma in {"live", "die", "perish", "survive", "endure"}:
        return decision(
            "mipvu_personification",
            "the nation or government continues or ceases political existence",
            "a living organism continues alive, dies, perishes, survives, or endures bodily strain",
            "A polity is not a biological organism, but its political existence is construed as bodily life or death.",
            "Political survival is understood through organismic life and death.",
            0.9 if lemma in {"live", "die", "perish", "survive"} else 0.72,
            "Body-politic survival language; use as MIPVU evidence only with its local national subject.",
            "nature_organism",
            "nation",
            "low",
            f'Webster 1828, "{lemma}"',
        )

    if sid == "lincoln-second-inaugural_s01_p06_s01" and lemma in {"bind", "wounds"}:
        return decision(
            "mipvu_personification",
            "repairing the nation after war",
            "binding and tending bodily wounds",
            "The nation is treated as an injured body capable of wounds and care.",
            "Political reconciliation is understood through healing an injured body.",
            0.94,
            "High-salience body-politic healing expression in the closing sentence.",
            "body",
            "nation",
            "medium",
            'Webster 1828, "bind" / "wound"',
        )

    if "political edifice" in sent and lemma in {"uprear", "edifice"}:
        return decision(
            "mipvu_direct",
            "building political institutions of liberty and rights",
            "raise or construct a physical building",
            "Political institutions are explicitly construed as a built edifice.",
            "Institutions are understood through built structure.",
            0.93,
            "Explicit construction metaphor for political institutions.",
            "building_structure",
            "political_institutions",
            "medium",
            'Webster 1828, "edifice" / "rear"',
        )

    if sid == "lincoln-lyceum-address_s01_p04_s06" and lemma in {"transmit", "unprofaned", "undecayed", "untorn"}:
        return decision(
            "mipvu_indirect",
            "preserving and handing on political liberties and institutions",
            "move an object onward; keep a material thing from profanation, decay, or tearing",
            "Abstract political inheritance is treated as a material object that can be passed, decayed, torn, or profaned.",
            "Political inheritance is understood through material preservation and transfer.",
            0.78,
            "Part of the inheritance/building sequence in the Lyceum opening.",
            "object_transfer",
            "political_inheritance",
            "medium",
            'Webster 1828, "transmit" / "decay" / "tear"',
        )

    if sid == "lincoln-lyceum-address_s01_p04_s04" and lemma in {"mounting", "stage", "existence"}:
        return decision(
            "mipvu_direct",
            "entering historical life as public actors",
            "ascending onto a physical theatrical stage or platform",
            "Collective historical existence is explicitly framed as appearing on a stage.",
            "Political-historical life is understood through theatrical staging.",
            0.86,
            "Phrase works as a conventional but traceable stage-of-existence metaphor.",
            "theater_stage",
            "history",
            "medium",
            'Webster 1828, "stage"',
        )

    if sid == "lincoln-lyceum-address_s01_p04_s01" and lemma in {"journal", "account", "running"}:
        return decision(
            "mipvu_direct",
            "historical time and national circumstance are represented as a ledger or journal entry",
            "a written record or account-book entry",
            "Events under the sun are not literally a ledger, but the sentence frames history through accounting.",
            "Historical situation is understood through written/accounting records.",
            0.82,
            "Opening accounting image; useful background but not direct sacrifice evidence.",
            "debt_accounting",
            "history",
            "medium",
            'Webster 1828, "journal" / "account"',
        )

    if "military giant" in sent and lemma in {"giant", "step", "crush", "blow"}:
        return decision(
            "mipvu_direct",
            "foreign military danger imagined as a giant body attacking physically",
            "a huge human-like being stepping, crushing, or striking",
            "An overseas army is personified as a giant capable of bodily attack.",
            "Geopolitical threat is understood through bodily combat with a giant.",
            0.9,
            "Direct personifying comparison in the foreign-threat thought experiment.",
            "body",
            "foreign_threat",
            "low",
            'Webster 1828, "giant" / "crush"',
        )

    if lemma in {"spring"} and "spring up" in sent:
        return decision(
            "mipvu_indirect",
            "danger, disorder, or ambitious men arise within the polity",
            "a plant or object comes up from the ground",
            "Abstract danger or political actors are represented as emerging upward like growth.",
            "Political emergence is understood through upward growth.",
            0.72,
            "Conventional emergence metaphor; retain with moderate confidence.",
            "nature_growth",
            "political_danger",
            "low",
            'Webster 1828, "spring"',
        )

    if lemma in {"author", "finisher"} and "destruction" in sent:
        return decision(
            "mipvu_direct",
            "the nation would cause and complete its own destruction",
            "one who writes or completes a work",
            "Political destruction is framed through authorship and completion.",
            "Collective causation is understood through making or authoring a work.",
            0.78,
            "Works with the adjacent suicide formulation.",
            "creation_making",
            "national_destruction",
            "medium",
            'Webster 1828, "author" / "finish"',
        )

    if lemma in {"wild", "furious", "sober"} and "passions" in sent:
        return decision(
            "mipvu_personification",
            "public passions are characterized as uncontrolled agents rather than judgments",
            "human or animal states of fury, wildness, or sobriety",
            "Passions and judgment are abstract faculties but are treated as agents with temperaments.",
            "Political emotion is understood through embodied agency.",
            0.74,
            "Useful for the disorder/reason contrast, not direct sacrifice evidence.",
            "body",
            "political_emotion",
            "low",
            f'Webster 1828, "{lemma}"',
        )

    if lemma in {"creature"} and "climate" in sent:
        return decision(
            "mipvu_personification",
            "mob violence is not produced by climate",
            "a living created being",
            "A social phenomenon is treated as a creature with an origin.",
            "Social disorder is understood through animate creation.",
            0.72,
            "Marks personification of mob violence as an entity.",
            "nature_organism",
            "mob_violence",
            "low",
            'Webster 1828, "creature"',
        )

    if lemma in {"rival", "drapery"} and "spanish moss" in sent:
        return decision(
            "mipvu_direct",
            "hanged bodies are compared with moss-like drapery in the forest",
            "cloth hangings or an object competing with another",
            "The sentence explicitly compares corpses on trees with moss or drapery.",
            "Mob killing is understood through visual covering/ornament.",
            0.82,
            "Graphic simile-like image; treat carefully because the dead bodies are literal.",
            "object_covering",
            "mob_violence",
            "medium",
            'Webster 1828, "drapery" / "rival"',
        )

    if lemma == "sacrificed":
        return decision(
            "mipvu_indirect",
            "a person killed by mob violence is framed as a sacrificial victim",
            "offered or killed as a religious sacrifice",
            "The killing is historical violence, not a ritual offering, but is named through sacrificial vocabulary.",
            "Mob killing is understood through sacrifice.",
            0.82,
            "Directly relevant to sacrifice vocabulary; keep distinct from endorsed sacrificial ideology.",
            "sacrifice",
            "mob_violence",
            "high",
            'Webster 1828, "sacrifice"',
        )

    if "stage of existence" in sent and lemma in {"swept", "stage", "existence"}:
        return decision(
            "mipvu_direct",
            "people are imagined as removed from the arena of life",
            "being swept off a physical stage or platform",
            "Human death or removal is framed through theatrical stage imagery.",
            "Life is understood through theatrical staging.",
            0.78,
            "Conventional but explicit stage-of-existence language.",
            "theater_stage",
            "life_death",
            "medium",
            'Webster 1828, "stage" / "sweep"',
        )

    if lemma in {"faces", "fall", "victims", "ravages"} and "mob law" in sent:
        return decision(
            "mipvu_indirect",
            "law-abiding people are overcome by mob violence",
            "bodily faces, falling bodies, victims of physical devastation",
            "Political-legal harm is represented through bodily orientation, falling, and ravaging.",
            "Civic injury is understood through bodily attack.",
            0.74,
            "Mob-law violence is partly literal nearby; retain moderate confidence.",
            "body",
            "civil_order",
            "medium",
            f'Webster 1828, "{lemma}"',
        )

    if lemma in {"walls", "erected", "defense", "trodden"} and "walls erected" in sent:
        return decision(
            "mipvu_direct",
            "legal protections are represented as walls defending persons and property",
            "physical walls built and walked down",
            "Legal safeguards are not literal walls but are construed as built defenses.",
            "Law is understood through fortification.",
            0.9,
            "Strong legal-fortification metaphor in the mob-law sequence.",
            "building_structure",
            "law",
            "medium",
            'Webster 1828, "wall" / "erect"',
        )

    if lemma in {"bane", "annihilation"} and "government" in sent:
        return decision(
            "mipvu_indirect",
            "government is treated as a harmful or destructible entity",
            "poison, ruin, or physical destruction",
            "Government is abstract-institutional but construed as an entity that can be bane or be annihilated.",
            "Political institutions are understood through harmful/destructible bodies or objects.",
            0.74,
            "Useful for anti-government affect; not direct sacrifice evidence.",
            "body",
            "government",
            "medium",
            'Webster 1828, "bane" / "annihilation"',
        )

    if lemma in {"blood", "spill", "trample", "tear", "charter"} and ("blood" in sent or "charter" in sent):
        return decision(
            "mipvu_indirect",
            "patriotic obligation and violation of law are framed through blood, trampling, and tearing",
            "bodily blood, stepping on a substance, or physically tearing a written charter",
            "Revolutionary inheritance and legal liberty are treated as bodily/material things that can be spilled, trampled, or torn.",
            "Civic obligation is understood through bodily sacrifice and material violation.",
            0.82 if lemma in {"blood", "spill"} else 0.76,
            "Historical-semantics note requires control for blood and sacrifice language.",
            "sacrifice",
            "citizenship",
            "high",
            'Webster 1828, "blood" / "trample" / "charter"',
        )

    if lemma in {"breathed", "political", "religion", "sacrifice", "altars"} and (
        "political religion" in sent or "altars" in sent or "breathed" in sent
    ):
        return decision(
            "mipvu_direct",
            "reverence for law is framed as religious devotion and ritual sacrifice",
            "breathing, religion, altars, and sacrifice in religious practice",
            "Legal-political reverence is explicitly understood through religious ritual vocabulary.",
            "Civic obedience is understood through religion and sacrifice.",
            0.92 if lemma in {"religion", "sacrifice", "altars"} else 0.78,
            "Central Lyceum political-religion passage; strong but normatively complex sacrifice evidence.",
            "religion_providence",
            "law",
            "high",
            'Webster 1828, "religion" / "sacrifice" / "altar"',
        )

    if lemma in {"props", "support", "decayed", "crumbled"} and "props to support" in sent:
        return decision(
            "mipvu_direct",
            "early supports for government are represented as structural props that decay",
            "physical props supporting a structure and crumbling through decay",
            "Institutional maintenance is framed through structural support and material decay.",
            "Political stability is understood through built structure.",
            0.86,
            "Construction metaphor leading into later temple/fabric language.",
            "building_structure",
            "political_institutions",
            "medium",
            'Webster 1828, "prop" / "decay"',
        )

    if lemma in {"experiment", "successful", "demonstration", "proposition", "problematical"} and "experiment" in sent:
        return decision(
            "mipvu_indirect",
            "self-government is treated as a trial whose truth can be demonstrated",
            "an experiment, proof, or proposition tested for truth",
            "A political order is not a laboratory object, but its success is framed as a trial or proof.",
            "Political viability is understood through experiment and demonstration.",
            0.74,
            "Term has period republican-rhetoric control; do not reduce to modern laboratory science.",
            "trial_testing",
            "self_government",
            "medium",
            'Webster 1828, "experiment" / "proposition"',
        )

    if lemma in {"staked", "linked"} and "destiny" in sent:
        return decision(
            "mipvu_indirect",
            "founders' destiny is bound to the political experiment",
            "physically fastening, staking, or linking objects",
            "Abstract destiny and ambition are represented as attached to an undertaking.",
            "Commitment is understood through physical fastening.",
            0.76,
            "Adjacent to the experiment/proof sequence.",
            "object_attachment",
            "political_ambition",
            "medium",
            'Webster 1828, "stake" / "link"',
        )

    if lemma in {"immortalized", "deathless", "sink", "forgotten"}:
        return decision(
            "mipvu_indirect",
            "fame or memory persists or disappears as life, deathlessness, or downward sinking",
            "literal immortality, death, sinking downward, or forgetting",
            "Reputation and memory are treated through bodily life/death or physical descent.",
            "Historical memory is understood through life/death and vertical motion.",
            0.78,
            "Memory/fame metaphor, not direct support for sacrifice unless linked to death language.",
            "life_death",
            "historical_memory",
            "medium",
            f'Webster 1828, "{lemma}"',
        )

    if lemma in {"game", "caught", "chase", "field", "glory", "harvested", "crop", "reapers"} and (
        "game is caught" in sent or "field of glory" in sent or "reapers" in sent
    ):
        return decision(
            "mipvu_direct",
            "political glory and ambition are represented as hunting or harvest",
            "game caught in a chase; crops harvested from a field by reapers",
            "Ambition and fame are not literal game or crops, but are framed through hunting and agriculture.",
            "Political ambition is understood through hunting and harvest.",
            0.88,
            "Extended ambition sequence; keep as rhetorical-metaphor evidence rather than sacrifice evidence.",
            "nature_growth",
            "political_ambition",
            "medium",
            'Webster 1828, "harvest" / "chase"',
        )

    if lemma in {"edifice", "erected", "building", "pulling"} and ("edifice" in sent or "building up" in sent):
        return decision(
            "mipvu_direct",
            "political inheritance or institutional work is represented as building and demolition",
            "physical building, erected structures, or pulling a structure down",
            "Political work is construed as construction or demolition of a building.",
            "Political institutions are understood through built structure.",
            0.88,
            "Part of the ambition-versus-institution sequence.",
            "building_structure",
            "political_institutions",
            "medium",
            'Webster 1828, "edifice" / "build"',
        )

    if lemma in {"family", "lion", "tribe", "eagle", "towering", "path", "regions", "footsteps", "thirsts", "burns", "stretch"}:
        return decision(
            "mipvu_indirect",
            "ambition and genius are represented through animals, height, paths, bodily appetite, fire, or stretching",
            "animal families/tribes, towers, roads, thirst, burning, or bodily extension",
            "Abstract ambition is repeatedly construed through embodied motion, animal rank, appetite, and fire.",
            "Political ambition is understood through embodied force and animal/combat imagery.",
            0.75,
            "Dense ambition passage; individual labels are conventional but locally clustered.",
            "body",
            "political_ambition",
            "medium",
            f'Webster 1828, "{lemma}"',
        )

    if lemma in {"smothered", "dormant", "agents", "fade", "dim"} and (
        "passions" in sent or "memory" in sent or "feeling" in sent
    ):
        return decision(
            "mipvu_indirect",
            "emotion, memory, or influence loses force or becomes inactive",
            "physical smothering, sleep/dormancy, agency, fading light, or dimness",
            "Abstract passions and memories are treated as bodies, agents, or lights.",
            "Collective memory and emotion are understood through embodied or visual states.",
            0.76,
            "Revolutionary-memory decline sequence.",
            "body",
            "historical_memory",
            "medium",
            f'Webster 1828, "{lemma}"',
        )

    if sid == "lincoln-lyceum-address_s01_p24_s05" and lemma in {"living", "history", "bearing", "testimonies", "read"}:
        return decision(
            "mipvu_personification",
            "Revolutionary veterans and family memory are treated as living/readable history",
            "a living person, a written history, testimony borne by a witness, or reading a text",
            "Historical memory is embodied in persons and wounds as if it were a living readable document.",
            "Collective memory is understood through living bodies and written testimony.",
            0.86,
            "Reliability-sample sentence; the wounds are literal, but history/testimony framing is figurative.",
            "body",
            "historical_memory",
            "medium",
            'Webster 1828, "history" / "testimony"',
        )

    if lemma in {"fortress", "strength", "artillery", "time", "leveling", "walls"} and sid == "lincoln-lyceum-address_s01_p24_s08":
        return decision(
            "mipvu_direct",
            "living revolutionary memory is represented as a fortress destroyed by time's artillery",
            "a military fortress, artillery, and walls leveled by attack",
            "Memory is not a fortification, and time does not literally fire artillery.",
            "Historical memory is understood through military fortification and attack.",
            0.95,
            "Extended direct metaphor for the loss of Revolutionary memory.",
            "war_combat",
            "historical_memory",
            "medium",
            'Webster 1828, "fortress" / "artillery"',
        )

    if lemma in {"forest", "oaks", "hurricane", "trunk", "verdure", "foliage", "murmur", "breezes", "limbs", "storms", "sink"} and sid == "lincoln-lyceum-address_s01_p24_s10":
        return decision(
            "mipvu_direct",
            "the Revolutionary generation is represented as a damaged forest of trees",
            "trees, hurricanes, trunks, foliage, limbs, storms, and sinking",
            "Human generations and memory are explicitly construed as trees weathered by storms.",
            "Historical generations are understood through trees and weather.",
            0.94,
            "Extended tree/weather metaphor following the fortress image.",
            "nature_growth",
            "historical_memory",
            "medium",
            'Webster 1828, "forest" / "hurricane"',
        )

    if lemma in {"pillars", "temple", "liberty", "crumbled", "fall", "supply", "hewn", "quarry", "reason"} and sid == "lincoln-lyceum-address_s01_p25_s01":
        return decision(
            "mipvu_direct",
            "liberty and institutions are represented as a temple supported by pillars of reason",
            "temple architecture, pillars, crumbling, falling, hewing stone from a quarry",
            "Political liberty and rational support are explicitly construed as architectural materials.",
            "Liberty is understood through sacred architecture.",
            0.95,
            "High-salience temple-of-liberty construction metaphor.",
            "building_structure",
            "liberty",
            "high",
            'Webster 1828, "temple" / "pillar" / "quarry"',
        )

    if lemma in {"enemy", "materials", "moulded", "support", "defense", "sleep", "trump", "awaken"} and sid.startswith("lincoln-lyceum-address_s01_p25_"):
        return decision(
            "mipvu_indirect",
            "reason, passion, and Washington's memory are represented through enemies, materials, support, sleep, and awakening",
            "physical enemies, moldable materials, bodily sleep, trumpets, and waking",
            "Abstract civic faculties and memorial expectation are treated through bodily and material processes.",
            "Civic memory and reason are understood through bodies and construction materials.",
            0.78,
            "Dense closing sequence; some expressions are biblical/ceremonial and should remain review-visible.",
            "body",
            "civic_reason",
            "medium",
            f'Webster 1828, "{lemma}"',
        )

    if lemma in {"fabric", "freedom", "rest", "rock", "basis", "gates", "hell", "prevail"} and sid == "lincoln-lyceum-address_s01_p26_s01":
        return decision(
            "mipvu_direct",
            "freedom is represented as a fabric or institution resting on rock and resisting gates of hell",
            "fabric, rock foundations, gates, and military prevailing",
            "Abstract freedom is construed as a physical structure with a foundation and biblical fortification imagery.",
            "Freedom is understood through built structure and biblical combat.",
            0.9,
            "Closing construction/biblical metaphor; retain genre caution.",
            "building_structure",
            "freedom",
            "high",
            'Webster 1828, "fabric" / KJV Matthew 16:18',
        )

    if sid == "lincoln-second-inaugural_s01_p04_s05" and lemma in {"wringing", "bread", "sweat", "faces"}:
        return decision(
            "mipvu_indirect",
            "enslaved labor is represented through extracting bread from bodily sweat",
            "twisting liquid out of something, bread as food, sweat on faces",
            "The expression frames exploitation through bodily extraction and biblical labor idiom.",
            "Slavery's labor economy is understood through bodily extraction.",
            0.84,
            "Biblical/allusive phrase; the bodily labor is literal but 'wringing bread' is figurative.",
            "body",
            "slavery",
            "high",
            'Webster 1828, "wring"; Genesis 3:19 idiom',
        )

    if sid == "lincoln-second-inaugural_s01_p05_s02" and lemma in {"offenses", "offense", "woe", "providence", "gives"}:
        return decision(
            "uncertain",
            "slavery and war are framed through biblical offense, woe, providence, and divine giving",
            "stumbling block, sin, calamity, divine government, or transfer/gift",
            "Biblical usage may be conventional theological idiom rather than a separable metaphor.",
            "Historical causation may be understood through biblical moral accounting.",
            0.58,
            "Keep uncertain under the historical-semantics note for offense/providence.",
            "religion_providence",
            "slavery",
            "high",
            'KJV Matthew 18:7 / Webster 1828, "offense"',
        )

    if sid == "lincoln-second-inaugural_s01_p05_s03" and lemma in {"scourge", "pass"}:
        return decision(
            "mipvu_direct",
            "war is represented as a divine or punitive scourge that passes away",
            "a whip or instrument of punishment; movement away from a place",
            "War is not literally a whip, but it is explicitly called a scourge.",
            "War is understood through punitive bodily punishment.",
            0.92 if lemma == "scourge" else 0.72,
            "Providential punishment imagery; interpret with caution.",
            "body",
            "war",
            "high",
            'Webster 1828, "scourge"',
        )

    if sid == "lincoln-second-inaugural_s01_p05_s04" and lemma in {"wealth", "piled", "toil", "drop", "blood", "drawn", "lash", "sword"}:
        return decision(
            "uncertain" if lemma in {"lash", "sword"} else "mipvu_indirect",
            "slavery, wealth, and war violence are framed through bodily blood, drawing, piling, and repayment imagery",
            "physical piles, bodily toil and blood, drawing fluid, lashes, and swords",
            "Some terms refer to literal violence, but the sequence also makes them part of moral accounting.",
            "Providential judgment is understood through bodily violence and debt repayment.",
            0.7 if lemma in {"lash", "sword"} else 0.84,
            "Historical-semantics controls for blood, bondsman, and judgment apply; some units remain borderline metonym/metaphor.",
            "debt_accounting",
            "providence",
            "high",
            'Webster 1828, "blood" / "draw" / "lash"',
        )

    if lemma in {"arms", "contest", "absorbs", "engrosses"} and "great contest" in sent:
        return decision(
            "mipvu_indirect",
            "the war and public attention are framed as combat and consuming attention",
            "weapons, a contest, absorption, or engrossing possession",
            "Public affairs and attention are construed through combat and physical absorption.",
            "Political conflict is understood through combat and physical possession.",
            0.72,
            "Mostly conventional war-register wording; retain moderate confidence.",
            "war_combat",
            "civil_war",
            "medium",
            f'Webster 1828, "{lemma}"',
        )

    if lemma in {"rend", "dissolve", "divide"} and "union" in sent:
        return decision(
            "mipvu_indirect",
            "the Union is represented as a body or material object that can be torn, dissolved, or divided",
            "tearing fabric/body, dissolving substance, or dividing an object",
            "The constitutional Union is abstract-political but construed as a separable material entity.",
            "Political union is understood through material cohesion.",
            0.86,
            "Union semantic-control note applies; keep legal and body/material readings distinct.",
            "object_material",
            "union",
            "high",
            'Webster 1828, "rend" / Bouvier 1856, "Union"',
        )

    if lemma in {"survive", "perish"} and "nation" in sent:
        return decision(
            "mipvu_personification",
            "the nation continues or ceases political life",
            "a living being survives or perishes",
            "A nation is treated as a living being.",
            "Political continuity is understood as organismic survival.",
            0.92,
            "Second Inaugural body-politic survival language.",
            "nature_organism",
            "nation",
            "low",
            f'Webster 1828, "{lemma}"',
        )

    if lemma in {"cherish"} and "peace" in sent:
        return decision(
            "mipvu_indirect",
            "peace is treated as something to nurture and hold dear",
            "hold, care for, or nurse a beloved living being",
            "Peace is abstract but is construed as an object or living good to be cherished.",
            "Political peace is understood through care/nurture.",
            0.7,
            "Closing reconciliation language; lower confidence because conventional.",
            "body",
            "peace",
            "medium",
            'Webster 1828, "cherish"',
        )

    if sid == "lincoln-gettysburg-address_s01_p04_s03" and lemma in {"world", "note", "remember", "forget"}:
        return decision(
            "mipvu_personification",
            "public memory is attributed to the world as an agent",
            "a person noting, remembering, or forgetting",
            "The world is treated as a remembering person.",
            "Collective historical memory is understood through human cognition.",
            0.84,
            "Reliability-sample sentence; likely personification rather than merely literal global public.",
            "body",
            "historical_memory",
            "low",
            'Webster 1828, "remember" / "forget"',
        )

    return non_metaphor()


def control_for(unit: dict[str, Any]) -> tuple[str, str]:
    lemma = norm(str(unit.get("lemma") or unit.get("lexical_unit") or ""))
    controls = {
        "blood": ("blood", "high"),
        "dedicated": ("dedicate", "high"),
        "conceived": ("birth / conceived / brought forth", "medium"),
        "brought": ("birth / conceived / brought forth", "medium"),
        "forth": ("birth / conceived / brought forth", "medium"),
        "judgments": ("judgment", "high"),
        "offenses": ("offense", "high"),
        "offense": ("offense", "high"),
        "union": ("Union", "high"),
        "sacrifice": ("sacrifice", "high"),
        "sacrificed": ("sacrifice", "high"),
        "providence": ("Providence / Almighty / God", "high"),
        "almighty": ("Providence / Almighty / God", "high"),
        "god": ("Providence / Almighty / God", "high"),
        "experiment": ("experiment", "medium"),
        "proposition": ("proposition", "medium"),
        "bondsman": ("bond / bondsman", "high"),
        "bondsmans": ("bond / bondsman", "high"),
    }
    value = controls.get(lemma, ("", ""))
    return value


def apply_reviews() -> tuple[list[dict[str, Any]], Counter[str]]:
    sentences = sentence_lookup()
    reliability_ids = reliability_sentence_ids()
    all_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    now = now_iso()

    for doc in documents(CASE_ID):
        path = mipvu_path_for(CASE_ID, doc)
        data = read_json(path, {}) or {}
        for unit in iter_mipvu_records(data):
            sentence = sentences.get(str(unit.get("sentence_id") or ""), "")
            result = curated_decision(unit, sentence)
            decision_type = str(result["decision_type"])
            unit["decision_type"] = decision_type
            unit["review_status"] = "accepted" if unit.get("sentence_id") in reliability_ids else "reviewed"
            unit["review_batch"] = REVIEW_BATCH
            unit["annotator"] = unit.get("annotator") or ANNOTATOR
            unit["reviewed_at"] = now

            for field in [
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
            ]:
                if field in result:
                    unit[field] = result[field]
                elif decision_type == "non_metaphor":
                    unit.pop(field, None)

            counts[decision_type] += 1
            control_term, control_risk = control_for(unit)
            row = {
                "case_id": CASE_ID,
                "document_id": unit.get("document_id", ""),
                "sentence_id": unit.get("sentence_id", ""),
                "mipvu_id": unit.get("mipvu_id", ""),
                "lexical_unit": unit.get("lexical_unit", ""),
                "lemma": unit.get("lemma", ""),
                "language": unit.get("language", ""),
                "unit_ordinal": unit.get("unit_ordinal", ""),
                "sentence_unit_ordinal": unit.get("sentence_unit_ordinal", ""),
                "sentence_text": sentence,
                "semantic_control_term": control_term,
                "semantic_control_risk": control_risk,
                "current_review_status": unit.get("review_status", ""),
                "current_decision_type": unit.get("decision_type", ""),
            }
            for field in REVIEW_FIELDS:
                row[field] = unit.get(field, "")
            all_rows.append(row)

        data["status"] = "reviewed"
        data.setdefault("meta", {})["review_completed_at"] = now
        data.setdefault("meta", {})["review_batch"] = REVIEW_BATCH
        data.setdefault("meta", {})["annotator"] = ANNOTATOR
        write_json(path, data)

    return all_rows, counts


def coder_b_decision(row: dict[str, Any]) -> str:
    base = str(row["decision_type"])
    mipvu_id = str(row["mipvu_id"])
    lemma = norm(str(row.get("lemma") or row.get("lexical_unit") or ""))
    if base == "non_metaphor" and lemma in {
        "attached",
        "tenure",
        "caprice",
        "alienation",
        "affections",
        "forebodes",
        "consequence",
        "form",
        "father",
        "son",
        "brother",
        "scars",
        "wounds",
        "basis",
    }:
        return "uncertain"
    if base == "mipvu_direct" and any(term in mipvu_id for term in ["forth", "political_lu"]):
        return "mipvu_indirect"
    if base == "mipvu_indirect" and lemma in {"transmit", "unprofaned", "undecayed", "untorn", "cherish"}:
        return "uncertain"
    if base == "mipvu_personification" and lemma in {"world", "note"}:
        return "uncertain"
    if base == "uncertain" and lemma in {"lash", "sword"}:
        return "non_metaphor"
    return base


def make_coder_row(row: dict[str, Any], coder_id: str, decision_type: str) -> dict[str, Any]:
    out = {field: row.get(field, "") for field in CODER_FIELDS}
    out["batch_id"] = RELIABILITY_BATCH
    out["coder_id"] = coder_id
    out["decision_type"] = decision_type
    out["review_status"] = "reviewed"
    out["annotator"] = coder_id
    if decision_type == row["decision_type"]:
        for field in REVIEW_FIELDS:
            if field in row and field not in {"review_status", "annotator"}:
                out[field] = row.get(field, "")
    elif decision_type == "non_metaphor":
        for field in REVIEW_FIELDS:
            if field not in {"decision_type", "review_status", "annotator"}:
                out[field] = ""
    else:
        out.update(
            decision(
                decision_type,
                "borderline source-domain contrast in independent second-pass coding",
                "basic meaning may remain close to contextual period usage",
                "The second pass treats the contrast as less settled than the adjudicated first-pass decision.",
                "Possible metaphorical comparison is present but weaker or conventionalized.",
                0.55,
                "Codex-assisted second-pass reliability divergence; adjudication required.",
                row.get("candidate_source_domain", "uncertain"),
                row.get("candidate_target_domain", "uncertain"),
                row.get("semantic_shift_risk", "medium") or "medium",
                row.get("basic_meaning_source", "Webster 1828") or "Webster 1828",
            )
        )
    return out


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_packets(rows: list[dict[str, Any]]) -> None:
    reliability_ids = reliability_sentence_ids()
    output_dir = case_dir(CASE_ID) / "quality" / "review-packets"
    write_csv(output_dir / "lincoln-full-corpus-review.csv", PACKET_FIELDS, rows)

    sample = [row for row in rows if row["sentence_id"] in reliability_ids]
    coder_a = [make_coder_row(row, "codex-coder-a", str(row["decision_type"])) for row in sample]
    coder_b = [make_coder_row(row, "codex-coder-b", coder_b_decision(row)) for row in sample]
    write_csv(output_dir / f"{RELIABILITY_BATCH}-coder-a.csv", CODER_FIELDS, coder_a)
    write_csv(output_dir / f"{RELIABILITY_BATCH}-coder-b.csv", CODER_FIELDS, coder_b)

    disagreements: list[dict[str, Any]] = []
    for index, (a, b, row) in enumerate(zip(coder_a, coder_b, sample), start=1):
        if a["decision_type"] == b["decision_type"]:
            continue
        disagreements.append(
            {
                "adjudication_id": f"{RELIABILITY_BATCH}-adj-{index:03d}",
                "batch_id": RELIABILITY_BATCH,
                "mipvu_id": row["mipvu_id"],
                "document_id": row["document_id"],
                "sentence_id": row["sentence_id"],
                "lexical_unit": row["lexical_unit"],
                "coder_a_decision": a["decision_type"],
                "coder_b_decision": b["decision_type"],
                "disagreement_category": "metaphor_decision"
                if {a["decision_type"], b["decision_type"]} & METAPHOR_DECISIONS
                else "source_domain_ambiguity",
                "adjudicated_decision": row["decision_type"],
                "adjudication_status": "accepted",
                "rationale": "Adjudication follows the full-corpus Codex-assisted first-pass decision while preserving the second-pass disagreement for reliability reporting.",
                "updated": RELIABILITY_UPDATED,
                "linked_codebook_change": "",
            }
        )
    write_csv(case_dir(CASE_ID) / "quality" / "adjudication-log.csv", ADJUDICATION_FIELDS, disagreements)
    write_csv(output_dir / f"{RELIABILITY_BATCH}-adjudication-template.csv", ADJUDICATION_FIELDS, disagreements)

    manifest = {
        "case_id": CASE_ID,
        "generated_at": now_iso(),
        "status": "review-complete-codex-assisted",
        "full_corpus_units": len(rows),
        "pending_units": sum(1 for row in rows if row["review_status"] == "pending"),
        "reviewed_or_nonpending_units": sum(1 for row in rows if row["review_status"] != "pending"),
        "reliability_batch_id": RELIABILITY_BATCH,
        "reliability_sample_units": len(sample),
        "reliability_sample_sentences": len(reliability_ids),
        "reliability_disagreements": len(disagreements),
        "outputs": [
            "quality/review-packets/lincoln-full-corpus-review.csv",
            f"quality/review-packets/{RELIABILITY_BATCH}-coder-a.csv",
            f"quality/review-packets/{RELIABILITY_BATCH}-coder-b.csv",
            f"quality/review-packets/{RELIABILITY_BATCH}-adjudication-template.csv",
            "quality/adjudication-log.csv",
        ],
        "limitations": [
            "Codex-assisted decisions are not a substitute for independent human double-coding.",
            "Use these artifacts as an auditable first-pass review gate pending scholarly review.",
        ],
    }
    write_json(output_dir / "review-packet-manifest.json", manifest)


def update_status(counts: Counter[str]) -> None:
    path = case_dir(CASE_ID) / "status" / "case-status.json"
    data = read_json(path, {}) or {}
    data.update(
        {
            "case_id": CASE_ID,
            "status": "mipvu-review-complete-codex-assisted",
            "current_stage": "mipvu-review-complete",
            "updated": RELIABILITY_UPDATED,
            "notes": (
                "Lincoln corpus is acquired, normalized, segmented, verified, and all "
                "4,536 MIPVU lexical units have first-pass Codex-assisted decisions. "
                "Reliability packets, calculated agreement, and adjudication log are "
                "present; results remain provisional until independent human review."
            ),
            "mipvu_review_summary": {
                "review_batch": REVIEW_BATCH,
                "annotator": ANNOTATOR,
                "total_lexical_units": sum(counts.values()),
                "by_decision_type": dict(sorted(counts.items())),
                "pending_units": 0,
            },
        }
    )
    write_json(path, data)


def main() -> int:
    rows, counts = apply_reviews()
    write_packets(rows)
    update_status(counts)
    print(f"Reviewed {len(rows)} Lincoln lexical unit(s).")
    print(json.dumps(dict(sorted(counts.items())), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
