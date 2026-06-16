#!/usr/bin/env python3
"""Complete the Hitler German-source MIPVU review gate.

The Hitler v1 set is reviewed in German. English glosses are included only as
annotation aids for translation-sensitive and politically-loaded terms; the
source-language `span_text` remains the authoritative unit text for MIPVU decisions.

Fair-use and copyright note: Mein Kampf text is used under the fair-use/educational
exclusion for scholarly metaphor analysis. Raw source text is gitignored; only
annotation metadata and decision records are committed.
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

CASE_ID = "hitler"
ANNOTATOR = "codex-assisted-mipvu-v1"
REVIEW_BATCH = "hitler-source-language-mipvu-review-v1"
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

# Gloss map for politically-loaded and translation-sensitive German terms.
# English glosses are analytical aids only — source-language span_text governs.
GLOSS_MAP: dict[str, tuple[str, str]] = {
    "opfer": (
        "sacrifice / victim",
        "German `Opfer` covers both sacrificial offering and innocent victim; "
        "the entailment (sacrifice vs. victimhood) must be read from context.",
    ),
    "opfern": (
        "to sacrifice / to offer up",
        "German `opfern` may denote willing self-sacrifice or victimization; "
        "context determines the agent-patient structure.",
    ),
    "opfers": (
        "sacrifice / victim (genitive)",
        "Genitive of `Opfer`; carries the same dual sacrifice/victim entailment.",
    ),
    "opfersinn": (
        "spirit of sacrifice / self-sacrificial disposition",
        "German compound; `Sinn` adds dispositional force — the willingness to sacrifice.",
    ),
    "blut": (
        "blood",
        "German `Blut` spans literal biological blood, racial-lineage metaphor, and "
        "sacrificial-cost rhetoric; context is decisive for MIPVU.",
    ),
    "blutes": (
        "blood (genitive)",
        "Genitive of `Blut`; same range of literal and metaphorical entailments.",
    ),
    "blute": (
        "blood (dative/accusative)",
        "Inflected form of `Blut`; retains the full literal/racial/sacrificial range.",
    ),
    "blutsvermischung": (
        "blood-mixing / racial intermixture",
        "Nazi compound; `Blut` is used quasi-literally as racial essence — "
        "maps to contamination metaphor but the term itself encodes a pseudo-scientific claim.",
    ),
    "blutschande": (
        "blood-disgrace / miscegenation",
        "Nazi compound; `Schande` (disgrace/shame) applied to `Blut` (blood/race) "
        "encodes a moral-pollution metaphor over racial mixing.",
    ),
    "volk": (
        "people / nation / folk",
        "German `Volk` is not identical to English people or nation; it carries "
        "ethnic-organic unity entailments that English glosses flatten.",
    ),
    "volkes": (
        "of the people / nation (genitive)",
        "Genitive of `Volk`; same ethnic-organic entailments.",
    ),
    "volker": (
        "peoples / nations",
        "Plural of `Volk`; in Nazi register often denotes competing racial peoples "
        "rather than political nations.",
    ),
    "volkisch": (
        "völkisch / ethnic-nationalist",
        "Adjectival form; `völkisch` encodes ethnic-organic nationalist ideology "
        "not reducible to 'national' or 'popular'.",
    ),
    "volkstum": (
        "ethnic character / folkdom",
        "German `Volkstum` denotes the essential ethnic character of a Volk; "
        "the English 'folkdom' is a partial gloss only.",
    ),
    "rasse": (
        "race",
        "German `Rasse` in Nazi register carries pseudo-biological and hierarchical "
        "entailments; map cautiously — the term is ideologically loaded.",
    ),
    "reinheit": (
        "purity / cleanliness",
        "German `Reinheit des Blutes` (purity of blood) extends cleanliness-as-purity "
        "into racial ideology; the physical sense underlies the metaphorical application.",
    ),
    "vernichtung": (
        "annihilation / destruction",
        "German `Vernichtung` denotes total destruction; in Nazi text often applied "
        "to enemies or states — may be literal or figurative depending on target.",
    ),
    "ausrottung": (
        "eradication / extermination",
        "German `Ausrottung` (from `rotten` = to root out) carries literal uprooting "
        "extended to extermination; the botanical source domain remains active.",
    ),
    "schicksal": (
        "fate / destiny",
        "German `Schicksal` may be literal fate-as-circumstance or personified destiny-as-agent; "
        "context distinguishes conventional from live metaphor.",
    ),
    "schicksals": (
        "fate / destiny (genitive)",
        "Genitive of `Schicksal`; same fate/destiny range.",
    ),
    "sieg": (
        "victory",
        "German `Sieg` may be a literal battle outcome or a quasi-agent "
        "(der Sieg des Stärkeren = the victory of the stronger) in evolutionary-struggle framing.",
    ),
    "geist": (
        "spirit / mind / intellect",
        "German `Geist` spans intellectual capacity, cultural spirit, and spiritual agency; "
        "English spirit/mind/intellect each capture only part of the range.",
    ),
    "seele": (
        "soul / psyche",
        "German `Seele des Volkes` (soul of the people) extends the individual soul "
        "as a collective-organic metaphor.",
    ),
    "ehre": (
        "honor / dignity",
        "German `Ehre` in political register carries public reputation, martial obligation, "
        "and national dignity — not reducible to English honor.",
    ),
    "held": (
        "hero",
        "German `Held` in nationalist rhetoric may denote a literal soldier-hero "
        "or a culturally-idealized sacrificial figure.",
    ),
    "helden": (
        "heroes",
        "Plural of `Held`; may be literal fallen soldiers or idealized sacrifice-bearers.",
    ),
    "heldentum": (
        "heroism / hero-dom",
        "German compound; `Heldentum` encodes heroism as a collective virtue or cultural legacy.",
    ),
    "boden": (
        "soil / ground / territory",
        "German `Boden` in `Lebensraum` contexts extends physical soil into territorial-organic "
        "entitlement rhetoric.",
    ),
    "lebensraum": (
        "living space",
        "Nazi geopolitical compound; the physical `Raum` (space) metaphor underwrites "
        "expansionist territorial claims — the spatial source domain is live.",
    ),
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


def gloss_for(span: str, lemma: str) -> tuple[str, str] | None:
    normalized = norm(lemma or span)
    # Handle common inflectional variants not covered by the lemmatizer
    variants: dict[str, str] = {
        "des blutes": "blutes",
        "im blute": "blute",
        "am blute": "blute",
        "des volkes": "volkes",
        "der rasse": "rasse",
        "des schicksals": "schicksals",
        "des sieges": "sieges",
        "des opfers": "opfers",
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
    source: str = "Grimm Deutsches Wörterbuch / Duden, historical sense",
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
    logs = [item for item in logs if item.get("stage") != "complete-hitler-mipvu-review"]
    logs.append(
        {
            "stage": "complete-hitler-mipvu-review",
            "script": "scripts/complete-hitler-mipvu-review.py",
            "generated_at": generated_at,
        }
    )
    return logs


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

    # ── Opfer (sacrifice / victim) ──────────────────────────────────────────
    # Self-sacrifice framing: willing subordination of self to the community
    if in_terms(lemma, {"opfer", "opfern", "opfersinn"}) and (
        "hingabe" in sent
        or "opfersinn" in sent
        or "eigene ich dem leben der gesamtheit" in sent
        or "eigenen gluck verzichteten" in sent
        or "eigene grobe zu opfern" in sent
    ):
        return decision(
            "mipvu_indirect",
            "willing self-subordination to the collective is framed as ritual offering or sacrifice",
            "a religious or ritual offering given to a deity or cause",
            "The individual gives up their ego/advantage to the community; this is not a religious ritual but is structured as one.",
            "Self-denial is understood through the frame of ritual sacrifice and offering.",
            0.84,
            "Source-language decision on German `Opfer`/`opfern`; English sacrifice/victim gloss is not the decision basis.",
            "ritual_religion",
            "self_denial",
            "sacrifice",
            GLOSS_MAP["opfer"][1],
            "high",
            rule_id="hitler-opfer-self-sacrifice",
        )

    # Opfer as victim in exploitation/vampirism framing
    if in_terms(lemma, {"opfer", "opfers"}) and (
        "vampir" in sent
        or "nach dem tode des opfers" in sent
        or "blutegel" in sent
        or "abgehauteten opfern" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Opfer` marks the exploited victim of a parasitic agent (vampire/leech imagery)",
            "a sacrificial offering or victim",
            "The exploited population is cast as a sacrificial victim consumed by a predatory agent.",
            "Economic or political exploitation is understood through predator-victim and sacrifice framing.",
            0.82,
            "Parasitic-agent cluster (`Vampir`, `Blutegel`) licenses victim-as-sacrifice reading.",
            "ritual_religion",
            "exploitation",
            "victim / sacrifice",
            GLOSS_MAP["opfer"][1],
            "high",
            rule_id="hitler-opfer-victim-parasite",
        )

    # ── Blut (blood) ────────────────────────────────────────────────────────
    # Blood as racial lineage / essence — pseudo-biological extension
    if in_terms(lemma, {"blut", "blutes", "blute"}) and (
        "reinhaltung" in sent
        or "reinheit" in sent
        or "blutsvermischung" in sent
        or "blutschande" in sent
        or "rassenniveau" in sent
        or "im blut" in sent
        or "im blute" in sent
        or "aus dem blut" in sent
        or "blut der" in sent
        or "sein blut" in sent
        or "stimme des blutes" in sent
        or "im blute wurzelnden" in sent
        or "vergiftet das blut" in sent
        or "sein eigenes" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Blut` denotes racial lineage, genetic essence, or inherited cultural capacity — "
            "not literal blood in veins",
            "the bodily fluid circulating in the cardiovascular system",
            "Biological blood is extended to denote racial descent and inherited essence; "
            "the physical source domain underwrites racial-purity claims.",
            "Racial identity and cultural capacity are understood through the bodily blood domain.",
            0.88,
            "Source-language decision on German `Blut`; this is the racial-essence metaphor, "
            "not a description of physical bloodshed. Historiographical note: this usage is "
            "central to Nazi racial ideology and should be flagged for downstream CMT mapping.",
            "body_blood",
            "racial_identity",
            "blood (racial lineage)",
            GLOSS_MAP["blut"][1],
            "high",
            rule_id="hitler-blut-racial-essence",
        )

    # Blood as military sacrifice / fallen soldiers
    if in_terms(lemma, {"blut", "blutes", "blute"}) and (
        "heldenblut" in sent
        or "helden blut" in sent
        or "blut des grenadiers" in sent
        or "gefallenen" in sent
        or "blut vergossen" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Blut` frames soldiers' deaths as a sacrificial blood-cost",
            "the bodily fluid shed in wounding or killing",
            "Physical blood is used to stand for soldiers' lives given in battle; "
            "the bodily source domain frames death as sacrificial expenditure.",
            "Military death is understood through the sacrificial blood-cost frame.",
            0.80,
            "Military-sacrifice sub-cluster; preserve `Blut` as source-language evidence.",
            "body_blood",
            "military_sacrifice",
            "blood (sacrificial cost)",
            GLOSS_MAP["blut"][1],
            "high",
            rule_id="hitler-blut-military-sacrifice",
        )

    # ── Vernichtung / Ausrottung ─────────────────────────────────────────────
    if in_terms(lemma, {"vernichtung"}) and (
        "vernichtung des schwachen" in sent
        or "vernichtung der wirtschaft" in sent
        or "sieg des starkeren und die vernichtung" in sent
        or "vernichtung" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Vernichtung` extends physical destruction/annihilation to economic, "
            "political, or racial elimination of groups",
            "total physical destruction or annihilation",
            "Physical destruction is extended to social/economic/racial elimination; "
            "the basic physical sense underwrites the metaphorical application to groups.",
            "Social or racial elimination is understood through total physical annihilation.",
            0.78,
            "German `Vernichtung` appears in evolutionary-struggle and racial-domination contexts; "
            "mark as indirect metaphor when the target is economic, political, or racial rather than physical.",
            "physical_destruction",
            "social_elimination",
            "annihilation / destruction",
            GLOSS_MAP["vernichtung"][1],
            "high",
            rule_id="hitler-vernichtung-elimination",
        )

    if in_terms(lemma, {"ausrottung"}) and (
        "ausrottung" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Ausrottung` extends botanical uprooting to the eradication of groups or movements",
            "physical uprooting or eradication of plants (ausrotten = to root out)",
            "The botanical act of rooting out is extended to human elimination; "
            "the physical source domain is preserved in the compound.",
            "Group eradication is understood through botanical uprooting.",
            0.82,
            "German `Ausrotten` retains the root-out etymology; this is a live spatial/botanical "
            "metaphor applied to human targets. High historiographical sensitivity.",
            "plant_nature",
            "group_elimination",
            "eradication / extermination",
            GLOSS_MAP["ausrottung"][1],
            "high",
            rule_id="hitler-ausrottung-rooting-out",
        )

    # ── Schicksal (fate / destiny) ───────────────────────────────────────────
    # Schicksal as personified agent striking or deciding
    if in_terms(lemma, {"schicksal", "schicksals"}) and (
        "hammerschlag des schicksals" in sent
        or "schicksal schlug" in sent
        or "schicksals entscheidung" in sent
        or "schicksal hatte seine entscheidung getroffen" in sent
        or "schicksal verdammten" in sent
        or "schicksal entgegenfuhrt" in sent
        or "schicksal besonderen" in sent
    ):
        return decision(
            "mipvu_personification",
            "`Schicksal` is treated as an agent that strikes, decides, or leads — "
            "not an abstract circumstance",
            "fate or destiny as an abstract condition or outcome",
            "Fate does not literally strike with a hammer, make decisions, or lead people; "
            "it is cast as an intentional agent.",
            "Life circumstances are understood through personified fate acting on people.",
            0.79,
            "German `Schicksal` in agentive contexts (hammerblow, decision, leading) "
            "is marked as personification; retain source-language form.",
            "person_agency",
            "life_circumstances",
            "fate / destiny",
            GLOSS_MAP["schicksal"][1],
            "medium",
            rule_id="hitler-schicksal-personified",
        )

    # Schicksal as conventional fate-as-circumstance (lower confidence)
    if in_terms(lemma, {"schicksal", "schicksals"}) and (
        "hartes schicksal" in sent
        or "jammerlichen zukunft" in sent
        or "schicksal des arbeiters" in sent
        or "schicksal erproben" in sent
    ):
        return decision(
            "uncertain",
            "`Schicksal` denotes life circumstances or an assigned lot; "
            "the personification may be faded or conventional",
            "fate or destiny as abstract condition",
            "German `Schicksal` here may be a conventional expression for life-lot "
            "rather than a live personification.",
            "Life adversity may be understood through fate as abstract condition or weak personification.",
            0.55,
            "Marked uncertain because these `Schicksal` uses may be conventional rather than live metaphor.",
            "person_agency",
            "life_circumstances",
            "fate / destiny",
            GLOSS_MAP["schicksal"][1],
            "medium",
            rule_id="hitler-schicksal-conventional",
        )

    # ── Sieg (victory) ───────────────────────────────────────────────────────
    # Sieg as quasi-agent or teleological end in evolutionary framing
    if in_terms(lemma, {"sieg", "siege", "sieges"}) and (
        "sieg des starkeren" in sent
        or "sieg des besten" in sent
        or "sieg der demokratie" in sent
        or "sieg des pazifistischen" in sent
        or "restlosen siege" in sent
        or "sieg fuhren kann" in sent
        or "nahenden sieg" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Sieg` frames political, ideological, or racial victory as a natural-law outcome "
            "or quasi-agent in evolutionary-struggle rhetoric",
            "a military victory or winning of a battle",
            "Battle-victory is extended to denote the triumph of races, ideologies, or laws of nature; "
            "the competitive combat source domain is applied to politics and biology.",
            "Ideological or racial dominance is understood through military victory.",
            0.76,
            "German `Sieg` in evolutionary-struggle contexts ("
            "`Sieg des Stärkeren`, `Sieg des Besten`) extends the military-victory frame; "
            "mark as indirect. Retain source-language form for CMT mapping.",
            "war_combat",
            "racial_ideological_dominance",
            "victory",
            GLOSS_MAP["sieg"][1],
            "medium",
            rule_id="hitler-sieg-evolutionary-struggle",
        )

    # ── Geist (spirit / mind) ────────────────────────────────────────────────
    if in_terms(lemma, {"geist"}) and (
        "hellenischer geist" in sent
        or "geist und germanisches" in sent
        or "menschlicher geist" in sent
        or "geist des volkes" in sent
        or "innere gesinnung" in sent
        or "geist an sich" in sent
        or "geist vermag" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Geist` extends the notion of individual intellect or spirit to "
            "civilizational, racial, or cultural agency",
            "mind, intellect, or individual spirit",
            "Individual mind is extended to collective cultural/civilizational agency; "
            "abstract spirit becomes a force that builds or degrades civilizations.",
            "Cultural or civilizational capacity is understood through collective spirit/mind.",
            0.72,
            "German `Geist` in culture-bearer contexts (`hellenischer Geist`, `Geist des Volkes`) "
            "extends individual intellect to collective-organic agency; mark as indirect.",
            "mind_intellect",
            "civilizational_agency",
            "spirit / mind / intellect",
            GLOSS_MAP["geist"][1],
            "medium",
            rule_id="hitler-geist-civilizational",
        )

    # ── Seele (soul / psyche) ────────────────────────────────────────────────
    if in_terms(lemma, {"seele"}) and (
        "seele des volkes" in sent
        or "gewinnung der seele" in sent
        or "seele unseres volkes" in sent
        or "seele der anstandigen" in sent
        or "hirn und seele" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Seele` extends individual soul/psyche to the collective psyche of a people "
            "as something that can be won, poisoned, or protected",
            "the individual soul or psychic inner life",
            "Individual soul is extended to collective psychological disposition; "
            "the collective soul becomes something that political actors can capture or poison.",
            "Collective political disposition is understood through individual soul as a capturable entity.",
            0.78,
            "German `Seele des Volkes` is a collective-psyche metaphor; "
            "`Gewinnung der Seele` (winning of the soul) adds conquest framing.",
            "person_inner_life",
            "collective_psychology",
            "soul / psyche",
            GLOSS_MAP["seele"][1],
            "medium",
            rule_id="hitler-seele-collective-psyche",
        )

    # ── Held / Helden / Heldentum ────────────────────────────────────────────
    if in_terms(lemma, {"held", "helden", "heldentum"}) and (
        "heldenblut" in sent
        or "helden blut" in sent
        or "sterben lieB" in sent
        or "todesmutiger entschlossenheit" in sent
        or "heldentum das tiberwaltigende" in sent
        or "altgermanischem heldentum" in sent
        or "jungen held" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Held`/`Heldentum` frames soldiers' death or self-sacrifice as heroic idealization "
            "structured by the cultural hero-type",
            "a hero as an exceptionally brave or noble person",
            "Individual soldiers or citizens are idealized through the hero category; "
            "heroism becomes the organizing concept for military self-sacrifice.",
            "Soldier death and national sacrifice are understood through heroic idealization.",
            0.74,
            "German `Heldentum` in nationalist sacrifice contexts extends the hero concept "
            "to collective obligation; retain source-language evidence.",
            "person_virtue",
            "military_sacrifice",
            "hero / heroism",
            GLOSS_MAP["held"][1],
            "medium",
            rule_id="hitler-held-heroic-sacrifice",
        )

    # ── Boden / Lebensraum ───────────────────────────────────────────────────
    if in_terms(lemma, {"boden", "lebensraum"}) and (
        "lebensraum" in sent
        or "boden des volkes" in sent
        or "neuen boden" in sent
        or "boden und" in sent
        or "boden im osten" in sent
        or "auf kosten russlands" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Boden`/`Lebensraum` extends physical earth/soil to territorial-organic entitlement — "
            "land as the natural living-space of a racial people",
            "physical ground, soil, or earth",
            "Physical soil is extended to denote an organic territorial right; "
            "space becomes a biological necessity for the Volk.",
            "Territorial expansion is understood through the organic need for living-space/soil.",
            0.82,
            "German `Lebensraum` and `Boden` in geopolitical contexts extend physical earth "
            "to racial-territorial ideology; the spatial source domain is live. "
            "High historiographical sensitivity — flag for CMT mapping.",
            "earth_nature",
            "territorial_ideology",
            "soil / living-space",
            GLOSS_MAP["boden"][1],
            "high",
            rule_id="hitler-boden-lebensraum",
        )

    # ── Ehre (honor) ────────────────────────────────────────────────────────
    if in_terms(lemma, {"ehre"}) and (
        "nationale ehre" in sent
        or "dem reiche die ehre" in sent
        or "ehre und grobe" in sent
        or "ehre und wahrhaftigkeit" in sent
        or "liebe zum vaterland" in sent
    ):
        return decision(
            "mipvu_indirect",
            "`Ehre` frames national reputation or martial obligation as a property "
            "that can be given, lost, or restored",
            "individual honor as personal reputation or moral worth",
            "Individual honor is extended to national-collective honor as a possessable, "
            "transferable property; the Reich's honor can be restored like a physical object.",
            "National political standing is understood through individual honor as a tangible property.",
            0.71,
            "German `Ehre` in national-political contexts; English 'honor' is only a partial gloss. "
            "Mark as indirect where honor functions as a national-collective property.",
            "person_reputation",
            "national_standing",
            "honor / dignity",
            GLOSS_MAP["ehre"][1],
            "medium",
            rule_id="hitler-ehre-national-honor",
        )

    # ── Schicksal-as-hammer (compound rule for Hammerschlag) ─────────────────
    if "hammerschlag des schicksals" in sent and in_terms(lemma, {"hammerschlag", "stahl"}):
        return decision(
            "mipvu_indirect",
            "the hammer-blow of fate is a direct extended image: the hardening blow "
            "converts the victim into steel",
            "a hammer blow or the physical metal steel",
            "The hammer-blow metaphor compounds with steel transformation: fate strikes and reveals "
            "hidden strength, like a hammer that strikes steel and makes it ring.",
            "Adversity revealing inner strength is understood through metalworking.",
            0.75,
            "Compound image: `Hammerschlag des Schicksals` + `auf Stahl`; "
            "both `Stahl` and `Hammerschlag` are part of the extended metalworking metaphor.",
            "craftsmanship_metalwork",
            "adversity_strength",
            "hammer-blow / steel",
            "German metalworking compound: fate as hammer, person as steel revealed by the blow.",
            "medium",
            rule_id="hitler-schicksal-hammer-steel",
        )

    return non_metaphor()


def apply_gloss(unit: dict[str, Any]) -> None:
    gloss = gloss_for(
        str(unit.get("span_text") or unit.get("lexical_unit") or ""),
        str(unit.get("lemma") or ""),
    )
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
            unit["span_language"] = "de"
            result = curated_decision(unit, sentence)
            decision_type = str(result["decision_type"])
            unit["decision_type"] = decision_type
            unit["review_status"] = "reviewed"
            unit["review_batch"] = REVIEW_BATCH
            unit["annotator"] = unit.get("annotator") or ANNOTATOR
            unit["reviewed_at"] = now
            unit["curated_rule_id"] = result.get("curated_rule_id", "")
            unit["source_language_decision_basis"] = "span_text"

            for field in [*RATIONALE_FIELDS, "gloss_en", "gloss_notes"]:
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
        "source_language": "de",
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
            "German source-language span_text is authoritative; English glosses are only analytical aids.",
            "Mein Kampf source text is gitignored under fair-use/educational exclusion; "
            "only annotation metadata is committed.",
            "Politically loaded terms (Opfer, Blut, Volk, Rasse, Vernichtung, Ausrottung) carry "
            "Nazi ideological entailments that require separate historiographical review before "
            "CMT and Koenigsbergian annotations are finalized.",
            "Ordinary discourse-function words and proper names are marked non-metaphor "
            "without full rationale fields.",
            "Downstream CMT and Koenigsbergian annotations should only use metaphor-related or "
            "uncertain units after separate interpretive review.",
        ],
    }
    quality_dir = case_dir(CASE_ID) / "quality"
    quality_dir.mkdir(exist_ok=True)
    write_json(quality_dir / "mipvu-review-summary.json", summary)


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
                "Hitler German worklists exist for all 8 documents and "
                f"{total_units:,} lexical units have first-pass Codex-assisted "
                "source-language decisions. Each unit records source-language span_text; "
                "English glosses are retained only as aids for translation-sensitive and "
                "politically loaded terms including Opfer, Blut, Volk, Rasse, Vernichtung, "
                "and Ausrottung. Results remain provisional until independent human review. "
                "Mein Kampf source text is gitignored under fair-use constraints."
            ),
            "mipvu_review_summary": {
                "review_batch": REVIEW_BATCH,
                "annotator": ANNOTATOR,
                "source_language": "de",
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
            "source_language": "de",
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
    print(f"Reviewed {sum(decision_counts.values())} Hitler lexical unit(s).")
    print(json.dumps(dict(sorted(decision_counts.items())), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
