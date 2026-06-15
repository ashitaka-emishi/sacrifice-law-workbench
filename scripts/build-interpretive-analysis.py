#!/usr/bin/env python3
"""Build critical metaphor, rhetorical, and absence/agency artifacts."""
from __future__ import annotations

import argparse
from typing import Any

from pipeline_common import (
    case_dir,
    case_ids,
    cmt_mappings_path_for,
    document_id,
    documents,
    iter_cmt_mappings,
    now_iso,
    read_json,
    write_json,
)


LINCOLN_DOCUMENT_CONTEXT = {
    "lincoln-lyceum-address": {
        "audience": "Young Men's Lyceum of Springfield and a civic public concerned with republican institutions",
        "occasion": "Early public address on mob violence, political inheritance, and the perpetuation of American institutions",
        "genre": "public address",
        "rhetorical_action": "Warns that republican survival depends on civic discipline and reverence for law.",
        "emotional_posture": "warning",
        "agency_structure": {
            "agents": ["we", "nation of freemen", "citizens"],
            "patients": ["nation", "political institutions"],
            "beneficiaries": ["future republic", "American people"],
            "passive_or_absent": ["enslaved people", "women", "Indigenous people"],
            "displacement_mechanism": "National survival is framed as collective self-preservation rather than as conflict among named social groups.",
        },
    },
    "lincoln-gettysburg-address": {
        "audience": "Cemetery dedication audience, Union public, mourners, soldiers, and national readers",
        "occasion": "Dedication of the national cemetery after the Battle of Gettysburg",
        "genre": "ceremonial address",
        "rhetorical_action": "Transforms battlefield death into renewed obligation to preserve democratic government and freedom.",
        "emotional_posture": "mourning, consecration, exhortation",
        "agency_structure": {
            "agents": ["honored dead", "living citizens", "we"],
            "patients": ["dead soldiers", "nation", "government of the people"],
            "beneficiaries": ["nation", "freedom", "democratic government"],
            "passive_or_absent": ["Confederate agency", "enslaved people's own agency", "civilian suffering"],
            "displacement_mechanism": "Deaths are generalized as national offering and obligation; specific agents and material bodies recede behind public dedication.",
        },
    },
    "lincoln-second-inaugural": {
        "audience": "Second inaugural audience, wartime public, Union and returning Confederate publics",
        "occasion": "Second presidential inauguration near the end of the Civil War",
        "genre": "inaugural address",
        "rhetorical_action": "Reframes the war as providential judgment on slavery and redirects victory toward reconciliation.",
        "emotional_posture": "humility, judgment, reconciliation",
        "agency_structure": {
            "agents": ["God", "both parties", "we"],
            "patients": ["bondsman", "nation", "war dead"],
            "beneficiaries": ["reunited nation", "emancipation as moral horizon"],
            "passive_or_absent": ["Black political agency", "specific enslavers", "military perpetrators"],
            "displacement_mechanism": "Human agency is partially displaced into providential judgment and shared national guilt.",
        },
    },
}

LINCOLN_CLUSTER_NOTES = {
    "lincoln-01-body-organism": {
        "persuasive_function": "Makes national survival feel like the preservation of a living body rather than an abstract institutional choice.",
        "moral_emotions_activated": ["fear of collective death", "duty", "reverence for survival"],
        "political_actions_authorized": ["civic discipline", "continued preservation of republican government"],
        "negative_cases": ["The current reviewed sample does not yet show a fully medicalized disease or purification logic."],
        "relation_to_koenigsbergian_analysis": "Supports the body-politic corollary more directly than the sacrificial law itself.",
    },
    "lincoln-04-birth-creation": {
        "persuasive_function": "Turns war loss into the possibility of renewed political life.",
        "moral_emotions_activated": ["hope", "obligation", "reverent futurity"],
        "political_actions_authorized": ["continuing the war effort", "renewing democratic commitment"],
        "negative_cases": ["Current evidence is concentrated in the Gettysburg climax and should not be treated as distributed across the full Lincoln corpus yet."],
        "relation_to_koenigsbergian_analysis": "Complicates preservation by adding rebirth: sacrifice does not merely keep the sacred object alive, it makes renewal imaginable.",
    },
    "lincoln-06-providence-theodicy": {
        "persuasive_function": "Places slavery, bloodshed, guilt, and reconciliation under divine judgment rather than partisan triumph.",
        "moral_emotions_activated": ["guilt", "humility", "reverence", "forbearance"],
        "political_actions_authorized": ["accepting war suffering as moral judgment", "reconciliation without denying slavery's offense"],
        "negative_cases": ["Providence language can be doctrinal quotation or rhetorical convention; it should not be used as evidence of private belief without corroboration."],
        "relation_to_koenigsbergian_analysis": "Supports historical-sacral framing and guilt distribution, while limiting enemy-destruction claims through reconciliation.",
    },
    "lincoln-08-sacrificial-death-gift": {
        "persuasive_function": "Converts soldier death into an offering that obligates the living.",
        "moral_emotions_activated": ["mourning", "gratitude", "debt", "devotion"],
        "political_actions_authorized": ["continued dedication", "completion of unfinished work", "preservation of national life"],
        "negative_cases": ["The current evidence sacralizes Union death but does not make killing an end in itself."],
        "relation_to_koenigsbergian_analysis": "Directly supports the sacrificial-body dimension, especially in Gettysburg's battlefield setting.",
    },
}

ABSENCE_ROWS = [
    {
        "absence_id": "lincoln-absence-001",
        "cluster_id": "lincoln-08-sacrificial-death-gift",
        "metaphor_system": "Soldier death as sacrifice / gift",
        "expected_presence": "Actual dead and wounded bodies, families, and material violence implied by battlefield sacrifice.",
        "possible_absence": "Physical suffering and bodily destruction are compressed into solemn offering and devotion.",
        "agents": ["honored dead", "living citizens"],
        "patients": ["dead soldiers", "bereaved families"],
        "beneficiaries": ["nation", "democratic government", "freedom"],
        "sacrificial_subjects": ["Union soldiers"],
        "excluded_agents": ["Confederate soldiers as subjects", "civilian casualties"],
        "displacement_mechanism": "Bodily loss is displaced into national obligation and cemetery consecration.",
        "evidence_mapping_ids": ["lincoln-cmt-002", "lincoln-cmt-004"],
        "claim_boundary": "Systematic absence candidate; requires fuller corpus review before becoming a case-level finding.",
    },
    {
        "absence_id": "lincoln-absence-002",
        "cluster_id": "lincoln-06-providence-theodicy",
        "metaphor_system": "Providential judgment and moral accounting",
        "expected_presence": "Named enslaved people, enslavers, policy mechanisms, military actors, and Black political agency.",
        "possible_absence": "Agency is partly shifted from human institutions into divine judgment and shared national guilt.",
        "agents": ["God", "both parties", "nation"],
        "patients": ["bondsman", "war dead"],
        "beneficiaries": ["reconciled nation", "freedom as moral horizon"],
        "sacrificial_subjects": ["enslaved people", "soldiers"],
        "excluded_agents": ["Black soldiers and activists", "specific enslavers", "military perpetrators"],
        "displacement_mechanism": "Providential grammar can widen guilt but also blur differentiated human agency.",
        "evidence_mapping_ids": ["lincoln-cmt-007", "lincoln-cmt-008", "lincoln-cmt-009"],
        "claim_boundary": "Interpretive caution, not a claim that Lincoln intentionally suppressed agency.",
    },
    {
        "absence_id": "lincoln-absence-003",
        "cluster_id": "lincoln-01-body-organism",
        "metaphor_system": "Nation or government as living organism",
        "expected_presence": "Specific political antagonists, social conflicts, and institutional choices that threaten national life.",
        "possible_absence": "The body-politic frame can make political conflict appear as life/death pressure on the collective body.",
        "agents": ["we", "citizens"],
        "patients": ["nation", "government of the people"],
        "beneficiaries": ["republic", "democratic government"],
        "sacrificial_subjects": ["citizens asked to preserve the polity"],
        "excluded_agents": ["named opponents", "excluded populations outside the citizen 'we'"],
        "displacement_mechanism": "Conflict is condensed into organism survival rather than social plurality.",
        "evidence_mapping_ids": ["lincoln-cmt-001", "lincoln-cmt-006"],
        "claim_boundary": "Useful for rhetorical analysis; not by itself evidence of coercive policy.",
    },
]


def load_mappings(case_id: str) -> list[dict[str, Any]]:
    data = read_json(cmt_mappings_path_for(case_id), {}) or {}
    return list(iter_cmt_mappings(data))


def doc_lookup(case_id: str) -> dict[str, dict[str, Any]]:
    return {document_id(doc): doc for doc in documents(case_id)}


def grouped_by_cluster(mappings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for mapping in mappings:
        cluster_id = str(mapping.get("cluster_id") or "")
        if cluster_id:
            grouped.setdefault(cluster_id, []).append(mapping)
    return grouped


def unique_values(items: list[dict[str, Any]], key: str) -> list[str]:
    values: set[str] = set()
    for item in items:
        value = item.get(key)
        if isinstance(value, list):
            values.update(str(entry) for entry in value if entry not in (None, ""))
        elif value not in (None, ""):
            values.add(str(value))
    return sorted(values)


def build_critical(case_id: str, generated_at: str, mappings: list[dict[str, Any]]) -> dict[str, Any]:
    clusters = grouped_by_cluster(mappings)
    profiles = []
    for cluster_id, items in sorted(clusters.items()):
        notes = LINCOLN_CLUSTER_NOTES.get(cluster_id, {})
        profiles.append(
            {
                "cluster_id": cluster_id,
                "mapping_ids": unique_values(items, "mapping_id"),
                "source_domains": sorted(
                    set(unique_values(items, "source_domain_primary"))
                    | set(unique_values(items, "source_domain_secondary"))
                ),
                "target_domains": unique_values(items, "target_domain"),
                "major_expressions": unique_values(items, "expression"),
                "corpus_distribution": {
                    "mapping_count": len(items),
                    "documents": unique_values(items, "document_id"),
                    "periods": unique_values(items, "diachronic_stage"),
                    "rhetorical_salience": unique_values(items, "rhetorical_salience"),
                },
                "rhetorical_contexts": unique_values(items, "rhetorical_functions"),
                "persuasive_function": notes.get("persuasive_function", "Pending fuller interpretive review."),
                "moral_emotions_activated": notes.get("moral_emotions_activated", []),
                "political_actions_authorized": notes.get("political_actions_authorized", []),
                "rival_readings": unique_values(items, "rival_reading"),
                "negative_cases": notes.get("negative_cases", []),
                "relation_to_koenigsbergian_analysis": notes.get(
                    "relation_to_koenigsbergian_analysis", "Pending support synthesis."
                ),
                "evidence_status": "provisional-cmt-backed",
            }
        )
    return {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft",
        "source": str(cmt_mappings_path_for(case_id).relative_to(case_dir(case_id))),
        "cluster_profiles": profiles,
    }


def build_rhetorical(case_id: str, generated_at: str, mappings: list[dict[str, Any]]) -> dict[str, Any]:
    docs = doc_lookup(case_id)
    contexts = []
    for mapping in mappings:
        doc_id = str(mapping.get("document_id") or "")
        doc = docs.get(doc_id, {})
        context = LINCOLN_DOCUMENT_CONTEXT.get(doc_id, {})
        contexts.append(
            {
                "mapping_id": mapping.get("mapping_id"),
                "document_id": doc_id,
                "sentence_id": mapping.get("sentence_id"),
                "date": doc.get("date"),
                "period": doc.get("period"),
                "audience": context.get("audience"),
                "occasion": context.get("occasion"),
                "genre": context.get("genre") or doc.get("genre") or doc.get("register"),
                "rhetorical_action": context.get("rhetorical_action"),
                "emotional_posture": context.get("emotional_posture"),
                "agency_structure": context.get("agency_structure", {}),
                "rhetorical_salience": mapping.get("rhetorical_salience"),
                "rhetorical_functions": mapping.get("rhetorical_functions", []),
                "evidence_span": mapping.get("evidence_span"),
                "claim_boundary": "Genre-sensitive interpretation; do not aggregate as frequency without document/register context.",
            }
        )
    return {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft",
        "contexts": contexts,
    }


def build_absence(case_id: str, generated_at: str) -> dict[str, Any]:
    return {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft",
        "method_note": "Absence rows state what would count as presence, what appears muted, and which CMT evidence motivates the review question.",
        "matrix": ABSENCE_ROWS,
    }


def md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    if not rows:
        return "_No rows._"
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def write_markdown(case_id: str, critical: dict[str, Any], rhetorical: dict[str, Any], absence: dict[str, Any]) -> None:
    analysis_dir = case_dir(case_id) / "analysis"
    profiles = critical["cluster_profiles"]
    critical_lines = [
        f"# Critical Metaphor Analysis: {case_id}",
        "",
        "Status: draft, CMT-backed interpretive layer.",
        "",
    ]
    for profile in profiles:
        critical_lines.extend(
            [
                f"## {profile['cluster_id']}",
                "",
                f"Mapping IDs: {', '.join(profile['mapping_ids'])}",
                "",
                f"Persuasive function: {profile['persuasive_function']}",
                "",
                f"Relation to Koenigsbergian analysis: {profile['relation_to_koenigsbergian_analysis']}",
                "",
                "Rival readings:",
                "",
                *[f"- {item}" for item in profile["rival_readings"]],
                "",
                "Negative cases:",
                "",
                *[f"- {item}" for item in profile["negative_cases"]],
                "",
            ]
        )
    (analysis_dir / "critical-metaphor-analysis.md").write_text("\n".join(critical_lines), encoding="utf-8")

    contexts = rhetorical["contexts"]
    rhetorical_md = f"""# Rhetorical Genre Analysis: {case_id}

Status: draft, CMT-backed rhetorical context layer.

{md_table(contexts, ["mapping_id", "document_id", "genre", "rhetorical_salience", "emotional_posture", "rhetorical_action"])}

These rows keep public address, ceremonial address, and inaugural address
claims separate. Genre-sensitive claims should cite mapping IDs and document
contexts rather than treating every mapping as interchangeable evidence.
"""
    (analysis_dir / "rhetorical-genre-analysis.md").write_text(rhetorical_md, encoding="utf-8")

    absence_md = f"""# Absence And Agency Analysis: {case_id}

Status: draft, systematic absence matrix.

{md_table(absence["matrix"], ["absence_id", "cluster_id", "expected_presence", "possible_absence", "displacement_mechanism", "claim_boundary"])}

Absence claims are review questions until fuller annotation and historical
corroboration show that an expected presence is systematically muted rather
than merely outside the current sample.
"""
    (analysis_dir / "absence-agency-analysis.md").write_text(absence_md, encoding="utf-8")


def build_case(case_id: str) -> dict[str, Any]:
    generated_at = now_iso()
    mappings = load_mappings(case_id)
    critical = build_critical(case_id, generated_at, mappings)
    rhetorical = build_rhetorical(case_id, generated_at, mappings)
    absence = build_absence(case_id, generated_at)
    analysis_dir = case_dir(case_id) / "analysis"
    write_json(analysis_dir / "critical-metaphor-analysis.json", critical)
    write_json(analysis_dir / "rhetorical-genre-analysis.json", rhetorical)
    write_json(analysis_dir / "absence-agency-analysis.json", absence)
    write_markdown(case_id, critical, rhetorical, absence)
    return {
        "case_id": case_id,
        "critical_profiles": len(critical["cluster_profiles"]),
        "rhetorical_contexts": len(rhetorical["contexts"]),
        "absence_rows": len(absence["matrix"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    args = parser.parse_args()

    for case_id in case_ids(args.case_id):
        result = build_case(case_id)
        print(
            f"{case_id}: built {result['critical_profiles']} cluster profile(s), "
            f"{result['rhetorical_contexts']} rhetorical context(s), "
            f"and {result['absence_rows']} absence row(s)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
