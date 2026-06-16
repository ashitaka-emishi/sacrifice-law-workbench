#!/usr/bin/env python3
"""Rebuild x-case comparison protocol and guarded synthesis artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pipeline_common import ROOT, now_iso, read_json, write_json

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


def lincoln_support() -> dict[str, Any]:
    path = ROOT / "cases" / "lincoln" / "analysis" / "support-ratings.json"
    data = read_json(path, {}) or {}
    return {
        "case_id": "lincoln",
        "status": data.get("status", "missing"),
        "support_rating_path": "cases/lincoln/analysis/support-ratings.json",
        "support_synthesis_path": "cases/lincoln/analysis/koenigsbergian-support-synthesis.json",
        "overall_support": data.get("overall_support", {}),
        "case_scores": data.get("case_scores", {}),
        "comparison_ready": bool(data.get("overall_support")),
    }


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
            "guilt_structure": "Shared national guilt and providential judgment, especially in the Second Inaugural.",
            "endpoint": "Reunion, democratic survival, reconciliation, and renewal.",
            "support_rating_path": lincoln["support_rating_path"],
            "support_synthesis_path": lincoln["support_synthesis_path"],
            "claim_boundary": "Lincoln is comparison-ready only as a provisional pilot case; full-corpus review and reliability adjudication remain pending.",
        },
        {
            "case_id": "hitler",
            "case_type": "genocidal-racial-state-violence",
            "status": "pending-case-level-support-rating",
            "support_rating": "pending",
            "claim_boundary": "Do not infer comparison from Lincoln or from starter clusters before Hitler case-level scoring is complete.",
        },
        {
            "case_id": "napoleon",
            "case_type": "imperial-war-mobilization",
            "status": "pending-case-level-support-rating",
            "support_rating": "pending",
            "claim_boundary": "Do not infer comparison from Lincoln or from starter clusters before Napoleon case-level scoring is complete.",
        },
        {
            "case_id": "am-rev",
            "case_type": "revolutionary-founding-violence",
            "status": "pending-case-level-support-rating",
            "support_rating": "pending",
            "claim_boundary": "Do not infer comparison from Lincoln or from starter clusters before American Revolution case-level scoring is complete.",
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


def write_qmd_pages(items: list[dict[str, Any]], protocol_data: dict[str, Any]) -> None:
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
    (qmd_dir / "sacrifice-law-findings.qmd").write_text(
        f"""---
title: "Sacrifice Law Findings"
---

## Current Support Findings

{markdown_table(items, ["case_id", "status", "support_rating", "support_score", "support_rating_path"])}

Only Lincoln currently has a draft case-level support rating. Other cases remain
pending until their annotation, corroboration, and support-rating artifacts are
complete.
""",
        encoding="utf-8",
    )
    (qmd_dir / "x-case-overview.qmd").write_text(
        f"""---
title: "X Case Overview"
---

The x-case layer now has a comparative protocol, moral-equivalence guardrails,
and a draft Lincoln-linked comparison row. Cross-case findings remain draft
until every included case has case-level support ratings and historical
alignment notes.
""",
        encoding="utf-8",
    )


def build() -> dict[str, Any]:
    generated_at = now_iso()
    protocol_data = protocol(generated_at)
    items = comparison_items()
    synthesis_dir = XCASE_DIR / "synthesis"
    protocol_dir = XCASE_DIR / "protocol"
    status_dir = XCASE_DIR / "status"
    validation_dir = XCASE_DIR / "validation"
    for directory in [synthesis_dir, protocol_dir, status_dir, validation_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    write_json(protocol_dir / "comparative-analysis-protocol.json", protocol_data)
    write_protocol_md(protocol_data)
    write_json(
        synthesis_dir / "case-comparison.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
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
    write_json(
        synthesis_dir / "sacrifice-law-findings.json",
        {
            "version": "1.0",
            "case_id": "x-case",
            "generated_at": generated_at,
            "status": "draft",
            "items": [
                {
                    "case_id": item["case_id"],
                    "support_rating": item.get("support_rating"),
                    "support_score": item.get("support_score"),
                    "support_rating_path": item.get("support_rating_path"),
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
            ],
            "dependencies": [
                "cases/lincoln/analysis/support-ratings.json",
                "cases/lincoln/analysis/historical-enactment-alignment.json",
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
    write_qmd_pages(items, protocol_data)
    return {"generated_at": generated_at, "case_rows": len(items), "guardrails": len(GUARDRAILS)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default=None, help="Unused compatibility option")
    parser.parse_args()
    result = build()
    print(
        f"x-case: built comparative protocol with {result['case_rows']} case row(s) "
        f"and {result['guardrails']} guardrail(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
