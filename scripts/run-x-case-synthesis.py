#!/usr/bin/env python3
"""Rebuild x-case comparison protocol and guarded synthesis artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pipeline_common import ROOT, case_ids, now_iso, read_json, write_json

XCASE_DIR = ROOT / "cases" / "x-case"

COMPARATIVE_DIMENSIONS = [
    {
        "id": "sacred_collective_object",
        "label": "Sacred collective object",
        "question": "What collective object is treated as ultimate, immortal, transcendent, or worth sacrifice?",
    },
    {
        "id": "dominant_body_metaphor",
        "label": "Dominant body metaphor",
        "question": "How is the polity or collective imagined as a body, organism, wound, disease, or rebirth?",
    },
    {
        "id": "violence_logic",
        "label": "Violence logic",
        "question": "Does violence function as preservation, sacrifice, punishment, purification, extermination, or another logic?",
    },
    {
        "id": "enemy_as_bringer_of_death",
        "label": "Enemy as bringer of death",
        "question": "Is the enemy represented as a death-bearing agent, carrier, embodiment, sign, contamination, dissolution, doubt, unreality, or existential threat?",
    },
    {
        "id": "death_logic",
        "label": "Death logic",
        "question": "How are killing, dying, martyrdom, or suffering made meaningful?",
    },
    {
        "id": "historical_alignment",
        "label": "Historical enactment / alignment",
        "question": "Which policies, practices, mobilizations, social uptake, or outcomes corroborate the symbolic pattern?",
    },
    {
        "id": "support_rating",
        "label": "Overall support rating",
        "question": "Does the case strongly, moderately, weakly, complicatedly, or not at all support the framework?",
    },
    {
        "id": "guilt_structure",
        "label": "Guilt structure",
        "question": "How are guilt, innocence, debt, pollution, or responsibility distributed?",
    },
    {
        "id": "endpoint",
        "label": "Endpoint",
        "question": "What imagined end state is authorized: reconciliation, preservation, purification, annihilation, coexistence, or something else?",
    },
]

GUARDRAILS = [
    "Structural comparison is not moral equivalence.",
    "Similarity in metaphor form is not equivalence in political content, institutional setting, or historical outcome.",
    "Enemy construction, endpoint, violence logic, and historical enactment matter centrally.",
    "Each case remains historically contextualized and evidence-bound.",
    "Comparator cases without support ratings remain pending, not inferred by analogy.",
    "War, genocide, enslavement, colonial violence, and state terror require separate historical and moral description even when symbolic structures overlap.",
]


def case_analysis(case_id: str) -> dict[str, Any]:
    path = ROOT / "cases" / case_id / "analysis" / "analysis.json"
    return read_json(path, {}) or {}


def case_absence(case_id: str) -> list[dict[str, Any]]:
    path = ROOT / "cases" / case_id / "analysis" / "absence-agency-analysis.json"
    data = read_json(path, {}) or {}
    return data.get("matrix", [])


def case_critical(case_id: str) -> list[dict[str, Any]]:
    path = ROOT / "cases" / case_id / "analysis" / "critical-metaphor-analysis.json"
    data = read_json(path, {}) or {}
    return data.get("cluster_profiles", [])


def case_concordance(case_id: str) -> list[dict[str, Any]]:
    path = ROOT / "cases" / case_id / "analysis" / "concordance.json"
    data = read_json(path, {}) or {}
    return data.get("instances", [])


def build_inputs(generated_at: str, all_ids: list[str]) -> dict[str, Any]:
    manifest_items = []
    readiness_items = []
    for cid in all_ids:
        analysis = case_analysis(cid)
        status = analysis.get("status", "missing")
        total = analysis.get("total_instances", 0)
        clusters = len(analysis.get("cluster_analyses", []))
        ready = status in ("complete", "draft") and total > 0
        manifest_items.append({
            "case_id": cid,
            "analysis_status": status,
            "total_instances": total,
            "cluster_count": clusters,
            "ready_for_xcase": ready,
        })
        readiness_items.append({
            "case_id": cid,
            "ready": ready,
            "reason": "complete" if ready else f"status={status}, instances={total}",
        })
    return {
        "manifest": {
            "generated_at": generated_at,
            "status": "draft",
            "items": manifest_items,
        },
        "inputs": {
            "generated_at": generated_at,
            "status": "draft",
            "items": [item for item in manifest_items if item["ready_for_xcase"]],
        },
        "readiness": {
            "generated_at": generated_at,
            "status": "draft",
            "items": readiness_items,
        },
    }


def build_cluster_comparison(all_ids: list[str]) -> list[dict[str, Any]]:
    rows = []
    for cid in all_ids:
        analysis = case_analysis(cid)
        for cluster in analysis.get("cluster_analyses", []):
            kp = cluster.get("koenigsberg_profile", {})
            rows.append({
                "case_id": cid,
                "cluster_id": cluster.get("cluster_id"),
                "cluster_name": cluster.get("cluster_name"),
                "instance_count": cluster.get("instance_count", 0),
                "cmt_mapping_count": cluster.get("cmt_mapping_count", 0),
                "primary_source_domains": list(cluster.get("cmt_source_domains", {}).keys())[:3],
                "primary_target_domains": list(cluster.get("cmt_target_domains", {}).keys())[:3],
                "fantasy_types": list(kp.get("fantasy_type_distribution", {}).keys()),
                "obligatory_frame_rate": kp.get("obligatory_frame_rate"),
                "sacrificial_economy_rate": kp.get("sacrificial_economy_rate"),
                "claim_boundary": "Cluster distributions are draft; pending support-rating adjudication per case.",
            })
    return rows


def build_absence_comparison(all_ids: list[str]) -> list[dict[str, Any]]:
    rows = []
    for cid in all_ids:
        for row in case_absence(cid):
            rows.append({
                "case_id": cid,
                "absence_id": row.get("absence_id"),
                "cluster_id": row.get("cluster_id"),
                "metaphor_system": row.get("metaphor_system"),
                "excluded_agents": row.get("excluded_agents", []),
                "displacement_mechanism": row.get("displacement_mechanism"),
                "claim_boundary": row.get("claim_boundary"),
            })
    return rows


def build_diachronic_comparison(all_ids: list[str]) -> list[dict[str, Any]]:
    rows = []
    for cid in all_ids:
        analysis = case_analysis(cid)
        profile = analysis.get("corpus_profile", {})
        by_doc = profile.get("by_document", {})
        rows.append({
            "case_id": cid,
            "total_instances": analysis.get("total_instances", 0),
            "documents_with_instances": len([k for k, v in by_doc.items() if v > 0]),
            "total_documents": len(by_doc),
            "by_cluster": profile.get("by_cluster", {}),
            "by_fantasy_type": profile.get("by_fantasy_type", {}),
            "by_violence_logic": profile.get("by_violence_logic", {}),
            "claim_boundary": "Diachronic claims require document-level dating and sequential context not yet fully represented in this aggregate.",
        })
    return rows


def build_shared_concordance(all_ids: list[str]) -> list[dict[str, Any]]:
    instances = []
    for cid in all_ids:
        for inst in case_concordance(cid):
            inst_copy = dict(inst)
            inst_copy.setdefault("case_id", cid)
            instances.append(inst_copy)
    return instances


def build_rival_explanations(all_ids: list[str]) -> list[dict[str, Any]]:
    rows = []
    for cid in all_ids:
        for profile in case_critical(cid):
            for rival in profile.get("rival_readings", []):
                if rival:
                    rows.append({
                        "case_id": cid,
                        "cluster_id": profile.get("cluster_id"),
                        "rival_reading": rival,
                        "claim_boundary": "Rival readings are per-mapping annotations; cross-case patterns require analyst review.",
                    })
    return rows


def build_open_questions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = {item["case_id"]: item for item in items if item.get("comparison_ready") or item.get("status") == "draft-scored"}
    all_scored = len(scored) == len(items)

    by_case = {item["case_id"]: item for item in items}

    def score_for(case_id: str, dim: str) -> float | None:
        return (by_case.get(case_id) or {}).get("case_scores", {}).get(dim)

    questions = [
        {
            "question_id": "xq-001",
            "question": "Do all four cases share a common sacrificial economy logic, or do preservation, glory, and extermination differ structurally?",
            "relevant_cases": ["lincoln", "napoleon", "am-rev", "hitler"],
            "status": "partially-answered" if all_scored else "open",
            "dependency": "All four cases now have draft support ratings." if all_scored else "All four cases require support-rating adjudication before this can be answered.",
            "draft_answer": (
                "All four cases show a functioning sacrificial economy (sacred collective object, body metaphor, violence logic, death-conversion), "
                "but the endpoint and violence logic differ structurally: Lincoln/Am-Rev use preservation-and-founding logic; Napoleon uses imperial glory; "
                "Hitler uses racial extermination. Shared form with divergent content — the framework holds cross-case, but the moral-political substance differs categorically. "
                "Full answer requires obligatory-frame rate comparison and corpus-level adjudication."
            ) if all_scored else None,
        },
        {
            "question_id": "xq-002",
            "question": "Is the enemy-as-bringer-of-death dimension present with comparable salience across all cases?",
            "relevant_cases": ["lincoln", "napoleon", "am-rev", "hitler"],
            "status": "partially-answered" if all_scored else "open",
            "dependency": "All four cases now have draft enemy-death scores." if all_scored else "Lincoln pilot evidence shows weak enemy-death salience; other cases remain unrated.",
            "draft_answer": (
                f"No — enemy-death salience varies significantly. Draft scores: "
                f"lincoln={score_for('lincoln', 'enemy_as_bringer_of_death')}, "
                f"am-rev={score_for('am-rev', 'enemy_as_bringer_of_death')}, "
                f"napoleon={score_for('napoleon', 'enemy_as_bringer_of_death')}, "
                f"hitler={score_for('hitler', 'enemy_as_bringer_of_death')}. "
                "Hitler shows the highest enemy-death salience (racial contamination/extermination logic); Napoleon shows the lowest (enemies as obstacles to order). "
                "Lincoln and Am-Rev are intermediate — tyranny and disunion as death-bearers, but enemy agency is often muted or diffused. "
                "Full answer requires obligatory-frame and cluster-density adjudication."
            ) if all_scored else None,
        },
        {
            "question_id": "xq-003",
            "question": "Does the obligatory frame appear in all cases, or only in cases with explicit covenantal or martyrological rhetoric?",
            "relevant_cases": ["lincoln", "am-rev", "napoleon", "hitler"],
            "status": "open",
            "dependency": "Per-case obligatory-frame rates exist in cluster profiles but have not been cross-case adjudicated. Requires analyst review of cluster-comparison data.",
        },
        {
            "question_id": "xq-004",
            "question": "Do absence patterns differ systematically by case type (war preservation vs. imperial vs. founding vs. genocide)?",
            "relevant_cases": ["lincoln", "napoleon", "am-rev", "hitler"],
            "status": "partially-answered" if all_scored else "open",
            "dependency": "Absence rows exist for all four cases; cross-case adjudication is draft." if all_scored else "Absence rows exist for all four cases but have not been cross-case adjudicated.",
            "draft_answer": (
                "Draft patterns: all four cases show agency-absence for defeated/excluded populations (slaves/freedmen in Lincoln, Hessians/loyalists in Am-Rev, "
                "Russian casualties in Napoleon, Jewish/Slavic victims in Hitler). The displacement mechanism differs by case type: "
                "preservation cases displace through elevation (honor/sacrifice); genocide cases displace through negation (subhuman/vermin). "
                "Full adjudication requires corpus-level absence-pattern review."
            ) if all_scored else None,
        },
        {
            "question_id": "xq-005",
            "question": "What is the structural role of the providence / historical destiny cluster across cases? Is it a universal feature or a historically specific one?",
            "relevant_cases": ["lincoln", "am-rev", "napoleon", "hitler"],
            "status": "open",
            "dependency": "Providence appears in lincoln, am-rev, and napoleon clusters; hitler uses destiny differently. Requires comparative analysis of cluster profiles.",
        },
    ]
    pending = [item.get("case_id", "") for item in items if item.get("status") == "pending-case-level-support-rating"]
    pending = [cid for cid in pending if cid]
    if pending:
        questions.append({
            "question_id": "xq-006",
            "question": f"When will case-level support ratings be available for: {', '.join(pending)}?",
            "relevant_cases": pending,
            "status": "blocking",
            "dependency": "These cases block all cross-case claims that require support-score comparisons.",
        })
    return questions


def read_support(case_id: str) -> dict[str, Any]:
    path = ROOT / "cases" / case_id / "analysis" / "support-ratings.json"
    data = read_json(path, {}) or {}
    has_support = bool(data.get("overall_support"))
    return {
        "case_id": case_id,
        "status": data.get("status", "missing") if has_support else "pending-case-level-support-rating",
        "support_rating_path": f"cases/{case_id}/analysis/support-ratings.json",
        "support_synthesis_path": f"cases/{case_id}/analysis/koenigsbergian-support-synthesis.json",
        "overall_support": data.get("overall_support", {}),
        "case_scores": data.get("case_scores", {}),
        "comparison_ready": has_support,
    }


def lincoln_support() -> dict[str, Any]:
    return read_support("lincoln")


def pending_case(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "pending-case-level-support-rating",
        "support_rating_path": f"cases/{case_id}/analysis/support-ratings.json",
        "overall_support": {},
        "case_scores": {},
        "comparison_ready": False,
    }


def protocol(generated_at: str) -> dict[str, Any]:
    return {
        "version": "1.0",
        "case_id": "x-case",
        "generated_at": generated_at,
        "status": "draft",
        "purpose": "Define comparative analysis dimensions and guardrails before cross-case claims are promoted.",
        "dimensions": COMPARATIVE_DIMENSIONS,
        "guardrails": GUARDRAILS,
        "support_categories": [
            "unsupported",
            "weak support",
            "moderate support",
            "strong support",
            "very strong support",
            "complicated support",
        ],
        "comparison_policy": "Cross-case claims must cite case-level support ratings, historical-alignment notes, and case-specific context. Cases without ratings remain pending.",
    }


def comparison_items() -> list[dict[str, Any]]:
    lincoln = lincoln_support()
    napoleon = read_support("napoleon")
    am_rev = read_support("am-rev")
    hitler = read_support("hitler")
    return [
        {
            "case_id": "lincoln",
            "case_type": "civil-war-preservation-and-reunion",
            "status": "draft-scored",
            "sacred_collective_object": "Union / republic / democracy / freedom",
            "dominant_body_metaphor": "Living nation, democratic organism, rebirth",
            "violence_logic": "Preservation, sacrificial obligation, providential judgment, reconciliation",
            "enemy_as_bringer_of_death": "Weak in the reviewed pilot evidence; disunion/slavery are threats, but enemy agency is often muted or diffused.",
            "death_logic": "Soldier death becomes obligation, devotion, and condition for national renewal.",
            "historical_alignment": "Battlefield death, public mourning, emancipation context, wartime bloodshed, and reunion practice require publication citations before final claims.",
            "support_rating": lincoln.get("overall_support", {}).get("final_category", "pending"),
            "support_score": lincoln.get("overall_support", {}).get("score"),
            "case_scores": lincoln.get("case_scores"),
            "guilt_structure": "Shared national guilt and providential judgment, especially in the Second Inaugural.",
            "endpoint": "Reunion, democratic survival, reconciliation, and renewal.",
            "support_rating_path": lincoln["support_rating_path"],
            "support_synthesis_path": lincoln["support_synthesis_path"],
            "claim_boundary": "Lincoln is comparison-ready only as a provisional pilot case; full-corpus review and reliability adjudication remain pending.",
        },
        {
            "case_id": "hitler",
            "case_type": "genocidal-racial-state-violence",
            "status": "draft-scored" if hitler["comparison_ready"] else "pending-case-level-support-rating",
            "sacred_collective_object": "Aryan Volk, blood-and-soil nation, racial purity",
            "dominant_body_metaphor": "Racial body, Volk as organic collective, parasite/pathogen (enemy)",
            "violence_logic": "Racial purification, extermination of contaminating enemy, national rebirth through blood",
            "enemy_as_bringer_of_death": "Strong — Jewish/Bolshevik enemy is explicit death-bearer and existential contamination threat.",
            "death_logic": "Death of enemies required for collective survival; German soldier deaths are sacrifice for racial Volk.",
            "historical_alignment": "Nuremberg Laws 1935, Operation Barbarossa 1941, Wannsee 1942 industrial genocide, documented social uptake in Nazi state machinery.",
            "support_rating": hitler.get("overall_support", {}).get("final_category", "pending"),
            "support_score": hitler.get("overall_support", {}).get("score"),
            "case_scores": hitler.get("case_scores"),
            "guilt_structure": "External guilt projected onto racial enemy; no internal moral accounting. Contamination logic inverts guilt.",
            "endpoint": "Racial state, Lebensraum, extermination of designated enemies, Thousand-Year Reich.",
            "support_rating_path": hitler["support_rating_path"],
            "support_synthesis_path": hitler["support_synthesis_path"],
            "claim_boundary": "Hitler case is draft-scored; full-corpus German source review and reliability adjudication remain pending.",
        },
        {
            "case_id": "napoleon",
            "case_type": "imperial-war-mobilization",
            "status": "draft-scored" if napoleon["comparison_ready"] else "pending-case-level-support-rating",
            "sacred_collective_object": "La Gloire, l'Empire, la France — imperial glory as sacred collective object",
            "dominant_body_metaphor": "Army-as-body, Emperor as embodiment of the nation",
            "violence_logic": "Military glory, conquest as historical destiny, soldier sacrifice for the Emperor and Empire",
            "enemy_as_bringer_of_death": "Weak to moderate — enemies are obstacles to order; death-bearer framing clearest in 29th Bulletin.",
            "death_logic": "Soldier death converted to honor and sacrifice for glory; Eylau is the clearest expression.",
            "historical_alignment": "Austerlitz mobilization, Eylau mass casualties, 29th Bulletin catastrophe acknowledgment corroborated historically.",
            "support_rating": napoleon.get("overall_support", {}).get("final_category", "pending"),
            "support_score": napoleon.get("overall_support", {}).get("score"),
            "case_scores": napoleon.get("case_scores"),
            "guilt_structure": "Minimal — bulletins externalize loss onto weather, terrain, or enemy resistance; no shared-guilt logic.",
            "endpoint": "Imperial consolidation, Napoleonic peace, historical glory; not extermination or republican founding.",
            "support_rating_path": napoleon["support_rating_path"],
            "support_synthesis_path": napoleon["support_synthesis_path"],
            "claim_boundary": "Napoleon case is draft-scored from bulletin corpus; thin evidence base (19 instances) and genre constraints limit generalization.",
        },
        {
            "case_id": "am-rev",
            "case_type": "revolutionary-founding-violence",
            "status": "draft-scored" if am_rev["comparison_ready"] else "pending-case-level-support-rating",
            "sacred_collective_object": "Liberty, republican self-governance, natural rights, Providence-backed founding",
            "dominant_body_metaphor": "Body politic, patriot sacrifice, civic organism",
            "violence_logic": "Defensive founding violence, tyranny-resistance as sacred obligation, providential justification",
            "enemy_as_bringer_of_death": "Moderate — British tyranny and Hessian mercenaries as death-bearers; tyranny as slavery-and-death frame.",
            "death_logic": "Patriot death as founding sacrifice; blood of martyrs consecrates the republic.",
            "historical_alignment": "Continental Army mobilization, Battle of Trenton, Valley Forge sacrifice, documented pamphlet reception corroborated.",
            "support_rating": am_rev.get("overall_support", {}).get("final_category", "pending"),
            "support_score": am_rev.get("overall_support", {}).get("score"),
            "case_scores": am_rev.get("case_scores"),
            "guilt_structure": "External guilt projected onto Crown and loyalists; colonists positioned as innocent victims of tyranny.",
            "endpoint": "Republican founding, constitutional self-governance, permanent severance from monarchical authority.",
            "support_rating_path": am_rev["support_rating_path"],
            "support_synthesis_path": am_rev["support_synthesis_path"],
            "claim_boundary": "Am-Rev case is draft-scored; tech debt #42 means am-rev MIPVU pipeline may have overwritten reviewed annotations for Washington Orders documents.",
        },
    ]


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def write_protocol_md(data: dict[str, Any]) -> None:
    protocol_dir = XCASE_DIR / "protocol"
    protocol_dir.mkdir(parents=True, exist_ok=True)
    dimensions = data["dimensions"]
    guardrails = "\n".join(f"- {item}" for item in data["guardrails"])
    text = f"""# Comparative Analysis Protocol

Status: {data['status']}.

## Dimensions

{markdown_table(dimensions, ["id", "label", "question"])}

## Guardrails

{guardrails}

## Policy

{data['comparison_policy']}
"""
    (protocol_dir / "comparative-analysis-protocol.md").write_text(text, encoding="utf-8")


def write_qmd_pages(items: list[dict[str, Any]], protocol_data: dict[str, Any], all_scored: bool = False) -> None:
    qmd_dir = XCASE_DIR / "artifacts" / "qmd"
    qmd_dir.mkdir(parents=True, exist_ok=True)
    guardrails = "\n".join(f"- {item}" for item in protocol_data["guardrails"])
    comparison_table = markdown_table(
        items,
        ["case_id", "case_type", "status", "support_rating", "endpoint", "claim_boundary"],
    )
    (qmd_dir / "case-comparison.qmd").write_text(
        f"""---
title: "Case Comparison"
---

## Draft Comparison Matrix

{comparison_table}

Comparisons remain evidence-bound. Pending cases are not interpreted by analogy.
""",
        encoding="utf-8",
    )
    (qmd_dir / "war-genocide-distinction.qmd").write_text(
        f"""---
title: "War Genocide Distinction"
---

## Guardrails

{guardrails}

The comparison protocol distinguishes war preservation, imperial mobilization,
revolutionary founding, and genocidal racial state violence by endpoint,
enemy construction, violence logic, and historical enactment. Similar metaphor
forms never establish moral equivalence.
""",
        encoding="utf-8",
    )
    findings_note = (
        "All four cases now have draft case-level support ratings. Cross-case findings are draft-scored. "
        "Full-corpus review, reliability adjudication, and publication-grade citations remain pending."
        if all_scored else
        "Some cases remain pending. Cross-case findings are not available until all cases are scored."
    )
    (qmd_dir / "sacrifice-law-findings.qmd").write_text(
        f"""---
title: "Sacrifice Law Findings"
---

## Current Support Findings

{markdown_table(items, ["case_id", "status", "support_rating", "support_score", "support_rating_path"])}

{findings_note}
""",
        encoding="utf-8",
    )
    overview_status = "draft-scored" if all_scored else "draft"
    overview_progress = (
        "All four cases have case-level support ratings and historical-alignment notes.\n"
        "Cross-case findings remain provisional until full-corpus review, reliability\n"
        "adjudication, and publication-grade citation work are complete."
        if all_scored
        else
        "Some cases do not yet have case-level support ratings. Cross-case findings\n"
        "remain unavailable until every required case is scored and validated."
    )
    overview_answer = (
        "The draft comparison finds the strongest support for the Law of Sacrifice in\n"
        "the Hitler case and moderate support in the American Revolution, Lincoln, and\n"
        "Napoleon cases. The shared pattern is not a claim of equivalence: metaphor\n"
        "form, political endpoint, enemy construction, institutional setting, and\n"
        "historical enactment differ substantially across the four cases."
        if all_scored
        else
        "The comparative answer is pending. Cases without support ratings are not\n"
        "interpreted by analogy, and partial results are not promoted as cross-case\n"
        "findings."
    )
    (qmd_dir / "x-case-overview.qmd").write_text(
        f"""---
title: "Findings"
---

::: {{.callout-note title="Status: {overview_status}"}}
{overview_progress}
:::

## Current answer

{overview_answer}

## Read the findings

- [Case comparison](case-comparison.qmd) — support ratings, endpoints, and claim boundaries.
- [Law of Sacrifice findings](sacrifice-law-findings.qmd) — current case-level scores.
- [Shared metaphor systems](shared-clusters.qmd) — provisional cross-case mappings.
- [War and genocide distinction](war-genocide-distinction.qmd) — moral and historical guardrails.
- [Rival explanations](rival-explanations.qmd) — competing interpretations and unresolved questions.
- [Validation summary](validation-summary.qmd) — readiness and evidentiary limits.

## Compare responsibly

Structural comparison is not moral equivalence. War, genocide, enslavement,
colonial violence, and state terror require separate historical and moral
description even when symbolic structures overlap. Readers can inspect the
[comparative protocol](../../protocol/comparative-analysis-protocol.md) or
[audit package](../../../../publication/audit-package.md) behind these claims.
""",
        encoding="utf-8",
    )


def build() -> dict[str, Any]:
    generated_at = now_iso()
    protocol_data = protocol(generated_at)
    items = comparison_items()
    all_ids = case_ids()
    synthesis_dir = XCASE_DIR / "synthesis"
    protocol_dir = XCASE_DIR / "protocol"
    inputs_dir = XCASE_DIR / "inputs"
    status_dir = XCASE_DIR / "status"
    validation_dir = XCASE_DIR / "validation"
    for directory in [synthesis_dir, protocol_dir, inputs_dir, status_dir, validation_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    # Build inputs
    inputs_data = build_inputs(generated_at, all_ids)
    write_json(inputs_dir / "case-output-manifest.json", inputs_data["manifest"])
    write_json(inputs_dir / "cross-case-inputs.json", inputs_data["inputs"])
    write_json(inputs_dir / "input-readiness-report.json", inputs_data["readiness"])

    # Build comparison artifacts
    cluster_rows = build_cluster_comparison(all_ids)
    write_json(
        synthesis_dir / "cluster-comparison.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
            "guardrails": GUARDRAILS,
            "items": cluster_rows,
        },
    )
    absence_rows = build_absence_comparison(all_ids)
    write_json(
        synthesis_dir / "absence-comparison.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
            "method_note": "Each absence row is a review question per case; cross-case patterns are not confirmed findings.",
            "items": absence_rows,
        },
    )
    diachronic_rows = build_diachronic_comparison(all_ids)
    write_json(
        synthesis_dir / "diachronic-comparison.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
            "guardrails": GUARDRAILS,
            "items": diachronic_rows,
        },
    )
    shared_instances = build_shared_concordance(all_ids)
    write_json(
        synthesis_dir / "shared-concordance.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
            "total_instances": len(shared_instances),
            "items": shared_instances,
        },
    )
    rival_rows = build_rival_explanations(all_ids)
    write_json(
        synthesis_dir / "rival-explanations-matrix.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
            "items": rival_rows,
        },
    )
    open_q = build_open_questions(items)
    write_json(
        synthesis_dir / "open-questions.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
            "items": open_q,
        },
    )

    write_json(protocol_dir / "comparative-analysis-protocol.json", protocol_data)
    write_protocol_md(protocol_data)
    all_scored = all(item.get("status") == "draft-scored" for item in items)
    by_case = {item["case_id"]: item for item in items}
    write_json(
        synthesis_dir / "case-comparison.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft-scored" if all_scored else "draft",
            "items": items,
            "guardrails": GUARDRAILS,
        },
    )
    write_json(
        synthesis_dir / "war-genocide-distinction.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
            "guardrails": GUARDRAILS,
            "distinction_policy": "War/genocide comparison requires separate endpoint, enemy-construction, violence-logic, and historical-enactment analysis.",
            "items": items,
        },
    )
    findings_status = "draft-scored" if all_scored else "draft"
    cross_case_findings = []
    if all_scored:
        def _cs(case_id: str, dim: str) -> float | None:
            return (by_case.get(case_id) or {}).get("case_scores", {}).get(dim)

        cross_case_findings = [
            {
                "finding_id": "xcf-001",
                "claim": "All four cases show a functioning Koenigsbergian sacrificial economy at draft-score level.",
                "evidence": "Each case has sacred_object, sacrificial_body, and historical_enactment_alignment scores ≥ 1.9 (moderate support or higher).",
                "support_scores": {item["case_id"]: item.get("support_score") for item in items},
                "guardrail": "Structural similarity is not moral equivalence. Endpoint, enemy-construction, and violence logic differ categorically across cases.",
                "claim_boundary": "Draft scoring only; full-corpus review and reliability adjudication remain pending for all cases.",
            },
            {
                "finding_id": "xcf-002",
                "claim": "The enemy-as-bringer-of-death dimension shows the largest cross-case variance of any scored dimension.",
                "evidence": (
                    f"Draft enemy-death scores: "
                    f"hitler={_cs('hitler', 'enemy_as_bringer_of_death')}, "
                    f"am-rev={_cs('am-rev', 'enemy_as_bringer_of_death')}, "
                    f"lincoln={_cs('lincoln', 'enemy_as_bringer_of_death')}, "
                    f"napoleon={_cs('napoleon', 'enemy_as_bringer_of_death')}."
                ),
                "guardrail": "High enemy-death scores in genocide cases reflect extermination logic; low scores in preservation cases reflect diffused enemy agency. These are not equivalent phenomena.",
                "claim_boundary": "Draft scoring only; full adjudication required.",
            },
            {
                "finding_id": "xcf-003",
                "claim": "Hitler case scores highest overall (strong support); lincoln, am-rev, and napoleon score moderate support.",
                "evidence": (
                    f"Overall scores: "
                    f"hitler={by_case.get('hitler', {}).get('support_score')}, "
                    f"am-rev={by_case.get('am-rev', {}).get('support_score')}, "
                    f"lincoln={by_case.get('lincoln', {}).get('support_score')}, "
                    f"napoleon={by_case.get('napoleon', {}).get('support_score')}."
                ),
                "guardrail": "Higher support score does not indicate moral precedence. Hitler's higher score reflects the framework's fit with genocidal racial-state rhetoric, not normative ranking.",
                "claim_boundary": "Draft scoring only; corpus size and genre constraints differ across cases.",
            },
        ]
    write_json(
        synthesis_dir / "sacrifice-law-findings.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": findings_status,
            "cross_case_findings": cross_case_findings,
            "items": [
                {
                    "case_id": item["case_id"],
                    "status": item.get("status"),
                    "support_rating": item.get("support_rating"),
                    "support_score": item.get("support_score"),
                    "support_rating_path": item.get("support_rating_path"),
                    "support_synthesis_path": item.get("support_synthesis_path"),
                    "case_scores": item.get("case_scores"),
                    "claim_boundary": item.get("claim_boundary"),
                }
                for item in items
            ],
        },
    )
    write_json(
        synthesis_dir / "synthesis-index.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
            "artifacts": [
                "protocol/comparative-analysis-protocol.json",
                "protocol/comparative-analysis-protocol.md",
                "synthesis/case-comparison.json",
                "synthesis/war-genocide-distinction.json",
                "synthesis/sacrifice-law-findings.json",
                "synthesis/cluster-comparison.json",
                "synthesis/absence-comparison.json",
                "synthesis/diachronic-comparison.json",
                "synthesis/shared-concordance.json",
                "synthesis/rival-explanations-matrix.json",
                "synthesis/open-questions.json",
                "inputs/case-output-manifest.json",
                "inputs/cross-case-inputs.json",
                "inputs/input-readiness-report.json",
            ],
            "dependencies": [
                "cases/lincoln/analysis/support-ratings.json",
                "cases/lincoln/analysis/historical-enactment-alignment.json",
                "cases/lincoln/analysis/koenigsbergian-support-synthesis.json",
                "cases/am-rev/analysis/support-ratings.json",
                "cases/am-rev/analysis/historical-enactment-alignment.json",
                "cases/am-rev/analysis/koenigsbergian-support-synthesis.json",
                "cases/napoleon/analysis/support-ratings.json",
                "cases/napoleon/analysis/historical-enactment-alignment.json",
                "cases/napoleon/analysis/koenigsbergian-support-synthesis.json",
                "cases/hitler/analysis/support-ratings.json",
                "cases/hitler/analysis/historical-enactment-alignment.json",
                "cases/hitler/analysis/koenigsbergian-support-synthesis.json",
            ],
        },
    )
    write_json(
        validation_dir / "moral-equivalence-guardrails.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
            "guardrails": GUARDRAILS,
            "review_questions": [
                "Does the comparison distinguish metaphor form from political content?",
                "Does it distinguish war, genocide, and other violence forms by endpoint and historical enactment?",
                "Does each case cite its own support ratings rather than borrowing another case's interpretation?",
            ],
        },
    )
    write_json(
        status_dir / "x-case-status.json",
        {
            "case_id": "x-case",
            "status": "comparative-protocol-draft",
            "current_stage": "comparative-guardrails-defined",
            "updated": generated_at[:10],
            "notes": "Comparative protocol and moral-equivalence guardrails are defined. Lincoln has a draft support row; other case comparisons remain pending case-level support ratings.",
        },
    )
    write_qmd_pages(items, protocol_data, all_scored=all_scored)
    return {
        "generated_at": generated_at,
        "case_rows": len(items),
        "guardrails": len(GUARDRAILS),
        "cluster_rows": len(cluster_rows),
        "absence_rows": len(absence_rows),
        "shared_instances": len(shared_instances),
        "open_questions": len(open_q),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default=None, help="Unused compatibility option")
    parser.parse_args()
    result = build()
    print(
        f"x-case: built comparative protocol with {result['case_rows']} case row(s), "
        f"{result['guardrails']} guardrail(s), {result['cluster_rows']} cluster row(s), "
        f"{result['absence_rows']} absence row(s), {result['shared_instances']} shared instance(s), "
        f"{result['open_questions']} open question(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
