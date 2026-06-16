#!/usr/bin/env python3
"""Build historical alignment notes, support ratings, and synthesis."""
from __future__ import annotations

import argparse
import csv
from math import prod
from pathlib import Path
from typing import Any

from pipeline_common import case_dir, case_ids, now_iso, write_json

DIMENSIONS = [
    "sacred_object",
    "sacrificial_body",
    "enemy_as_bringer_of_death",
    "historical_enactment_alignment",
]

LINCOLN_HISTORICAL_NOTES = [
    {
        "note_id": "lincoln-hist-001",
        "dimension": "historical_enactment_alignment",
        "topic": "Gettysburg battlefield death, cemetery dedication, and public mourning",
        "historical_alignment_level": ["historical_consequence", "social_uptake"],
        "summary": "Gettysburg links actual battlefield death, cemetery dedication, and public mourning to Lincoln's symbolic conversion of death into national obligation.",
        "linked_mapping_ids": ["lincoln-cmt-002", "lincoln-cmt-004", "lincoln-cmt-005", "lincoln-cmt-006"],
        "corroboration_status": "contextually-corroborated; publication citations required",
        "claim_boundary": "Supports historical alignment for public mourning and battlefield death, not a claim that the address caused the deaths.",
    },
    {
        "note_id": "lincoln-hist-002",
        "dimension": "historical_enactment_alignment",
        "topic": "Slavery, emancipation, and wartime bloodshed in the Second Inaugural",
        "historical_alignment_level": ["formal_enactment", "historical_consequence"],
        "summary": "The Second Inaugural's debt, blood, and judgment language aligns with the Civil War's slavery conflict, emancipation policy, and immense wartime death toll.",
        "linked_mapping_ids": ["lincoln-cmt-007", "lincoln-cmt-008", "lincoln-cmt-009"],
        "corroboration_status": "contextually-corroborated; publication citations required",
        "claim_boundary": "Separates historical alignment from proof of providential causality or private belief.",
    },
    {
        "note_id": "lincoln-hist-003",
        "dimension": "historical_enactment_alignment",
        "topic": "Lyceum republican survival rhetoric before the Civil War",
        "historical_alignment_level": ["social_uptake"],
        "summary": "The Lyceum Address supplies early body-politic survival language, but its alignment is primarily rhetorical and civic rather than direct war enactment.",
        "linked_mapping_ids": ["lincoln-cmt-001"],
        "corroboration_status": "limited-contextual alignment",
        "claim_boundary": "Useful for diachronic setup; does not by itself establish historical enactment.",
    },
]

LINCOLN_DOCUMENT_RATINGS = [
    {
        "score_id": "lincoln-score-doc-lyceum",
        "document_id": "lincoln-lyceum-address",
        "document_weight": 1.0,
        "weight_rationale": "Standard early public-address benchmark; important for diachronic setup but not war enactment.",
        "scores": {
            "sacred_object": 2.0,
            "sacrificial_body": 0.0,
            "enemy_as_bringer_of_death": 1.0,
            "historical_enactment_alignment": 1.0,
        },
        "mapping_ids": ["lincoln-cmt-001"],
        "historical_note_ids": ["lincoln-hist-003"],
        "rationale": "The address figures the nation as a living collective body but does not yet supply battlefield sacrifice or strong enemy-as-bringer-of-death evidence.",
    },
    {
        "score_id": "lincoln-score-doc-gettysburg",
        "document_id": "lincoln-gettysburg-address",
        "document_weight": 2.0,
        "weight_rationale": "Canonical, rhetorically central battlefield-dedication text.",
        "scores": {
            "sacred_object": 3.0,
            "sacrificial_body": 3.0,
            "enemy_as_bringer_of_death": 1.0,
            "historical_enactment_alignment": 3.0,
        },
        "mapping_ids": [
            "lincoln-cmt-002",
            "lincoln-cmt-003",
            "lincoln-cmt-004",
            "lincoln-cmt-005",
            "lincoln-cmt-006",
        ],
        "historical_note_ids": ["lincoln-hist-001"],
        "rationale": "Gettysburg strongly links battlefield death, national survival, civic dedication, and democratic renewal, while the enemy remains mostly unnamed.",
    },
    {
        "score_id": "lincoln-score-doc-second-inaugural",
        "document_id": "lincoln-second-inaugural",
        "document_weight": 2.0,
        "weight_rationale": "Canonical late-war inaugural text for providence, slavery, blood repayment, and reconciliation.",
        "scores": {
            "sacred_object": 2.0,
            "sacrificial_body": 3.0,
            "enemy_as_bringer_of_death": 1.0,
            "historical_enactment_alignment": 3.0,
        },
        "mapping_ids": ["lincoln-cmt-007", "lincoln-cmt-008", "lincoln-cmt-009"],
        "historical_note_ids": ["lincoln-hist-002"],
        "rationale": "The Second Inaugural strongly aligns blood, slavery, and judgment with historical war and emancipation contexts, but restrains enemy-destruction framing through shared guilt and reconciliation.",
    },
]


def category(score: float) -> str:
    if score < 0.5:
        return "unsupported"
    if score < 1.5:
        return "weak support"
    if score < 2.5:
        return "moderate support"
    if score < 3.5:
        return "strong support"
    return "very strong support"


def historical_cap(score: float) -> str:
    if score < 1.5:
        return "weak support"
    if score < 2.5:
        return "moderate support"
    if score < 3.5:
        return "strong support"
    return "very strong support"


def cap_category(overall: str, cap: str) -> str:
    order = ["unsupported", "weak support", "moderate support", "strong support", "very strong support"]
    return order[min(order.index(overall), order.index(cap))]


def weighted_dimension_scores(ratings: list[dict[str, Any]]) -> dict[str, float]:
    denominator = sum(float(item["document_weight"]) for item in ratings)
    scores: dict[str, float] = {}
    for dimension in DIMENSIONS:
        numerator = sum(float(item["scores"][dimension]) * float(item["document_weight"]) for item in ratings)
        scores[dimension] = round(numerator / denominator, 2)
    return scores


def shifted_geometric(scores: dict[str, float]) -> float:
    s = scores["sacred_object"]
    b = scores["sacrificial_body"]
    e = scores["enemy_as_bringer_of_death"]
    h = scores["historical_enactment_alignment"]
    return round((prod([s + 1, b + 1, e + 1, h + 1, h + 1]) ** (1 / 5)) - 1, 2)


def write_csv(path: Path, ratings: list[dict[str, Any]], case_scores: dict[str, float]) -> None:
    rows: list[dict[str, Any]] = []
    for item in ratings:
        row = {
            "score_id": item["score_id"],
            "level": "document",
            "document_id": item["document_id"],
            "document_weight": item["document_weight"],
            "mapping_ids": ";".join(item["mapping_ids"]),
            "historical_note_ids": ";".join(item["historical_note_ids"]),
        }
        row.update(item["scores"])
        rows.append(row)
    case_row = {
        "score_id": "lincoln-score-case",
        "level": "case",
        "document_id": "",
        "document_weight": "",
        "mapping_ids": "",
        "historical_note_ids": ";".join(note["note_id"] for note in LINCOLN_HISTORICAL_NOTES),
    }
    case_row.update(case_scores)
    rows.append(case_row)

    fieldnames = [
        "score_id",
        "level",
        "document_id",
        "document_weight",
        *DIMENSIONS,
        "mapping_ids",
        "historical_note_ids",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def write_markdown(case_id: str, generated_at: str, case_scores: dict[str, float], overall_score: float, final_category: str) -> None:
    analysis_dir = case_dir(case_id) / "analysis"
    hist_rows = [
        {
            "note_id": note["note_id"],
            "topic": note["topic"],
            "mapping_ids": ";".join(note["linked_mapping_ids"]),
            "corroboration_status": note["corroboration_status"],
        }
        for note in LINCOLN_HISTORICAL_NOTES
    ]
    (analysis_dir / "historical-enactment-alignment.md").write_text(
        f"""# Historical Enactment Alignment: {case_id}

Generated: {generated_at}

Status: draft contextual corroboration notes. Publication citations remain
required before these notes support final claims.

{md_table(hist_rows, ["note_id", "topic", "mapping_ids", "corroboration_status"])}

Historical alignment is separated from textual-symbolic evidence. These notes
corroborate context; they do not prove causal force or private intention.
""",
        encoding="utf-8",
    )

    score_rows = [
        {
            "dimension": dimension,
            "score": case_scores[dimension],
            "category": category(case_scores[dimension]),
        }
        for dimension in DIMENSIONS
    ]
    (analysis_dir / "koenigsbergian-support-synthesis.md").write_text(
        f"""# Koenigsbergian Support Synthesis: {case_id}

Generated: {generated_at}

Status: draft support assessment from reviewed pilot evidence.

## Case-Level Scores

{md_table(score_rows, ["dimension", "score", "category"])}

Weighted shifted geometric score: `{overall_score}`.

Historical-alignment cap applied. Overall category: **{final_category}**.

## Synthesis

The current Lincoln pilot evidence gives moderate, complicated support for the
Law of Sacrifice framework. Sacred-object and sacrificial-body evidence is
strongest around Gettysburg's national survival, dedication, and new-birth
language. Providence and blood-repayment evidence in the Second Inaugural
strengthens historical alignment and guilt distribution, but enemy-as-bringer-of-death
evidence remains weak because the key passages often suppress or diffuse enemy
agency rather than constructing an enemy as a death-bearing agent, carrier, or sign.

## Boundaries

- This is not proof of Koenigsberg's theory.
- Full-corpus MIPVU review and reliability adjudication remain pending.
- Historical notes require publication-grade citations before final use.
- Reconciliation and shared guilt complicate any simple enemy-destruction
  reading of Lincoln.
""",
        encoding="utf-8",
    )


def build_case(case_id: str) -> dict[str, Any]:
    generated_at = now_iso()
    analysis_dir = case_dir(case_id) / "analysis"
    case_scores = weighted_dimension_scores(LINCOLN_DOCUMENT_RATINGS)
    overall_score = shifted_geometric(case_scores)
    overall_category = category(overall_score)
    cap = historical_cap(case_scores["historical_enactment_alignment"])
    final_category = cap_category(overall_category, cap)

    historical = {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft",
        "notes": LINCOLN_HISTORICAL_NOTES,
    }
    ratings = {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft",
        "scale": "0-4 anchored support scale",
        "document_ratings": LINCOLN_DOCUMENT_RATINGS,
        "case_scores": case_scores,
        "overall_support": {
            "formula": "((S + 1) * (B + 1) * (E + 1) * (H + 1)^2)^(1/5) - 1",
            "score": overall_score,
            "uncapped_category": overall_category,
            "historical_alignment_cap": cap,
            "final_category": final_category,
        },
        "limitations": [
            "Scores are provisional and based on reviewed Lincoln pilot evidence.",
            "Full-corpus MIPVU review and reliability adjudication are pending.",
            "Historical alignment notes require publication-grade citations.",
        ],
    }
    synthesis = {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft",
        "support_summary": ratings["overall_support"],
        "support_statement": "moderate, complicated support",
        "supporting_dimensions": case_scores,
        "complications": [
            "Enemy-as-bringer-of-death evidence is weak in the reviewed Lincoln pilot sample.",
            "Reconciliation and shared guilt complicate a simple enemy-destruction reading.",
            "The strongest sacrificial evidence is concentrated in Gettysburg.",
        ],
        "claim_boundary": "Assessment of evidentiary support, not proof or causal explanation.",
    }

    write_json(analysis_dir / "historical-enactment-alignment.json", historical)
    write_json(analysis_dir / "support-ratings.json", ratings)
    write_json(analysis_dir / "koenigsbergian-support-synthesis.json", synthesis)
    write_csv(analysis_dir / "support-ratings.csv", LINCOLN_DOCUMENT_RATINGS, case_scores)
    write_markdown(case_id, generated_at, case_scores, overall_score, final_category)
    return ratings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    args = parser.parse_args()

    for case_id in case_ids(args.case_id):
        if case_id != "lincoln":
            print(f"{case_id}: skipped; support synthesis template is currently implemented for lincoln.")
            continue
        ratings = build_case(case_id)
        print(
            f"{case_id}: built support synthesis with overall score "
            f"{ratings['overall_support']['score']} ({ratings['overall_support']['final_category']})."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
