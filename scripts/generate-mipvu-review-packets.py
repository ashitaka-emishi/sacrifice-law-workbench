#!/usr/bin/env python3
"""Generate CSV review packets from MIPVU worklists."""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any

from pipeline_common import (
    case_dir,
    document_id,
    documents,
    iter_mipvu_records,
    iter_sentence_nodes,
    mipvu_path_for,
    now_iso,
    read_json,
    segmented_path_for,
    write_json,
)

DECISION_TYPES = [
    "non_metaphor",
    "mipvu_indirect",
    "mipvu_direct",
    "mipvu_implicit",
    "mipvu_personification",
    "uncertain",
    "excluded_nonlexical",
]

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

TERM_SPLIT_RE = re.compile(r"\s*/\s*")
WORD_RE = re.compile(r"[a-z]+")


def normalize(value: str) -> str:
    return re.sub(r"[^a-z]+", "", value.lower())


def historical_controls(case_id: str) -> dict[str, dict[str, str]]:
    path = case_dir(case_id) / "references" / "historical-semantics-notes.md"
    if not path.exists():
        return {}
    controls: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| Term ") or set(line.strip()) <= {"|", "-", " "}:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        term_cell, _, _, risk = cells[:4]
        for raw_term in TERM_SPLIT_RE.split(term_cell):
            words = WORD_RE.findall(raw_term.lower())
            if not words:
                continue
            term = " ".join(words)
            controls[normalize(term)] = {"term": term, "risk": risk}
            for word in words:
                controls.setdefault(normalize(word), {"term": term, "risk": risk})

    controls.update(
        {
            "dedicated": {"term": "dedicate", "risk": "high"},
            "dedication": {"term": "dedicate", "risk": "high"},
            "conceived": {"term": "conceived", "risk": "medium"},
            "brought": {"term": "brought forth", "risk": "medium"},
            "forth": {"term": "brought forth", "risk": "medium"},
            "bondsmans": {"term": "bond / bondsman", "risk": "high"},
            "judgments": {"term": "judgment", "risk": "high"},
            "offenses": {"term": "offense", "risk": "high"},
        }
    )
    return controls


def sentence_lookup(case_id: str) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for doc in documents(case_id):
        data = read_json(segmented_path_for(case_id, doc), {}) or {}
        if not isinstance(data, dict):
            continue
        for sentence in iter_sentence_nodes(data):
            sentence_id = str(sentence.get("sentence_id") or "")
            if sentence_id:
                lookup[sentence_id] = str(sentence.get("text") or "")
    return lookup


def all_units(case_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    sentences = sentence_lookup(case_id)
    controls = historical_controls(case_id)
    for doc in documents(case_id):
        path = mipvu_path_for(case_id, doc)
        data = read_json(path, {}) or {}
        for unit in iter_mipvu_records(data):
            key = normalize(str(unit.get("lemma") or unit.get("lexical_unit") or ""))
            control = controls.get(key, {})
            row = {
                "case_id": case_id,
                "document_id": document_id(doc),
                "sentence_id": unit.get("sentence_id", ""),
                "mipvu_id": unit.get("mipvu_id", ""),
                "lexical_unit": unit.get("lexical_unit", ""),
                "lemma": unit.get("lemma", ""),
                "language": unit.get("language", ""),
                "unit_ordinal": unit.get("unit_ordinal", ""),
                "sentence_unit_ordinal": unit.get("sentence_unit_ordinal", ""),
                "sentence_text": sentences.get(str(unit.get("sentence_id") or ""), ""),
                "semantic_control_term": control.get("term", ""),
                "semantic_control_risk": control.get("risk", ""),
                "current_review_status": unit.get("review_status", ""),
                "current_decision_type": unit.get("decision_type", ""),
            }
            for field in REVIEW_FIELDS:
                row[field] = unit.get(field, "") if unit.get("review_status") != "pending" else ""
            records.append(row)
    return records


def reliability_sentence_ids(case_id: str) -> tuple[str, set[str]]:
    path = case_dir(case_id) / "quality" / "reliability-sample.json"
    sample = read_json(path, {}) or {}
    batch_id = str(sample.get("batch_id") or f"{case_id}-reliability")
    reliability_sample = sample.get("reliability_sample", {}) if isinstance(sample, dict) else {}
    sentences = reliability_sample.get("sampled_sentences", []) if isinstance(reliability_sample, dict) else []
    ids = {
        str(item.get("sentence_id"))
        for item in sentences
        if isinstance(item, dict) and item.get("sentence_id")
    }
    return batch_id, ids


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def coder_rows(rows: list[dict[str, Any]], batch_id: str, coder_id: str, sentence_ids: set[str]) -> list[dict[str, Any]]:
    selected = [row for row in rows if row["sentence_id"] in sentence_ids]
    packet_rows = []
    for row in selected:
        out = {field: row.get(field, "") for field in CODER_FIELDS}
        out["batch_id"] = batch_id
        out["coder_id"] = coder_id
        for field in REVIEW_FIELDS:
            out[field] = ""
        packet_rows.append(out)
    return packet_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", required=True)
    args = parser.parse_args()

    case_id = args.case_id
    output_dir = case_dir(case_id) / "quality" / "review-packets"
    rows = all_units(case_id)
    batch_id, reliability_ids = reliability_sentence_ids(case_id)
    reliability_rows = [row for row in rows if row["sentence_id"] in reliability_ids]

    write_csv(output_dir / f"{case_id}-full-corpus-review.csv", PACKET_FIELDS, rows)
    write_csv(output_dir / f"{batch_id}-coder-a.csv", CODER_FIELDS, coder_rows(rows, batch_id, "coder-a", reliability_ids))
    write_csv(output_dir / f"{batch_id}-coder-b.csv", CODER_FIELDS, coder_rows(rows, batch_id, "coder-b", reliability_ids))
    write_csv(output_dir / f"{batch_id}-adjudication-template.csv", ADJUDICATION_FIELDS, [])

    manifest = {
        "case_id": case_id,
        "generated_at": now_iso(),
        "status": "review-packets-generated",
        "full_corpus_units": len(rows),
        "pending_units": sum(1 for row in rows if row["current_review_status"] == "pending"),
        "reviewed_or_nonpending_units": sum(1 for row in rows if row["current_review_status"] != "pending"),
        "reliability_batch_id": batch_id,
        "reliability_sample_units": len(reliability_rows),
        "reliability_sample_sentences": len(reliability_ids),
        "outputs": [
            str((output_dir / f"{case_id}-full-corpus-review.csv").relative_to(case_dir(case_id))),
            str((output_dir / f"{batch_id}-coder-a.csv").relative_to(case_dir(case_id))),
            str((output_dir / f"{batch_id}-coder-b.csv").relative_to(case_dir(case_id))),
            str((output_dir / f"{batch_id}-adjudication-template.csv").relative_to(case_dir(case_id))),
        ],
    }
    write_json(output_dir / "review-packet-manifest.json", manifest)
    print(
        f"{case_id}: wrote {len(rows)} full-corpus review row(s) and "
        f"{len(reliability_rows)} reliability sample row(s) to {output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
