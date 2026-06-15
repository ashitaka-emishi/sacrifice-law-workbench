#!/usr/bin/env python3
"""Build corpus-assisted and diachronic analysis outputs from CMT mappings."""
from __future__ import annotations

import argparse
import csv
from itertools import combinations
from pathlib import Path
from typing import Any

from pipeline_common import (
    case_dir,
    case_ids,
    cmt_mappings_path_for,
    count_by,
    document_id,
    documents,
    iter_cmt_mappings,
    now_iso,
    read_json,
    write_json,
)


def document_lookup(case_id: str) -> dict[str, dict[str, Any]]:
    return {document_id(doc): doc for doc in documents(case_id)}


def enriched_mappings(case_id: str) -> list[dict[str, Any]]:
    path = cmt_mappings_path_for(case_id)
    data = read_json(path, {}) or {}
    docs = document_lookup(case_id)
    mappings: list[dict[str, Any]] = []
    for mapping in iter_cmt_mappings(data):
        item = dict(mapping)
        doc = docs.get(str(item.get("document_id") or ""), {})
        item.setdefault("document_date", doc.get("date"))
        item.setdefault("period", doc.get("period"))
        item.setdefault("register", doc.get("register"))
        mappings.append(item)
    return mappings


def mapping_ids(items: list[dict[str, Any]]) -> str:
    return ";".join(str(item.get("mapping_id")) for item in items if item.get("mapping_id"))


def average_confidence(items: list[dict[str, Any]]) -> float | None:
    values = [item.get("confidence") for item in items if isinstance(item.get("confidence"), (int, float))]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def grouped_rows(mappings: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for mapping in mappings:
        value = mapping.get(field)
        values = value if isinstance(value, list) else [value]
        for entry in values:
            if entry in (None, "", []):
                continue
            buckets.setdefault(str(entry), []).append(mapping)
    return [
        {
            "metric": field,
            "value": value,
            "mapping_count": len(items),
            "document_count": len({item.get("document_id") for item in items}),
            "high_salience_count": sum(1 for item in items if item.get("rhetorical_salience") == "high"),
            "average_confidence": average_confidence(items),
            "mapping_ids": mapping_ids(items),
        }
        for value, items in sorted(buckets.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    ]


def source_domain_values(mapping: dict[str, Any]) -> list[str]:
    values = [mapping.get("source_domain_primary")]
    secondary = mapping.get("source_domain_secondary", [])
    values.extend(secondary if isinstance(secondary, list) else [secondary])
    return sorted({str(value) for value in values if value not in (None, "", [])})


def cooccurrence_rows(mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for mapping in mappings:
        domains = source_domain_values(mapping)
        for pair in combinations(domains, 2):
            buckets.setdefault(pair, []).append(mapping)
    return [
        {
            "source_domain_a": pair[0],
            "source_domain_b": pair[1],
            "mapping_count": len(items),
            "mapping_ids": mapping_ids(items),
        }
        for pair, items in sorted(buckets.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    ]


def cluster_distribution(mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    clusters: dict[str, list[dict[str, Any]]] = {}
    for mapping in mappings:
        cluster_id = str(mapping.get("cluster_id") or "")
        if cluster_id:
            clusters.setdefault(cluster_id, []).append(mapping)
    for cluster_id, items in sorted(clusters.items()):
        rows.append(
            {
                "cluster_id": cluster_id,
                "mapping_count": len(items),
                "document_count": len({item.get("document_id") for item in items}),
                "registers": ";".join(sorted({str(item.get("register")) for item in items if item.get("register")})),
                "periods": ";".join(sorted({str(item.get("period")) for item in items if item.get("period")})),
                "high_salience_count": sum(1 for item in items if item.get("rhetorical_salience") == "high"),
                "average_confidence": average_confidence(items),
                "mapping_ids": mapping_ids(items),
            }
        )
    return rows


def salience_review(mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    by_concept = count_by(mappings, lambda item: item.get("conceptual_metaphor"))
    by_cluster = count_by(mappings, lambda item: item.get("cluster_id"))
    for mapping in sorted(mappings, key=lambda item: (item.get("document_date") or "", item.get("mapping_id") or "")):
        concept = str(mapping.get("conceptual_metaphor") or "")
        cluster_id = str(mapping.get("cluster_id") or "")
        rows.append(
            {
                "mapping_id": mapping.get("mapping_id"),
                "rhetorical_salience": mapping.get("rhetorical_salience"),
                "frequency_count_for_concept": by_concept.get(concept, 0),
                "cluster_mapping_count": by_cluster.get(cluster_id, 0),
                "conceptual_centrality": "high" if by_cluster.get(cluster_id, 0) >= 2 else "local",
                "ideological_force": ";".join(mapping.get("ideological_functions", []) or []),
                "claim_caution": "high salience is not the same as high frequency",
            }
        )
    return rows


def timeline_rows(mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "document_date": mapping.get("document_date"),
            "period": mapping.get("period"),
            "register": mapping.get("register"),
            "document_id": mapping.get("document_id"),
            "mapping_id": mapping.get("mapping_id"),
            "cluster_id": mapping.get("cluster_id"),
            "source_domain_primary": mapping.get("source_domain_primary"),
            "target_domain": mapping.get("target_domain"),
            "conceptual_metaphor": mapping.get("conceptual_metaphor"),
            "rhetorical_salience": mapping.get("rhetorical_salience"),
            "confidence": mapping.get("confidence"),
            "mipvu_ids": ";".join(mapping.get("mipvu_ids", []) or []),
        }
        for mapping in sorted(mappings, key=lambda item: (item.get("document_date") or "", item.get("mapping_id") or ""))
    ]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    if not rows:
        return "_No rows._"
    header = "| " + " | ".join(fields) + " |"
    sep = "| " + " | ".join("---" for _ in fields) + " |"
    body = [
        "| " + " | ".join(str(row.get(field, "")) for field in fields) + " |"
        for row in rows
    ]
    return "\n".join([header, sep, *body])


def build_markdown(case_id: str, generated_at: str, mappings: list[dict[str, Any]], frequency_rows: list[dict[str, Any]], cluster_rows: list[dict[str, Any]], salience_rows: list[dict[str, Any]]) -> str:
    return f"""# Corpus-Assisted Analysis: {case_id}

Generated: {generated_at}

Status: draft analysis from MIPVU-backed CMT mappings.

## Scope

This artifact summarizes {len(mappings)} CMT mapping records. Each mapping cites
one or more MIPVU-positive or uncertain lexical units. Frequency counts are
counts of mapping records, not counts of every metaphor in the full corpus.

## Frequency And Distribution

{markdown_table(frequency_rows[:12], ["metric", "value", "mapping_count", "document_count", "high_salience_count", "average_confidence"])}

## Cluster Distribution

{markdown_table(cluster_rows, ["cluster_id", "mapping_count", "document_count", "registers", "periods", "high_salience_count", "average_confidence"])}

## Salience Review

{markdown_table(salience_rows, ["mapping_id", "rhetorical_salience", "frequency_count_for_concept", "cluster_mapping_count", "conceptual_centrality", "ideological_force"])}

## Claim Discipline

Frequency, distribution, concentration, rhetorical salience, conceptual
centrality, and ideological force are separate measures. A high-salience mapping
may appear once in a climactic passage; a repeated mapping may still be
conceptually weak or conventional. Treat this artifact as a review index, not a
finished interpretive argument.
"""


def build_diachronic_markdown(case_id: str, generated_at: str, timeline: list[dict[str, Any]]) -> str:
    return f"""# Diachronic Analysis: {case_id}

Generated: {generated_at}

Status: provisional; based on reviewed Lincoln MIPVU pilot evidence and CMT
mapping records.

## Timeline

{markdown_table(timeline, ["document_date", "period", "mapping_id", "cluster_id", "conceptual_metaphor", "rhetorical_salience"])}

## Change Notes

- `lincoln-01-body-organism` appears in the 1838 Lyceum evidence and again in
  the Gettysburg democratic-survival language. Current classification:
  stable/reactivated, not yet fully measured across the whole corpus.
- `lincoln-08-sacrificial-death-gift` is concentrated in the Gettysburg burial
  and dedication evidence. Current classification: intensifying at the
  peak-war-sacrifice stage, pending fuller review.
- `lincoln-04-birth-creation` appears in the Gettysburg "new birth" sentence.
  Current classification: local high-salience mutation from preservation toward
  renewal.
- `lincoln-06-providence-theodicy` appears in the Second Inaugural evidence.
  Current classification: reorganization toward providential accounting and
  shared moral judgment in the final-reconciliation stage.
- Clusters without current CMT mapping evidence should be treated as uncoded in
  this sample, not as disappearing from Lincoln's metaphor system.
"""


def build_cluster_evolution_markdown(case_id: str, generated_at: str, cluster_rows: list[dict[str, Any]]) -> str:
    return f"""# Cluster Evolution: {case_id}

Generated: {generated_at}

{markdown_table(cluster_rows, ["cluster_id", "mapping_count", "document_count", "periods", "mapping_ids"])}

## Interpretation Rules

- Stable: appears across periods with similar source-target structure.
- Intensifying: grows more rhetorically salient or densely connected in later
  periods.
- Mutating: source or target domain changes while retaining a recognizable
  family resemblance.
- Reorganizing: multiple source domains merge into a new explanatory frame.
- Disappearing: only assign after full-corpus review shows absence across
  comparable registers.
"""


def build_case_corpus_analysis(case_id: str) -> dict[str, Any]:
    case_path = case_dir(case_id)
    analysis_dir = case_path / "analysis"
    mappings = enriched_mappings(case_id)
    generated_at = now_iso()
    if not mappings:
        output = {
            "version": "1.0",
            "case_id": case_id,
            "generated_at": generated_at,
            "status": "stub",
            "mapping_count": 0,
            "errors": ["no CMT mapping file found or no mappings defined"],
        }
        write_json(analysis_dir / "corpus-analysis.json", output)
        return output

    frequency_rows: list[dict[str, Any]] = []
    for field in [
        "source_domain_primary",
        "target_domain",
        "conceptual_metaphor",
        "cluster_id",
        "rhetorical_salience",
        "register",
        "period",
    ]:
        frequency_rows.extend(grouped_rows(mappings, field))

    cluster_rows = cluster_distribution(mappings)
    cooccurrence = cooccurrence_rows(mappings)
    salience = salience_review(mappings)
    timeline = timeline_rows(mappings)

    output = {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "complete",
        "source": str(cmt_mappings_path_for(case_id).relative_to(case_path)),
        "mapping_count": len(mappings),
        "frequency_tables": frequency_rows,
        "cluster_distribution": cluster_rows,
        "source_domain_cooccurrence": cooccurrence,
        "salience_review": salience,
        "timeline": timeline,
        "measure_definitions": {
            "frequency": "Number of CMT mapping records in the reviewed mapping table.",
            "distribution": "Number of documents, registers, or periods in which a mapping pattern appears.",
            "concentration": "Whether mappings are concentrated in a few documents or periods.",
            "rhetorical_salience": "Analyst-coded prominence in the local rhetorical occasion.",
            "conceptual_centrality": "Whether a cluster organizes multiple mapping records in the current evidence set.",
            "ideological_force": "Recorded ideological functions attached to the mapping; not reducible to frequency.",
        },
        "diachronic_classification": {
            "lincoln-01-body-organism": "stable/reactivated",
            "lincoln-08-sacrificial-death-gift": "intensifying in peak-war-sacrifice evidence",
            "lincoln-04-birth-creation": "local high-salience mutation toward renewal",
            "lincoln-06-providence-theodicy": "reorganizing in final-reconciliation evidence",
        },
    }

    write_json(analysis_dir / "corpus-analysis.json", output)
    write_csv(analysis_dir / "frequency-tables.csv", frequency_rows)
    write_csv(analysis_dir / "cluster-distribution.csv", cluster_rows)
    write_csv(analysis_dir / "source-domain-cooccurrence.csv", cooccurrence)
    write_csv(analysis_dir / "salience-review.csv", salience)
    write_csv(analysis_dir / "metaphor-timeline.csv", timeline)
    (analysis_dir / "corpus-analysis.md").write_text(
        build_markdown(case_id, generated_at, mappings, frequency_rows, cluster_rows, salience),
        encoding="utf-8",
    )
    (analysis_dir / "diachronic-analysis.md").write_text(
        build_diachronic_markdown(case_id, generated_at, timeline),
        encoding="utf-8",
    )
    (analysis_dir / "cluster-evolution.md").write_text(
        build_cluster_evolution_markdown(case_id, generated_at, cluster_rows),
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    args = parser.parse_args()

    for case_id in case_ids(args.case_id):
        output = build_case_corpus_analysis(case_id)
        print(f"{case_id}: built corpus analysis from {output['mapping_count']} CMT mapping(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
