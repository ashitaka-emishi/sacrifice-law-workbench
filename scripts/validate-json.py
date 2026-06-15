#!/usr/bin/env python3
"""Validate JSON pipeline artifacts for all cases."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Optional

from pipeline_common import (
    ROOT,
    case_dir,
    case_ids,
    document_id,
    documents,
    get_nested,
    iter_instances_from_annotated,
    iter_mipvu_records,
    iter_sentence_nodes,
    mipvu_path_for,
    read_json,
    valid_cluster_ids,
)

MANIFEST_REQUIRED = [
    "document_id",
    "title",
    "date",
    "register",
    "source_url",
    "rights_status",
    "expected_raw_path",
    "analytical_priority",
]

CORPUS_REGISTER_REQUIRED = [
    "text_id",
    "title",
    "date",
    "period",
    "genre",
    "register",
    "source_edition",
    "source_url",
    "authorship_confidence",
    "editorial_status",
    "inclusion_rationale",
    "corpus_layer",
    "rights_status",
    "git_tracking",
    "expected_local_path",
]

MIPVU_DECISION_TYPES = {
    "non_metaphor",
    "mipvu_indirect",
    "mipvu_direct",
    "mipvu_implicit",
    "mipvu_personification",
    "uncertain",
    "excluded_nonlexical",
}

MIPVU_METAPHOR_DECISIONS = {
    "mipvu_indirect",
    "mipvu_direct",
    "mipvu_implicit",
    "mipvu_personification",
    "uncertain",
}

MIPVU_REQUIRED_RATIONALE = [
    "contextual_meaning",
    "basic_meaning",
    "basic_meaning_source",
    "contrast_explanation",
    "comparison_basis",
    "confidence",
    "review_notes",
]

MIPVU_REVIEW_STATUSES = {"pending", "needs_review", "reviewed", "accepted", "rejected"}

CONTROLLED_VOCABULARY_SECTIONS = [
    "source_domains",
    "target_domains",
    "rhetorical_functions",
    "ideological_functions",
    "semantic_shift_risk_values",
    "claim_statuses",
    "support_dimensions",
]


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, path: Path, message: str) -> None:
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        self.errors.append(f"{rel}: {message}")

    def validate_json_parseability(self) -> None:
        for root in [ROOT / "cases", ROOT / "schemas", ROOT / "status", ROOT / "config"]:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*.json")):
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    self.error(path, f"JSON parse error: {exc}")

    def validate_controlled_vocabularies(self) -> None:
        path = ROOT / "config" / "controlled-vocabularies.json"
        if not path.exists():
            return
        data = read_json(path, {}) or {}
        if not isinstance(data, dict):
            self.error(path, "controlled vocabularies must be an object")
            return
        for section in CONTROLLED_VOCABULARY_SECTIONS:
            items = data.get(section)
            if not isinstance(items, list) or not items:
                self.error(path, f"`{section}` must be a non-empty array")
                continue
            seen: set[str] = set()
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    self.error(path, f"{section}[{index}] must be an object")
                    continue
                vocab_id = str(item.get("id") or "")
                label = str(item.get("label") or "")
                if not vocab_id:
                    self.error(path, f"{section}[{index}] missing `id`")
                    continue
                if vocab_id in seen:
                    self.error(path, f"{section}: duplicate id `{vocab_id}`")
                seen.add(vocab_id)
                if not label:
                    self.error(path, f"{section}.{vocab_id}: missing `label`")

    def validate_manifest(self, case_id: str) -> None:
        path = case_dir(case_id) / "metadata" / "document-manifest.json"
        manifest = read_json(path, {}) or {}
        docs = manifest.get("documents")
        if not isinstance(docs, list):
            self.error(path, "`documents` must be an array")
            return
        seen: set[str] = set()
        for index, doc in enumerate(docs):
            if not isinstance(doc, dict):
                self.error(path, f"documents[{index}] must be an object")
                continue
            doc_id = document_id(doc)
            if not doc_id:
                self.error(path, f"documents[{index}] missing `document_id`")
                continue
            if doc_id in seen:
                self.error(path, f"duplicate document_id `{doc_id}`")
            seen.add(doc_id)
            for field in MANIFEST_REQUIRED:
                if field not in doc and not (field == "document_id" and "id" in doc):
                    self.error(path, f"{doc_id}: missing `{field}`")
            confidence = doc.get("authorship_confidence")
            if confidence is not None and (
                not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1
            ):
                self.error(path, f"{doc_id}: authorship_confidence must be in [0, 1]")

    def validate_corpus_register(self, case_id: str) -> None:
        path = case_dir(case_id) / "metadata" / "corpus-register.csv"
        if not path.exists():
            return

        manifest_docs = {document_id(doc): doc for doc in documents(case_id)}
        rows: list[dict[str, str]] = []
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                missing_columns = [
                    field for field in CORPUS_REGISTER_REQUIRED if field not in (reader.fieldnames or [])
                ]
                if missing_columns:
                    self.error(path, f"missing column(s): {', '.join(missing_columns)}")
                    return
                rows = [dict(row) for row in reader]
        except csv.Error as exc:
            self.error(path, f"CSV parse error: {exc}")
            return

        seen: set[str] = set()
        for index, row in enumerate(rows, start=2):
            text_id = (row.get("text_id") or "").strip()
            if not text_id:
                self.error(path, f"row {index}: missing `text_id`")
                continue
            if text_id in seen:
                self.error(path, f"duplicate text_id `{text_id}`")
            seen.add(text_id)
            if text_id not in manifest_docs:
                self.error(path, f"{text_id}: not found in document manifest")
                continue
            for field in CORPUS_REGISTER_REQUIRED:
                if field == "risk_flags":
                    continue
                if not (row.get(field) or "").strip():
                    self.error(path, f"{text_id}: missing `{field}`")
            doc = manifest_docs[text_id]
            for field in ["title", "date", "register", "source_url", "rights_status"]:
                if str(doc.get(field, "")).strip() != str(row.get(field, "")).strip():
                    self.error(path, f"{text_id}: `{field}` does not match document manifest")

        missing_from_register = sorted(set(manifest_docs) - seen)
        for text_id in missing_from_register:
            self.error(path, f"{text_id}: missing from corpus register")

    def validate_segmented(self, case_id: str) -> set[str]:
        sentence_ids: set[str] = set()
        for path in sorted((case_dir(case_id) / "corpus" / "segmented").glob("*.json")):
            data = read_json(path, {}) or {}
            if not isinstance(data, dict):
                self.error(path, "segmented document must be an object")
                continue
            if not data.get("document_id"):
                self.error(path, "missing `document_id`")
            if not isinstance(data.get("sections"), list):
                self.error(path, "missing `sections` array")
                continue
            local_ids: set[str] = set()
            for sent in iter_sentence_nodes(data):
                sent_id = sent.get("sentence_id")
                if not sent_id:
                    self.error(path, "sentence missing `sentence_id`")
                    continue
                if sent_id in local_ids:
                    self.error(path, f"duplicate sentence_id `{sent_id}`")
                local_ids.add(str(sent_id))
                sentence_ids.add(str(sent_id))
                if not isinstance(sent.get("metaphor_instances"), list):
                    self.error(path, f"{sent_id}: `metaphor_instances` must be an array")
                for offset in ["word_offset_start", "word_offset_end"]:
                    if not isinstance(sent.get(offset), int):
                        self.error(path, f"{sent_id}: `{offset}` must be an integer")
        return sentence_ids

    def validate_mipvu(
        self,
        case_id: str,
        sentence_ids: set[str],
        strict: bool = False,
    ) -> dict[str, dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = {}
        seen_files = 0
        docs = documents(case_id)

        for doc in docs:
            doc_id = document_id(doc)
            path = mipvu_path_for(case_id, doc)
            if not path.exists():
                if strict:
                    self.error(path, f"{doc_id}: missing MIPVU worklist")
                continue

            seen_files += 1
            data = read_json(path, {}) or {}
            if not isinstance(data, dict):
                self.error(path, "MIPVU document must be an object")
                continue
            if data.get("case_id") != case_id:
                self.error(path, f"case_id must be `{case_id}`")
            if data.get("document_id") != doc_id:
                self.error(path, f"document_id must be `{doc_id}`")
            units = data.get("lexical_units")
            if not isinstance(units, list):
                self.error(path, "`lexical_units` must be an array")
                continue

            local_ids: set[str] = set()
            for unit in iter_mipvu_records(data):
                mipvu_id = str(unit.get("mipvu_id") or "")
                if not mipvu_id:
                    self.error(path, "lexical unit missing `mipvu_id`")
                    continue
                if mipvu_id in local_ids:
                    self.error(path, f"duplicate mipvu_id `{mipvu_id}`")
                local_ids.add(mipvu_id)
                lookup[mipvu_id] = unit

                for field in [
                    "case_id",
                    "document_id",
                    "sentence_id",
                    "lexical_unit",
                    "lemma",
                    "language",
                    "char_offset_start",
                    "char_offset_end",
                    "review_status",
                ]:
                    if field not in unit or unit.get(field) in (None, ""):
                        self.error(path, f"{mipvu_id}: missing `{field}`")

                if unit.get("case_id") != case_id:
                    self.error(path, f"{mipvu_id}: case_id must be `{case_id}`")
                if unit.get("document_id") != doc_id:
                    self.error(path, f"{mipvu_id}: document_id must be `{doc_id}`")
                sentence_id = str(unit.get("sentence_id") or "")
                if sentence_id and sentence_id not in sentence_ids:
                    self.error(path, f"{mipvu_id}: sentence_id `{sentence_id}` not found in segmented docs")
                for offset in ["char_offset_start", "char_offset_end"]:
                    if not isinstance(unit.get(offset), int):
                        self.error(path, f"{mipvu_id}: `{offset}` must be an integer")
                if (
                    isinstance(unit.get("char_offset_start"), int)
                    and isinstance(unit.get("char_offset_end"), int)
                    and unit["char_offset_end"] < unit["char_offset_start"]
                ):
                    self.error(path, f"{mipvu_id}: char_offset_end precedes char_offset_start")

                review_status = unit.get("review_status")
                if review_status not in MIPVU_REVIEW_STATUSES:
                    self.error(path, f"{mipvu_id}: review_status has unexpected value `{review_status}`")

                decision = unit.get("decision_type")
                if decision is None:
                    if strict:
                        self.error(path, f"{mipvu_id}: missing `decision_type` in strict mode")
                    continue
                if decision not in MIPVU_DECISION_TYPES:
                    self.error(path, f"{mipvu_id}: invalid decision_type `{decision}`")
                    continue
                if decision in MIPVU_METAPHOR_DECISIONS:
                    for field in MIPVU_REQUIRED_RATIONALE:
                        if unit.get(field) in (None, ""):
                            self.error(path, f"{mipvu_id}: `{field}` required for {decision}")
                    confidence = unit.get("confidence")
                    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                        self.error(path, f"{mipvu_id}: confidence must be in [0, 1]")

        if strict and docs and seen_files == 0:
            self.error(case_dir(case_id) / "corpus" / "mipvu", f"{case_id}: no MIPVU worklists found")

        return lookup

    def validate_instance(
        self,
        path: Path,
        case_id: str,
        inst: dict[str, Any],
        container_sentence_id: Optional[str],
        sentence_ids: set[str],
        mipvu_lookup: dict[str, dict[str, Any]],
    ) -> None:
        instance_id = inst.get("instance_id")
        if not instance_id:
            self.error(path, "annotation missing `instance_id`")
        sentence_id = inst.get("sentence_id") or container_sentence_id
        if not sentence_id:
            self.error(path, f"{instance_id or 'unknown'}: missing `sentence_id`")
        elif sentence_ids and str(sentence_id) not in sentence_ids:
            self.error(path, f"{instance_id or 'unknown'}: sentence_id `{sentence_id}` not found in segmented docs")
        if container_sentence_id and inst.get("sentence_id") and inst["sentence_id"] != container_sentence_id:
            self.error(path, f"{instance_id or 'unknown'}: sentence_id does not match container sentence")
        for field in ["document_id", "span_text"]:
            if not inst.get(field):
                self.error(path, f"{instance_id or 'unknown'}: missing `{field}`")

        exploratory = get_nested(inst, "meta", "exploratory_without_mipvu") is True
        mipvu_ids = inst.get("mipvu_ids")
        if not exploratory:
            if not isinstance(mipvu_ids, list) or not mipvu_ids:
                self.error(path, f"{instance_id or 'unknown'}: missing non-empty `mipvu_ids`")
            else:
                for mipvu_id in mipvu_ids:
                    if not isinstance(mipvu_id, str) or not mipvu_id:
                        self.error(path, f"{instance_id or 'unknown'}: mipvu_ids entries must be strings")
                        continue
                    unit = mipvu_lookup.get(mipvu_id)
                    if not unit:
                        self.error(path, f"{instance_id or 'unknown'}: mipvu_id `{mipvu_id}` not found")
                        continue
                    if inst.get("document_id") and unit.get("document_id") != inst.get("document_id"):
                        self.error(path, f"{instance_id or 'unknown'}: mipvu_id `{mipvu_id}` belongs to another document")
                    if sentence_id and unit.get("sentence_id") != sentence_id:
                        self.error(path, f"{instance_id or 'unknown'}: mipvu_id `{mipvu_id}` belongs to another sentence")
                    if unit.get("decision_type") not in MIPVU_METAPHOR_DECISIONS:
                        self.error(
                            path,
                            f"{instance_id or 'unknown'}: mipvu_id `{mipvu_id}` is not metaphor-related or uncertain",
                        )
        cluster_id = get_nested(inst, "cmt", "cluster_id")
        if not cluster_id:
            self.error(path, f"{instance_id or 'unknown'}: missing `cmt.cluster_id`")
        elif cluster_id not in valid_cluster_ids(case_id):
            self.error(path, f"{instance_id or 'unknown'}: invalid cluster_id `{cluster_id}`")
        koenigsberg = inst.get("koenigsberg")
        if not isinstance(koenigsberg, dict):
            self.error(path, f"{instance_id or 'unknown'}: missing `koenigsberg` object")
        else:
            absence_flags = koenigsberg.get("absence_flags", [])
            if absence_flags is not None and not isinstance(absence_flags, list):
                self.error(path, f"{instance_id or 'unknown'}: `koenigsberg.absence_flags` must be an array")
            for boolean_field in ["obligatory_frame", "sacrificial_economy"]:
                value = koenigsberg.get(boolean_field)
                if value is not None and not isinstance(value, bool):
                    self.error(path, f"{instance_id or 'unknown'}: `{boolean_field}` must be boolean")
        confidence = get_nested(inst, "meta", "confidence")
        if confidence is None:
            self.error(path, f"{instance_id or 'unknown'}: missing `meta.confidence`")
        elif not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            self.error(path, f"{instance_id or 'unknown'}: meta.confidence must be in [0, 1]")

    def validate_annotated(
        self,
        case_id: str,
        sentence_ids: set[str],
        mipvu_lookup: dict[str, dict[str, Any]],
    ) -> None:
        for path in sorted((case_dir(case_id) / "corpus" / "annotated").glob("*_annotated.json")):
            data = read_json(path, {}) or {}
            if not isinstance(data, (dict, list)):
                self.error(path, "annotated file must be an object or list")
                continue
            for inst, container_sentence_id in iter_instances_from_annotated(data):
                self.validate_instance(path, case_id, inst, container_sentence_id, sentence_ids, mipvu_lookup)

    def validate_concordance_and_analysis(self, case_id: str) -> None:
        for rel_path in ["analysis/concordance.json", "analysis/analysis.json"]:
            path = case_dir(case_id) / rel_path
            if not path.exists():
                continue
            data = read_json(path, {}) or {}
            if not isinstance(data, dict):
                self.error(path, "artifact must be an object")
                continue
            if data.get("case_id") != case_id:
                self.error(path, f"case_id must be `{case_id}`")
            if data.get("status") not in {"stub", "complete", "ready", "error", "draft"}:
                self.error(path, "status has unexpected value")

    def validate_case(self, case_id: str, strict: bool = False) -> None:
        self.validate_manifest(case_id)
        self.validate_corpus_register(case_id)
        sentence_ids = self.validate_segmented(case_id)
        mipvu_lookup = self.validate_mipvu(case_id, sentence_ids, strict=strict)
        self.validate_annotated(case_id, sentence_ids, mipvu_lookup)
        self.validate_concordance_and_analysis(case_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", dest="case_id", default=None, help="Optional case id")
    parser.add_argument("--strict", action="store_true", help="Require completed MIPVU worklists")
    args = parser.parse_args()

    validator = Validator()
    validator.validate_json_parseability()
    validator.validate_controlled_vocabularies()
    for case_id in case_ids(args.case_id):
        validator.validate_case(case_id, strict=args.strict)

    if validator.errors:
        for error in validator.errors:
            print(f"ERROR: {error}")
        print(f"\nValidation failed with {len(validator.errors)} error(s).")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
