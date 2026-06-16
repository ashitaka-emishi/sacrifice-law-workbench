#!/usr/bin/env python3
"""Generate the publication package and claim traceability audit."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from pipeline_common import (
    ROOT,
    case_dir,
    cmt_mappings_path_for,
    document_id,
    documents,
    iter_cmt_mappings,
    iter_mipvu_records,
    iter_sentence_nodes,
    mipvu_path_for,
    now_iso,
    raw_path_for,
    read_json,
    segmented_path_for,
    write_json,
)

PACKAGE_DIR = ROOT / "publication"
AUDIT_DIR = PACKAGE_DIR / "audit"

SUPPORT_DIMENSION_LABELS = {
    "sacred_object": "sacred object",
    "sacrificial_body": "sacrificial body",
    "enemy_as_bringer_of_death": "enemy as bringer of death",
    "historical_enactment_alignment": "historical enactment or alignment",
}

VALIDATION_GATE = [
    "npm run status",
    "npm run pipeline",
    "npm run validate",
    "quarto render",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def md_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    text = str(value).replace("\n", " ").strip()
    return text.replace("|", "\\|")


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    if not rows:
        return "_No rows._"
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_cell(row.get(field)) for field in fields) + " |")
    return "\n".join(lines)


def score_category(score: float | int | None) -> str:
    if not isinstance(score, (int, float)):
        return "unscored"
    if score < 0.5:
        return "unsupported"
    if score < 1.5:
        return "weak support"
    if score < 2.5:
        return "moderate support"
    if score < 3.5:
        return "strong support"
    return "very strong support"


def document_lookup(case_id: str) -> dict[str, dict[str, Any]]:
    return {document_id(doc): doc for doc in documents(case_id)}


def sentence_lookup(case_id: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for doc in documents(case_id):
        doc_id = document_id(doc)
        path = segmented_path_for(case_id, doc)
        data = read_json(path, {}) or {}
        if not isinstance(data, dict):
            continue
        for sentence in iter_sentence_nodes(data):
            sentence_id = str(sentence.get("sentence_id") or "")
            if not sentence_id:
                continue
            lookup[sentence_id] = {
                "sentence_id": sentence_id,
                "document_id": doc_id,
                "text": sentence.get("text", ""),
                "path": rel(path),
            }
    return lookup


def mipvu_lookup(case_id: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for doc in documents(case_id):
        path = mipvu_path_for(case_id, doc)
        data = read_json(path, {}) or {}
        if not isinstance(data, dict):
            continue
        for unit in iter_mipvu_records(data):
            mipvu_id = str(unit.get("mipvu_id") or "")
            if mipvu_id:
                item = dict(unit)
                item["path"] = rel(path)
                lookup[mipvu_id] = item
    return lookup


def mapping_lookup(case_id: str) -> dict[str, dict[str, Any]]:
    data = read_json(cmt_mappings_path_for(case_id), {}) or {}
    return {
        str(mapping.get("mapping_id")): dict(mapping)
        for mapping in iter_cmt_mappings(data)
        if mapping.get("mapping_id")
    }


def historical_note_lookup(case_id: str) -> dict[str, dict[str, Any]]:
    path = case_dir(case_id) / "analysis" / "historical-enactment-alignment.json"
    data = read_json(path, {}) or {}
    notes = data.get("notes", []) if isinstance(data, dict) else []
    return {
        str(note.get("note_id")): dict(note)
        for note in notes
        if isinstance(note, dict) and note.get("note_id")
    }


def trace_limitations(case_id: str) -> list[str]:
    support_path = case_dir(case_id) / "analysis" / "support-ratings.json"
    data = read_json(support_path, {}) or {}
    limitations = data.get("limitations", []) if isinstance(data, dict) else []
    base = [
        "Trace rows are draft review aids, not final publication claims.",
        "Publication-grade historical citations remain required where historical notes say so.",
    ]
    return base + [str(item) for item in limitations if item]


def build_trace_records(case_id: str, generated_at: str) -> list[dict[str, Any]]:
    docs = document_lookup(case_id)
    sentences = sentence_lookup(case_id)
    mipvu = mipvu_lookup(case_id)
    mappings = mapping_lookup(case_id)
    historical_notes = historical_note_lookup(case_id)
    support_path = case_dir(case_id) / "analysis" / "support-ratings.json"
    support = read_json(support_path, {}) or {}
    ratings = support.get("document_ratings", []) if isinstance(support, dict) else []
    limitations = trace_limitations(case_id)

    traces: list[dict[str, Any]] = []
    for rating in ratings:
        if not isinstance(rating, dict):
            continue
        score_id = str(rating.get("score_id") or "")
        doc_id = str(rating.get("document_id") or "")
        doc = docs.get(doc_id, {})
        doc_title = doc.get("short_title") or doc.get("title") or doc_id
        raw_path = raw_path_for(case_id, doc) if doc else case_dir(case_id) / "corpus" / "raw"
        note_ids = [str(item) for item in rating.get("historical_note_ids", []) if item]
        note_records = [historical_notes[note_id] for note_id in note_ids if note_id in historical_notes]
        mapping_ids = [str(item) for item in rating.get("mapping_ids", []) if item]

        for dimension, score in (rating.get("scores") or {}).items():
            if dimension not in SUPPORT_DIMENSION_LABELS:
                continue
            for mapping_id in mapping_ids:
                mapping = mappings.get(mapping_id, {})
                mipvu_ids = [str(item) for item in mapping.get("mipvu_ids", []) if item]
                sentence_id = str(mapping.get("sentence_id") or "")
                sentence = sentences.get(sentence_id, {})
                trace_id = f"{score_id}-{dimension}-{mapping_id}"
                claim_status = "inference" if dimension == "historical_enactment_alignment" else "interpretation"
                traces.append(
                    {
                        "trace_id": trace_id,
                        "case_id": case_id,
                        "generated_at": generated_at,
                        "claim_id": f"{score_id}-{dimension}",
                        "claim_text": (
                            f"{doc_title} contributes {score_category(score)} evidence "
                            f"for {SUPPORT_DIMENSION_LABELS[dimension]} "
                            f"(score {score}/4): {rating.get('rationale', '')}"
                        ),
                        "claim_status": claim_status,
                        "claim_boundary": (
                            "Draft evidentiary-support assessment from reviewed pilot evidence; "
                            "not proof, diagnosis, or monocausal historical explanation."
                        ),
                        "support_dimension": dimension,
                        "support_dimension_label": SUPPORT_DIMENSION_LABELS[dimension],
                        "support_score_id": score_id,
                        "support_score": score,
                        "support_score_path": rel(support_path),
                        "document_weight": rating.get("document_weight"),
                        "weight_rationale": rating.get("weight_rationale"),
                        "cluster_id": mapping.get("cluster_id"),
                        "mapping_id": mapping_id,
                        "mapping_status": mapping.get("mapping_status"),
                        "conceptual_metaphor": mapping.get("conceptual_metaphor"),
                        "source_domain_primary": mapping.get("source_domain_primary"),
                        "target_domain": mapping.get("target_domain"),
                        "expression": mapping.get("expression"),
                        "evidence_span": mapping.get("evidence_span"),
                        "mapping_confidence": mapping.get("confidence"),
                        "rival_reading": mapping.get("rival_reading"),
                        "mipvu_ids": mipvu_ids,
                        "mipvu_units": [
                            {
                                "mipvu_id": unit_id,
                                "lexical_unit": mipvu.get(unit_id, {}).get("lexical_unit"),
                                "decision_type": mipvu.get(unit_id, {}).get("decision_type"),
                                "review_status": mipvu.get(unit_id, {}).get("review_status"),
                                "confidence": mipvu.get(unit_id, {}).get("confidence"),
                                "path": mipvu.get(unit_id, {}).get("path"),
                            }
                            for unit_id in mipvu_ids
                        ],
                        "sentence_id": sentence_id,
                        "sentence_text": sentence.get("text"),
                        "segmented_sentence_path": sentence.get("path"),
                        "document_id": doc_id,
                        "document_title": doc.get("title"),
                        "document_date": doc.get("date"),
                        "document_register": doc.get("register"),
                        "source_url": doc.get("source_url"),
                        "source_citation": doc.get("source_citation"),
                        "rights_status": doc.get("rights_status"),
                        "source_text_path": rel(raw_path),
                        "historical_note_ids": note_ids,
                        "historical_corroboration": [
                            {
                                "note_id": note.get("note_id"),
                                "topic": note.get("topic"),
                                "summary": note.get("summary"),
                                "corroboration_status": note.get("corroboration_status"),
                                "claim_boundary": note.get("claim_boundary"),
                            }
                            for note in note_records
                        ],
                        "upstream_artifacts": [
                            rel(support_path),
                            rel(cmt_mappings_path_for(case_id)),
                            rel(case_dir(case_id) / "analysis" / "historical-enactment-alignment.json"),
                            rel(case_dir(case_id) / "metadata" / "document-manifest.json"),
                            rel(case_dir(case_id) / "metadata" / "corpus-register.csv"),
                        ],
                        "review_limitations": limitations,
                    }
                )
    return traces


def write_trace_json(case_id: str, generated_at: str, traces: list[dict[str, Any]]) -> dict[str, Any]:
    document = {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft-review-audit",
        "trace_policy": (
            "Every trace row links a draft support claim to a support score, "
            "CMT mapping, MIPVU unit list, sentence ID, document metadata, "
            "source text path, and historical corroboration where available."
        ),
        "traces": traces,
    }
    write_json(AUDIT_DIR / "claim-traceability.json", document)
    return document


def write_trace_csv(traces: list[dict[str, Any]]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    path = AUDIT_DIR / "claim-traceability.csv"
    fieldnames = [
        "trace_id",
        "claim_id",
        "claim_status",
        "support_dimension",
        "support_score",
        "support_score_id",
        "document_id",
        "mapping_id",
        "cluster_id",
        "mipvu_ids",
        "sentence_id",
        "historical_note_ids",
        "source_text_path",
        "rights_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for trace in traces:
            row = {field: trace.get(field, "") for field in fieldnames}
            for field in ["mipvu_ids", "historical_note_ids"]:
                row[field] = ";".join(trace.get(field, []) or [])
            writer.writerow(row)


def write_mipvu_annotations_csv(case_id: str) -> None:
    path = AUDIT_DIR / "mipvu-annotations.csv"
    fieldnames = [
        "mipvu_id",
        "case_id",
        "document_id",
        "sentence_id",
        "lexical_unit",
        "lemma",
        "decision_type",
        "review_status",
        "contextual_meaning",
        "basic_meaning",
        "confidence",
        "semantic_shift_risk",
        "review_notes",
        "source_path",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for doc in documents(case_id):
            source_path = mipvu_path_for(case_id, doc)
            data = read_json(source_path, {}) or {}
            if not isinstance(data, dict):
                continue
            for unit in iter_mipvu_records(data):
                row = {field: unit.get(field, "") for field in fieldnames}
                row["source_path"] = rel(source_path)
                writer.writerow(row)


def write_cmt_mappings_csv(case_id: str) -> None:
    path = AUDIT_DIR / "cmt-mappings.csv"
    fieldnames = [
        "mapping_id",
        "case_id",
        "document_id",
        "sentence_id",
        "expression",
        "source_domain_primary",
        "source_domain_secondary",
        "target_domain",
        "conceptual_metaphor",
        "cluster_id",
        "confidence",
        "mipvu_ids",
        "rival_reading",
        "mapping_status",
    ]
    mappings = mapping_lookup(case_id)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for mapping in sorted(mappings.values(), key=lambda item: str(item.get("mapping_id") or "")):
            row = {field: mapping.get(field, "") for field in fieldnames}
            for field in ["source_domain_secondary", "mipvu_ids"]:
                value = row.get(field)
                row[field] = ";".join(value) if isinstance(value, list) else value
            writer.writerow(row)


def write_trace_markdown(generated_at: str, traces: list[dict[str, Any]]) -> None:
    rows = [
        {
            "trace_id": trace["trace_id"],
            "status": trace["claim_status"],
            "dimension": trace["support_dimension"],
            "score": trace["support_score"],
            "mapping": trace["mapping_id"],
            "sentence": trace["sentence_id"],
            "document": trace["document_id"],
            "historical notes": trace["historical_note_ids"],
        }
        for trace in traces
    ]
    text = f"""---
title: "Claim Traceability"
---

::: {{.callout-note}}
Generated by `scripts/generate-traceability-report.py` on {generated_at}.
:::

This audit table links draft support claims to support scores, CMT mappings,
MIPVU lexical units, sentence IDs, document metadata, source text paths, and
historical corroboration notes. It is a review index, not a finished argument.

## Trace Rows

{markdown_table(rows, ["trace_id", "status", "dimension", "score", "mapping", "sentence", "document", "historical notes"])}

## Machine-Readable Artifacts

- `publication/audit/claim-traceability.json`
- `publication/audit/claim-traceability.csv`
"""
    (PACKAGE_DIR / "claim-traceability.md").write_text(text, encoding="utf-8")


def component_status(path: str, glob: bool = False) -> dict[str, Any]:
    if glob:
        matches = sorted(ROOT.glob(path))
        return {
            "path": path,
            "status": "available" if matches else "missing",
            "file_count": len(matches),
            "files": [rel(item) for item in matches],
        }
    file_path = ROOT / path
    return {
        "path": path,
        "status": "available" if file_path.exists() and file_path.stat().st_size > 0 else "missing",
        "file_count": 1 if file_path.exists() and file_path.stat().st_size > 0 else 0,
        "files": [path] if file_path.exists() and file_path.stat().st_size > 0 else [],
    }


def package_components(case_id: str) -> list[dict[str, Any]]:
    items = [
        ("research-design", "Research design", "RESEARCH_DESIGN.md", "Defines scope, method sequence, integrity rules, and evidence boundaries."),
        ("corpus-register", "Corpus register", f"cases/{case_id}/metadata/corpus-register.csv", "Documents included texts, provenance, rights status, and inclusion rationale."),
        ("annotation-codebook", "Annotation codebook", "MIPVU_ANNOTATION_GUIDE.md", "Defines MIPVU coding rules and review expectations."),
        ("historical-semantics-notes", "Historical semantics notes", f"cases/{case_id}/references/historical-semantics-notes.md", "Records period-meaning controls and semantic-risk notes."),
        ("mipvu-annotations", "MIPVU annotations", "publication/audit/mipvu-annotations.csv", "Review-table export of lexical-unit metaphor decisions."),
        ("reliability-report", "Reliability report", f"cases/{case_id}/quality/reliability-report.md", "Shows the reliability sampling and adjudication workflow."),
        ("cmt-mappings", "CMT mappings", "publication/audit/cmt-mappings.csv", "Review-table export linking conceptual mappings to MIPVU evidence."),
        ("corpus-analysis", "Corpus analysis", f"cases/{case_id}/analysis/corpus-analysis.md", "Summarizes frequency, distribution, salience, and chronology."),
        ("critical-metaphor-analysis", "Critical metaphor analysis", f"cases/{case_id}/analysis/critical-metaphor-analysis.md", "Interprets persuasive and ideological functions."),
        ("rhetorical-genre-analysis", "Rhetorical/genre analysis", f"cases/{case_id}/analysis/rhetorical-genre-analysis.md", "Controls claims by audience, occasion, genre, and agency structure."),
        ("absence-agency-analysis", "Absence/agency analysis", f"cases/{case_id}/analysis/absence-agency-analysis.md", "Records displacement, silence, and agency limits."),
        ("historical-enactment-alignment", "Historical enactment/alignment", f"cases/{case_id}/analysis/historical-enactment-alignment.md", "Corroborates symbolic patterns against historical context."),
        ("support-ratings", "Support ratings", f"cases/{case_id}/analysis/support-ratings.csv", "Records document-level and case-level support scores."),
        ("support-synthesis", "Koenigsbergian support synthesis", f"cases/{case_id}/analysis/koenigsbergian-support-synthesis.md", "Presents the draft evidentiary-support assessment."),
        ("claim-traceability", "Claim traceability", "publication/claim-traceability.md", "Links support claims to evidence records and source metadata."),
        ("ai-use-statement", "AI-use statement", "publication/ai-use-statement.md", "Explains AI assistance and human scholarly responsibility."),
        ("data-availability", "Data availability", "publication/data-availability.md", "Explains shareable data, rights status, and reuse cautions."),
        ("validation-gate", "Validation gate", "publication/validation-gate.md", "Documents the milestone-level rebuild, validation, and publication checks."),
        ("public-site-readiness", "Public-site readiness", "publication/public-site-readiness.md", "Shows draft/placeholder signals on public pages."),
    ]
    components: list[dict[str, Any]] = []
    for item in items:
        component_id, label, path, purpose = item[:4]
        status = component_status(path, bool(item[4]) if len(item) > 4 else False)
        components.append(
            {
                "component_id": component_id,
                "label": label,
                "purpose": purpose,
                "publication_status": "draft-review-package",
                **status,
            }
        )
    return components


def corpus_register_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted((ROOT / "cases").glob("*/metadata/corpus-register.csv")):
        case_id = path.parts[-3]
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    {
                        "case_id": case_id,
                        "text_id": row.get("text_id", ""),
                        "rights_status": row.get("rights_status", ""),
                        "git_tracking": row.get("git_tracking", ""),
                        "expected_local_path": row.get("expected_local_path", ""),
                        "known_limitations": row.get("known_limitations", ""),
                    }
                )
    return rows


def write_ai_use_statement(generated_at: str) -> None:
    text = f"""---
title: "AI Use Statement"
---

::: {{.callout-note}}
Generated by `scripts/generate-traceability-report.py` on {generated_at}.
:::

AI tools were used to assist with text preparation, candidate identification,
organization of annotations, schema-shaped artifact drafting, validation
support, and prose revision. All metaphor-identification decisions, conceptual
mappings, interpretive claims, support scores, historical-corroboration claims,
and final scholarly conclusions remain the responsibility of the researcher.

AI-generated suggestions are treated as provisional. They are not independent
evidence, do not replace source inspection, and do not authorize claims without
traceable support in corpus metadata, MIPVU decisions, CMT mappings, support
ratings, historical notes, or validation artifacts.
"""
    (PACKAGE_DIR / "ai-use-statement.md").write_text(text, encoding="utf-8")


def write_data_availability(generated_at: str) -> None:
    rows = corpus_register_rows()
    text = f"""---
title: "Data Availability"
---

::: {{.callout-note}}
Generated by `scripts/generate-traceability-report.py` on {generated_at}.
:::

Project scripts, schemas, manifests, source registries, analysis artifacts,
validation outputs, and public review pages are intended to be inspectable in
the repository. Corpus text reuse is governed by each document's source
metadata, rights status, storage policy, and source edition or translation
notes.

Raw texts that are public domain and marked as committed may be inspected from
the repository. Metadata-only, local-only, restricted, or unresolved sources
should be reacquired from their cited source records rather than reused from
the workbench. Publication quotations should still be checked against the
named edition or manuscript source before final use.

## Corpus Availability Snapshot

{markdown_table(rows, ["case_id", "text_id", "rights_status", "git_tracking", "expected_local_path", "known_limitations"])}
"""
    (PACKAGE_DIR / "data-availability.md").write_text(text, encoding="utf-8")


def write_validation_gate(generated_at: str) -> None:
    commands = "\n".join(f"{index}. `{command}`" for index, command in enumerate(VALIDATION_GATE, start=1))
    text = f"""---
title: "Validation Gate"
---

::: {{.callout-note}}
Generated by `scripts/generate-traceability-report.py` on {generated_at}.
:::

The milestone-level publication gate is the minimum check before promoting the
audit package or public pages as review-ready.

## Required Commands

{commands}

## Gate Meaning

- `npm run status` regenerates the project status page from status JSON.
- `npm run pipeline` rebuilds case-local outputs, x-case synthesis, and this
  publication/audit package.
- `npm run validate` checks JSON parseability and cross-artifact references,
  including claim traceability records.
- `quarto render` verifies that public pages render.

## Limitations To Preserve

- Lincoln support artifacts remain draft and based on the reviewed pilot
  sample.
- Full-corpus MIPVU review and reliability adjudication remain pending.
- Historical-alignment notes still require publication-grade citations.
- Comparator cases do not yet have case-level support ratings.
- The existing full pipeline may refresh generated corpus worklists and status
  files outside this publication package; review generated diffs before
  committing them.
"""
    (PACKAGE_DIR / "validation-gate.md").write_text(text, encoding="utf-8")


def public_page_paths() -> list[Path]:
    paths = [
        ROOT / "project-status.qmd",
        ROOT / "methodology.qmd",
        ROOT / "validation-protocol.qmd",
        ROOT / "RESEARCH_DESIGN.md",
    ]
    paths.extend(sorted((ROOT / "cases").glob("*/artifacts/qmd/*.qmd")))
    paths.extend(sorted((ROOT / "cases" / "lincoln" / "analysis").glob("*.md")))
    paths.extend(sorted(PACKAGE_DIR.glob("*.md")))
    return [path for path in paths if path.exists()]


def build_public_site_readiness(generated_at: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    for path in public_page_paths():
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        has_placeholder = "placeholder" in lower or "draft case overview" in lower or "draft x-case" in lower
        has_draft_signal = "draft" in lower or "provisional" in lower or "pending" in lower
        if has_placeholder and not has_draft_signal:
            status = "placeholder-unmarked"
            blockers.append(rel(path))
        elif has_placeholder:
            status = "placeholder-marked-as-draft"
        elif has_draft_signal:
            status = "draft-or-provisional-marked"
        else:
            status = "no-draft-signal-detected"
        rows.append(
            {
                "path": rel(path),
                "status": status,
                "has_placeholder_signal": has_placeholder,
                "has_draft_or_pending_signal": has_draft_signal,
            }
        )

    report = {
        "version": "1.0",
        "generated_at": generated_at,
        "status": "pass" if not blockers else "needs-review",
        "policy": "Placeholder public pages must be visibly marked as draft, provisional, or pending.",
        "blockers": blockers,
        "pages": rows,
    }
    write_json(AUDIT_DIR / "public-site-readiness.json", report)

    md_rows = [
        {"path": row["path"], "status": row["status"]}
        for row in rows
    ]
    text = f"""---
title: "Public Site Readiness"
---

::: {{.callout-note}}
Generated by `scripts/generate-traceability-report.py` on {generated_at}.
:::

Status: **{report['status']}**.

Placeholder pages are acceptable only when they are visibly marked as draft,
provisional, or pending. This audit does not promote draft analysis to final
publication status.

## Page Signals

{markdown_table(md_rows, ["path", "status"])}
"""
    (PACKAGE_DIR / "public-site-readiness.md").write_text(text, encoding="utf-8")
    return report


def write_package_manifest(
    case_id: str,
    generated_at: str,
    traces: list[dict[str, Any]],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    components = package_components(case_id)
    missing = [item for item in components if item["status"] != "available"]
    manifest = {
        "version": "1.0",
        "case_id": case_id,
        "generated_at": generated_at,
        "status": "draft-review-package" if not missing else "incomplete",
        "source_issue": "#13",
        "package_policy": (
            "This package exposes the method, evidence, validation gate, AI-use "
            "statement, data-availability statement, and claim traceability "
            "needed for scholarly review."
        ),
        "components": components,
        "traceability": {
            "trace_count": len(traces),
            "json_path": "publication/audit/claim-traceability.json",
            "csv_path": "publication/audit/claim-traceability.csv",
            "public_page": "publication/claim-traceability.md",
        },
        "validation_gate": VALIDATION_GATE,
        "public_site_readiness": {
            "status": readiness.get("status"),
            "blockers": readiness.get("blockers", []),
            "report_path": "publication/audit/public-site-readiness.json",
        },
        "known_limitations": trace_limitations(case_id),
    }
    write_json(AUDIT_DIR / "publication-package.json", manifest)
    return manifest


def write_package_markdown(generated_at: str, manifest: dict[str, Any]) -> None:
    component_rows = [
        {
            "component": item["label"],
            "status": item["status"],
            "path": item["path"],
            "purpose": item["purpose"],
        }
        for item in manifest["components"]
    ]
    limitations = "\n".join(f"- {item}" for item in manifest.get("known_limitations", []))
    commands = "\n".join(f"- `{command}`" for command in manifest["validation_gate"])
    text = f"""---
title: "Publication Audit Package"
---

::: {{.callout-note}}
Generated by `scripts/generate-traceability-report.py` on {generated_at}.
:::

Status: **{manifest['status']}**.

This package assembles the method, evidence, traceability, AI-use disclosure,
data-availability statement, validation gate, and public-readiness audit for
scholarly review. It preserves draft boundaries rather than promoting the
Lincoln pilot analysis as final.

## Package Components

{markdown_table(component_rows, ["component", "status", "path", "purpose"])}

## Traceability

- Trace rows: `{manifest['traceability']['trace_count']}`
- JSON: `{manifest['traceability']['json_path']}`
- CSV: `{manifest['traceability']['csv_path']}`
- Public table: `{manifest['traceability']['public_page']}`

## Validation Gate

{commands}

## Public Site Readiness

Status: **{manifest['public_site_readiness']['status']}**.

Report: `{manifest['public_site_readiness']['report_path']}`

## Known Limitations

{limitations}
"""
    (PACKAGE_DIR / "audit-package.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default="lincoln", help="Case id to package")
    args = parser.parse_args()

    generated_at = now_iso()
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    write_ai_use_statement(generated_at)
    write_data_availability(generated_at)
    write_validation_gate(generated_at)
    write_mipvu_annotations_csv(args.case_id)
    write_cmt_mappings_csv(args.case_id)
    traces = build_trace_records(args.case_id, generated_at)
    write_trace_json(args.case_id, generated_at, traces)
    write_trace_csv(traces)
    write_trace_markdown(generated_at, traces)
    readiness = build_public_site_readiness(generated_at)
    manifest = write_package_manifest(args.case_id, generated_at, traces, readiness)
    write_package_markdown(generated_at, manifest)

    print(
        json.dumps(
            {
                "case_id": args.case_id,
                "status": manifest["status"],
                "trace_count": len(traces),
                "public_site_readiness": readiness["status"],
                "package_manifest": "publication/audit/publication-package.json",
            },
            indent=2,
        )
    )
    return 0 if manifest["status"] != "incomplete" and readiness["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
