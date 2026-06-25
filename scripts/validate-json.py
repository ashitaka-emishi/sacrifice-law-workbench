#!/usr/bin/env python3
"""Validate JSON pipeline artifacts for all cases."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Optional

from local_corpus_reference_index import (
    INDEX_VERSION,
    index_path as local_reference_index_path,
    iter_prohibited_fields,
    read_index as read_local_reference_index,
    sha256_json_artifact,
)
from pipeline_common import (
    ROOT,
    case_dir,
    case_ids,
    cmt_mappings_path_for,
    document_id,
    documents,
    get_nested,
    iter_cmt_mappings,
    iter_instances_from_annotated,
    iter_mipvu_records,
    iter_sentence_nodes,
    mipvu_path_for,
    read_json,
    segmented_path_for,
    valid_cluster_ids,
)
from model_reliability.status import evaluate_case
from human_reliability.status import evaluate_case as evaluate_human_case

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

RELIABILITY_DISAGREEMENT_CATEGORIES = {
    "lexical_segmentation",
    "contextual_meaning",
    "basic_meaning",
    "metaphor_decision",
    "confidence",
    "source_domain_ambiguity",
}

ADJUDICATION_LOG_REQUIRED = [
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
]

CMT_MAPPING_REQUIRED = [
    "mapping_id",
    "case_id",
    "document_id",
    "sentence_id",
    "mipvu_ids",
    "expression",
    "source_domain_primary",
    "target_domain",
    "conceptual_metaphor",
    "entailments",
    "cluster_id",
    "confidence",
    "rival_reading",
    "justification",
]

CMT_MAPPING_STATUSES = {"provisional", "reviewed", "accepted", "rejected", "exploratory"}

PUBLICATION_TRACE_REQUIRED = [
    "trace_id",
    "case_id",
    "claim_id",
    "claim_text",
    "claim_status",
    "support_dimension",
    "support_score_id",
    "support_score",
    "support_score_path",
    "mapping_id",
    "mipvu_ids",
    "sentence_id",
    "document_id",
    "source_url",
    "rights_status",
    "source_text_path",
]


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.notices: list[str] = []

    def error(self, path: Path, message: str) -> None:
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        self.errors.append(f"{rel}: {message}")

    def notice(self, path: Path, message: str) -> None:
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        self.notices.append(f"{rel}: {message}")

    @staticmethod
    def valid_sha256(value: Any) -> bool:
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )

    def validate_local_reference_index(
        self,
        case_id: str,
    ) -> tuple[set[str], dict[str, dict[str, Any]]]:
        path = local_reference_index_path(ROOT, case_id)
        try:
            data = read_local_reference_index(ROOT, case_id)
        except json.JSONDecodeError:
            return set(), {}
        if data is None:
            if path.exists():
                self.error(path, "public reference index must be an object")
            return set(), {}

        if data.get("version") != INDEX_VERSION:
            self.error(path, f"version must be `{INDEX_VERSION}`")
        if data.get("case_id") != case_id:
            self.error(path, f"case_id must be `{case_id}`")
        if data.get("status") != "public-safe-reference-index":
            self.error(path, "status must be `public-safe-reference-index`")
        for field_path in iter_prohibited_fields(data):
            self.error(path, f"public index contains prohibited source-derived field `{field_path}`")

        manifest_doc_records = {
            document_id(doc): doc for doc in documents(case_id) if document_id(doc)
        }
        manifest_docs = set(manifest_doc_records)
        artifacts = data.get("artifacts")
        if not isinstance(artifacts, list):
            self.error(path, "`artifacts` must be an array")
            artifacts = []
        seen_artifact_docs: set[str] = set()
        local_artifact_count = 0
        indexed_artifact_count = 0
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                self.error(path, f"artifacts[{index}] must be an object")
                continue
            doc_id = str(artifact.get("document_id") or "")
            if not doc_id or doc_id not in manifest_docs:
                self.error(path, f"artifacts[{index}] has unknown document_id `{doc_id}`")
            if doc_id in seen_artifact_docs:
                self.error(path, f"duplicate artifact document_id `{doc_id}`")
            seen_artifact_docs.add(doc_id)
            for field in ("segmented_artifact", "mipvu_artifact"):
                record = artifact.get(field)
                if not isinstance(record, dict):
                    self.error(path, f"{doc_id}: `{field}` must be an object")
                    continue
                rel_path = record.get("path")
                expected_hash = record.get("sha256")
                if not isinstance(rel_path, str) or not rel_path:
                    self.error(path, f"{doc_id}: `{field}.path` must be a string")
                    continue
                doc = manifest_doc_records.get(doc_id)
                if doc is not None:
                    expected_path = (
                        segmented_path_for(case_id, doc)
                        if field == "segmented_artifact"
                        else mipvu_path_for(case_id, doc)
                    ).relative_to(ROOT).as_posix()
                    if rel_path != expected_path:
                        self.error(
                            path,
                            f"{doc_id}: `{field}.path` must be `{expected_path}`",
                        )
                if not self.valid_sha256(expected_hash):
                    self.error(path, f"{doc_id}: `{field}.sha256` must be lowercase SHA-256")
                    continue
                indexed_artifact_count += 1
                artifact_path = (ROOT / rel_path).resolve()
                expected_root = (case_dir(case_id) / "corpus").resolve()
                if not artifact_path.is_relative_to(expected_root):
                    self.error(path, f"{doc_id}: `{field}.path` escapes the case corpus")
                    continue
                if artifact_path.is_file():
                    local_artifact_count += 1
                    actual_hash = sha256_json_artifact(artifact_path)
                    if actual_hash != expected_hash:
                        self.error(
                            artifact_path,
                            f"SHA-256 does not match public reference index `{expected_hash}`",
                        )
        for doc_id in sorted(manifest_docs - seen_artifact_docs):
            self.error(path, f"missing artifact record for `{doc_id}`")

        sentences = data.get("sentences")
        if not isinstance(sentences, list) or not sentences:
            self.error(path, "`sentences` must be a non-empty array")
            sentences = []
        sentence_ids: set[str] = set()
        sentence_docs: dict[str, str] = {}
        for index, sentence in enumerate(sentences):
            if not isinstance(sentence, dict):
                self.error(path, f"sentences[{index}] must be an object")
                continue
            sentence_id = str(sentence.get("sentence_id") or "")
            doc_id = str(sentence.get("document_id") or "")
            if not sentence_id:
                self.error(path, f"sentences[{index}] missing sentence_id")
                continue
            if sentence_id in sentence_ids:
                self.error(path, f"duplicate sentence_id `{sentence_id}`")
            sentence_ids.add(sentence_id)
            sentence_docs[sentence_id] = doc_id
            if doc_id not in manifest_docs:
                self.error(path, f"{sentence_id}: unknown document_id `{doc_id}`")
            if not self.valid_sha256(sentence.get("record_sha256")):
                self.error(path, f"{sentence_id}: record_sha256 must be lowercase SHA-256")

        units = data.get("mipvu_units")
        if not isinstance(units, list) or not units:
            self.error(path, "`mipvu_units` must be a non-empty array")
            units = []
        mipvu_lookup: dict[str, dict[str, Any]] = {}
        for index, unit in enumerate(units):
            if not isinstance(unit, dict):
                self.error(path, f"mipvu_units[{index}] must be an object")
                continue
            mipvu_id = str(unit.get("mipvu_id") or "")
            if not mipvu_id:
                self.error(path, f"mipvu_units[{index}] missing mipvu_id")
                continue
            if mipvu_id in mipvu_lookup:
                self.error(path, f"duplicate mipvu_id `{mipvu_id}`")
            mipvu_lookup[mipvu_id] = unit
            doc_id = str(unit.get("document_id") or "")
            sentence_id = str(unit.get("sentence_id") or "")
            if sentence_id not in sentence_ids:
                self.error(path, f"{mipvu_id}: unknown sentence_id `{sentence_id}`")
            elif sentence_docs.get(sentence_id) != doc_id:
                self.error(path, f"{mipvu_id}: document_id does not match indexed sentence")
            if unit.get("decision_type") not in MIPVU_METAPHOR_DECISIONS:
                self.error(path, f"{mipvu_id}: invalid indexed decision_type `{unit.get('decision_type')}`")
            if not self.valid_sha256(unit.get("record_sha256")):
                self.error(path, f"{mipvu_id}: record_sha256 must be lowercase SHA-256")

        if local_artifact_count == indexed_artifact_count and indexed_artifact_count:
            self.notice(path, "authorized local artifacts match the committed integrity hashes")
        elif local_artifact_count:
            self.error(
                path,
                (
                    f"partial local artifact restore: found {local_artifact_count} of "
                    f"{indexed_artifact_count} indexed artifacts"
                ),
            )
        else:
            self.notice(
                path,
                "local source-derived artifacts unavailable; references verified against the public-safe index",
            )
        return sentence_ids, mipvu_lookup

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

    def controlled_vocab_ids(self, section: str) -> set[str]:
        path = ROOT / "config" / "controlled-vocabularies.json"
        data = read_json(path, {}) or {}
        items = data.get(section, []) if isinstance(data, dict) else []
        return {str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")}

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
                if review_status != "pending" and decision is None:
                    self.error(path, f"{mipvu_id}: reviewed unit missing `decision_type`")
                    continue
                if decision is None:
                    if strict:
                        self.error(path, f"{mipvu_id}: missing `decision_type` in strict mode")
                    continue
                if decision not in MIPVU_DECISION_TYPES:
                    self.error(path, f"{mipvu_id}: invalid decision_type `{decision}`")
                    continue
                if decision != "non_metaphor" and review_status == "pending":
                    self.error(path, f"{mipvu_id}: `{decision}` cannot remain pending")
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
        for rel_path in [
            "analysis/concordance.json",
            "analysis/analysis.json",
            "analysis/corpus-analysis.json",
            "analysis/critical-metaphor-analysis.json",
            "analysis/rhetorical-genre-analysis.json",
            "analysis/absence-agency-analysis.json",
            "analysis/historical-enactment-alignment.json",
            "analysis/support-ratings.json",
            "analysis/koenigsbergian-support-synthesis.json",
        ]:
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

    def validate_mapping_id_list(
        self,
        path: Path,
        owner: str,
        values: Any,
        valid_mapping_ids: set[str],
    ) -> None:
        if not isinstance(values, list) or not values:
            self.error(path, f"{owner}: mapping ID list must be non-empty")
            return
        for mapping_id in values:
            if not isinstance(mapping_id, str) or not mapping_id:
                self.error(path, f"{owner}: mapping ID entries must be strings")
            elif mapping_id not in valid_mapping_ids:
                self.error(path, f"{owner}: mapping_id `{mapping_id}` not found")

    def validate_interpretive_artifacts(self, case_id: str, valid_mapping_ids: set[str]) -> None:
        analysis_dir = case_dir(case_id) / "analysis"

        critical_path = analysis_dir / "critical-metaphor-analysis.json"
        if critical_path.exists():
            data = read_json(critical_path, {}) or {}
            profiles = data.get("cluster_profiles") if isinstance(data, dict) else None
            if not isinstance(profiles, list) or not profiles:
                self.error(critical_path, "cluster_profiles must be a non-empty array")
            else:
                for index, profile in enumerate(profiles):
                    if not isinstance(profile, dict):
                        self.error(critical_path, f"cluster_profiles[{index}] must be an object")
                        continue
                    owner = str(profile.get("cluster_id") or f"cluster_profiles[{index}]")
                    self.validate_mapping_id_list(
                        critical_path, owner, profile.get("mapping_ids"), valid_mapping_ids
                    )
                    for field in [
                        "persuasive_function",
                        "rival_readings",
                        "negative_cases",
                        "relation_to_koenigsbergian_analysis",
                    ]:
                        if profile.get(field) in (None, "", []):
                            self.error(critical_path, f"{owner}: missing `{field}`")

        rhetorical_path = analysis_dir / "rhetorical-genre-analysis.json"
        if rhetorical_path.exists():
            data = read_json(rhetorical_path, {}) or {}
            contexts = data.get("contexts") if isinstance(data, dict) else None
            if not isinstance(contexts, list) or not contexts:
                self.error(rhetorical_path, "contexts must be a non-empty array")
            else:
                for index, context in enumerate(contexts):
                    if not isinstance(context, dict):
                        self.error(rhetorical_path, f"contexts[{index}] must be an object")
                        continue
                    mapping_id = context.get("mapping_id")
                    if mapping_id not in valid_mapping_ids:
                        self.error(rhetorical_path, f"contexts[{index}]: mapping_id `{mapping_id}` not found")
                    for field in ["audience", "occasion", "genre", "rhetorical_action", "agency_structure"]:
                        if context.get(field) in (None, "", {}):
                            self.error(rhetorical_path, f"{mapping_id or index}: missing `{field}`")

        absence_path = analysis_dir / "absence-agency-analysis.json"
        if absence_path.exists():
            data = read_json(absence_path, {}) or {}
            matrix = data.get("matrix") if isinstance(data, dict) else None
            if not isinstance(matrix, list) or not matrix:
                self.error(absence_path, "matrix must be a non-empty array")
            else:
                for index, row in enumerate(matrix):
                    if not isinstance(row, dict):
                        self.error(absence_path, f"matrix[{index}] must be an object")
                        continue
                    owner = str(row.get("absence_id") or f"matrix[{index}]")
                    self.validate_mapping_id_list(
                        absence_path, owner, row.get("evidence_mapping_ids"), valid_mapping_ids
                    )
                    for field in ["expected_presence", "possible_absence", "displacement_mechanism", "claim_boundary"]:
                        if row.get(field) in (None, ""):
                            self.error(absence_path, f"{owner}: missing `{field}`")

    def validate_support_artifacts(self, case_id: str, valid_mapping_ids: set[str]) -> None:
        analysis_dir = case_dir(case_id) / "analysis"
        historical_note_ids: set[str] = set()

        historical_path = analysis_dir / "historical-enactment-alignment.json"
        if historical_path.exists():
            data = read_json(historical_path, {}) or {}
            notes = data.get("notes") if isinstance(data, dict) else None
            if not isinstance(notes, list) or not notes:
                self.error(historical_path, "notes must be a non-empty array")
            else:
                for index, note in enumerate(notes):
                    if not isinstance(note, dict):
                        self.error(historical_path, f"notes[{index}] must be an object")
                        continue
                    note_id = str(note.get("note_id") or "")
                    if not note_id:
                        self.error(historical_path, f"notes[{index}] missing note_id")
                        continue
                    historical_note_ids.add(note_id)
                    self.validate_mapping_id_list(
                        historical_path, note_id, note.get("linked_mapping_ids"), valid_mapping_ids
                    )
                    for field in ["topic", "summary", "corroboration_status", "claim_boundary"]:
                        if note.get(field) in (None, ""):
                            self.error(historical_path, f"{note_id}: missing `{field}`")

        ratings_path = analysis_dir / "support-ratings.json"
        if ratings_path.exists():
            data = read_json(ratings_path, {}) or {}
            if not isinstance(data, dict):
                self.error(ratings_path, "support ratings must be an object")
            else:
                for container_name in ["document_ratings"]:
                    ratings = data.get(container_name)
                    if not isinstance(ratings, list) or not ratings:
                        self.error(ratings_path, f"{container_name} must be a non-empty array")
                        continue
                    for index, rating in enumerate(ratings):
                        if not isinstance(rating, dict):
                            self.error(ratings_path, f"{container_name}[{index}] must be an object")
                            continue
                        score_id = str(rating.get("score_id") or f"{container_name}[{index}]")
                        scores = rating.get("scores")
                        if not isinstance(scores, dict):
                            self.error(ratings_path, f"{score_id}: missing scores object")
                        else:
                            for dimension in [
                                "sacred_object",
                                "sacrificial_body",
                                "enemy_as_bringer_of_death",
                                "historical_enactment_alignment",
                            ]:
                                value = scores.get(dimension)
                                if not isinstance(value, (int, float)) or value < 0 or value > 4:
                                    self.error(ratings_path, f"{score_id}: invalid `{dimension}` score")
                        self.validate_mapping_id_list(
                            ratings_path, score_id, rating.get("mapping_ids"), valid_mapping_ids
                        )
                        note_ids = rating.get("historical_note_ids", [])
                        if not isinstance(note_ids, list) or not note_ids:
                            self.error(ratings_path, f"{score_id}: historical_note_ids must be non-empty")
                        for note_id in note_ids:
                            if historical_note_ids and note_id not in historical_note_ids:
                                self.error(ratings_path, f"{score_id}: historical_note_id `{note_id}` not found")

                case_scores = data.get("case_scores")
                if not isinstance(case_scores, dict):
                    self.error(ratings_path, "missing case_scores object")
                else:
                    for dimension, value in case_scores.items():
                        if not isinstance(value, (int, float)) or value < 0 or value > 4:
                            self.error(ratings_path, f"case_scores.{dimension} must be in [0, 4]")
                overall = data.get("overall_support")
                if not isinstance(overall, dict) or "score" not in overall or "final_category" not in overall:
                    self.error(ratings_path, "missing overall_support score/category")

        csv_path = analysis_dir / "support-ratings.csv"
        if csv_path.exists():
            try:
                with csv_path.open(newline="", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    required = {
                        "score_id",
                        "level",
                        "sacred_object",
                        "sacrificial_body",
                        "enemy_as_bringer_of_death",
                        "historical_enactment_alignment",
                    }
                    missing = sorted(required - set(reader.fieldnames or []))
                    if missing:
                        self.error(csv_path, f"missing column(s): {', '.join(missing)}")
            except csv.Error as exc:
                self.error(csv_path, f"CSV parse error: {exc}")

        synthesis_path = analysis_dir / "koenigsbergian-support-synthesis.json"
        if synthesis_path.exists():
            data = read_json(synthesis_path, {}) or {}
            if not isinstance(data, dict):
                self.error(synthesis_path, "synthesis must be an object")
            else:
                for field in ["support_summary", "support_statement", "claim_boundary"]:
                    if data.get(field) in (None, "", {}):
                        self.error(synthesis_path, f"missing `{field}`")

    def validate_x_case_artifacts(self) -> None:
        x_dir = ROOT / "cases" / "x-case"
        protocol_path = x_dir / "protocol" / "comparative-analysis-protocol.json"
        if protocol_path.exists():
            data = read_json(protocol_path, {}) or {}
            if not isinstance(data, dict):
                self.error(protocol_path, "comparative protocol must be an object")
            else:
                dimensions = data.get("dimensions")
                guardrails = data.get("guardrails")
                if not isinstance(dimensions, list) or len(dimensions) < 4:
                    self.error(protocol_path, "dimensions must contain comparative dimensions")
                if not isinstance(guardrails, list) or len(guardrails) < 4:
                    self.error(protocol_path, "guardrails must contain explicit comparison cautions")
                guardrail_text = " ".join(str(item).lower() for item in guardrails or [])
                for phrase in ["moral equivalence", "historically contextualized", "enemy construction"]:
                    if phrase not in guardrail_text:
                        self.error(protocol_path, f"guardrails missing `{phrase}` caution")

        comparison_path = x_dir / "synthesis" / "case-comparison.json"
        if comparison_path.exists():
            data = read_json(comparison_path, {}) or {}
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list) or not items:
                self.error(comparison_path, "items must be a non-empty array")
            else:
                for index, item in enumerate(items):
                    if not isinstance(item, dict):
                        self.error(comparison_path, f"items[{index}] must be an object")
                        continue
                    for field in ["case_id", "status", "support_rating", "claim_boundary"]:
                        if item.get(field) in (None, ""):
                            self.error(comparison_path, f"items[{index}] missing `{field}`")

    def validate_publication_package(self) -> None:
        manifest_path = ROOT / "publication" / "audit" / "publication-package.json"
        trace_path = ROOT / "publication" / "audit" / "claim-traceability.json"
        readiness_path = ROOT / "publication" / "audit" / "public-site-readiness.json"

        if not manifest_path.exists():
            self.error(manifest_path, "publication package manifest is required")
            return

        manifest = read_json(manifest_path, {}) or {}
        if not isinstance(manifest, dict):
            self.error(manifest_path, "publication package manifest must be an object")
            return

        case_id = str(manifest.get("case_id") or "")
        if not case_id:
            self.error(manifest_path, "missing case_id")
            return

        components = manifest.get("components")
        if not isinstance(components, list) or not components:
            self.error(manifest_path, "components must be a non-empty array")
        else:
            for index, component in enumerate(components):
                if not isinstance(component, dict):
                    self.error(manifest_path, f"components[{index}] must be an object")
                    continue
                component_id = component.get("component_id") or f"components[{index}]"
                if component.get("status") != "available":
                    self.error(manifest_path, f"{component_id}: component is not available")
                files = component.get("files", [])
                if not isinstance(files, list) or not files:
                    self.error(manifest_path, f"{component_id}: files must be a non-empty array")
                    continue
                for rel_path in files:
                    path = ROOT / str(rel_path)
                    if not path.exists() or path.stat().st_size == 0:
                        self.error(manifest_path, f"{component_id}: file `{rel_path}` is missing or empty")

        trace = read_json(trace_path, {}) or {}
        if not isinstance(trace, dict):
            self.error(trace_path, "claim traceability document must be an object")
            return
        if trace.get("case_id") != case_id:
            self.error(trace_path, f"case_id must be `{case_id}`")

        traces = trace.get("traces")
        if not isinstance(traces, list) or not traces:
            self.error(trace_path, "traces must be a non-empty array")
            return

        doc_ids = {document_id(doc) for doc in documents(case_id)}
        sentence_ids: set[str] = set()
        for doc in documents(case_id):
            segmented = read_json(segmented_path_for(case_id, doc), {}) or {}
            if isinstance(segmented, dict):
                sentence_ids.update(
                    str(sentence.get("sentence_id"))
                    for sentence in iter_sentence_nodes(segmented)
                    if sentence.get("sentence_id")
                )

        mipvu_ids: set[str] = set()
        for doc in documents(case_id):
            mipvu_doc = read_json(mipvu_path_for(case_id, doc), {}) or {}
            if isinstance(mipvu_doc, dict):
                mipvu_ids.update(
                    str(unit.get("mipvu_id"))
                    for unit in iter_mipvu_records(mipvu_doc)
                    if unit.get("mipvu_id")
                )

        cmt_data = read_json(cmt_mappings_path_for(case_id), {}) or {}
        mapping_ids = {
            str(mapping.get("mapping_id"))
            for mapping in iter_cmt_mappings(cmt_data)
            if mapping.get("mapping_id")
        }
        claim_status_ids = self.controlled_vocab_ids("claim_statuses")
        support_dimension_ids = self.controlled_vocab_ids("support_dimensions")

        seen_trace_ids: set[str] = set()
        for index, item in enumerate(traces):
            if not isinstance(item, dict):
                self.error(trace_path, f"traces[{index}] must be an object")
                continue
            trace_id = str(item.get("trace_id") or f"traces[{index}]")
            if trace_id in seen_trace_ids:
                self.error(trace_path, f"duplicate trace_id `{trace_id}`")
            seen_trace_ids.add(trace_id)

            for field in PUBLICATION_TRACE_REQUIRED:
                if item.get(field) in (None, "", []):
                    self.error(trace_path, f"{trace_id}: missing `{field}`")

            if item.get("case_id") != case_id:
                self.error(trace_path, f"{trace_id}: case_id must be `{case_id}`")
            if claim_status_ids and item.get("claim_status") not in claim_status_ids:
                self.error(trace_path, f"{trace_id}: invalid claim_status `{item.get('claim_status')}`")
            if support_dimension_ids and item.get("support_dimension") not in support_dimension_ids:
                self.error(trace_path, f"{trace_id}: invalid support_dimension `{item.get('support_dimension')}`")

            support_score = item.get("support_score")
            if not isinstance(support_score, (int, float)) or support_score < 0 or support_score > 4:
                self.error(trace_path, f"{trace_id}: support_score must be in [0, 4]")

            mapping_id = item.get("mapping_id")
            if mapping_id not in mapping_ids:
                self.error(trace_path, f"{trace_id}: mapping_id `{mapping_id}` not found")

            values = item.get("mipvu_ids")
            if not isinstance(values, list) or not values:
                self.error(trace_path, f"{trace_id}: mipvu_ids must be a non-empty array")
            else:
                for mipvu_id in values:
                    if mipvu_id not in mipvu_ids:
                        self.error(trace_path, f"{trace_id}: mipvu_id `{mipvu_id}` not found")

            sentence_id = item.get("sentence_id")
            if sentence_id not in sentence_ids:
                self.error(trace_path, f"{trace_id}: sentence_id `{sentence_id}` not found")
            document = item.get("document_id")
            if document not in doc_ids:
                self.error(trace_path, f"{trace_id}: document_id `{document}` not found")

            for rel_path in [item.get("support_score_path"), item.get("source_text_path")]:
                path = ROOT / str(rel_path)
                if not path.exists() or path.stat().st_size == 0:
                    self.error(trace_path, f"{trace_id}: referenced file `{rel_path}` is missing or empty")

            upstream = item.get("upstream_artifacts", [])
            if not isinstance(upstream, list) or not upstream:
                self.error(trace_path, f"{trace_id}: upstream_artifacts must be a non-empty array")
            else:
                for rel_path in upstream:
                    path = ROOT / str(rel_path)
                    if not path.exists() or path.stat().st_size == 0:
                        self.error(trace_path, f"{trace_id}: upstream artifact `{rel_path}` is missing or empty")

            if item.get("support_dimension") == "historical_enactment_alignment" and not item.get(
                "historical_corroboration"
            ):
                self.error(trace_path, f"{trace_id}: historical trace missing historical_corroboration")

        readiness = read_json(readiness_path, {}) or {}
        if not isinstance(readiness, dict):
            self.error(readiness_path, "public-site readiness report must be an object")
        elif readiness.get("status") != "pass":
            self.error(readiness_path, f"public-site readiness status is `{readiness.get('status')}`")
        elif readiness.get("blockers"):
            self.error(readiness_path, "public-site readiness blockers must be resolved")

    def validate_reliability_artifacts(
        self,
        case_id: str,
        sentence_ids: set[str],
        mipvu_lookup: dict[str, dict[str, Any]],
    ) -> None:
        quality_dir = case_dir(case_id) / "quality"
        sample_path = quality_dir / "reliability-sample.json"
        if sample_path.exists():
            sample = read_json(sample_path, {}) or {}
            if not isinstance(sample, dict):
                self.error(sample_path, "reliability sample must be an object")
            elif sample.get("case_id") != case_id:
                self.error(sample_path, f"case_id must be `{case_id}`")
            else:
                required_categories = set(sample.get("disagreement_categories", []))
                missing_categories = sorted(RELIABILITY_DISAGREEMENT_CATEGORIES - required_categories)
                if missing_categories:
                    self.error(sample_path, f"missing disagreement categories: {', '.join(missing_categories)}")

                reliability_sample = sample.get("reliability_sample", {})
                sentences = reliability_sample.get("sampled_sentences") if isinstance(reliability_sample, dict) else None
                if not isinstance(sentences, list) or not sentences:
                    self.error(sample_path, "reliability_sample.sampled_sentences must be a non-empty array")
                else:
                    total_units = 0
                    sentence_counts: dict[str, int] = {}
                    for unit in mipvu_lookup.values():
                        sid = str(unit.get("sentence_id") or "")
                        if sid:
                            sentence_counts[sid] = sentence_counts.get(sid, 0) + 1
                    for index, sentence in enumerate(sentences):
                        if not isinstance(sentence, dict):
                            self.error(sample_path, f"sampled_sentences[{index}] must be an object")
                            continue
                        sentence_id = str(sentence.get("sentence_id") or "")
                        if not sentence_id:
                            self.error(sample_path, f"sampled_sentences[{index}] missing sentence_id")
                            continue
                        if sentence_id not in sentence_ids:
                            self.error(sample_path, f"{sentence_id}: not found in segmented docs")
                        expected_count = sentence_counts.get(sentence_id)
                        recorded_count = sentence.get("lexical_unit_count")
                        if not isinstance(recorded_count, int):
                            self.error(sample_path, f"{sentence_id}: lexical_unit_count must be an integer")
                        elif expected_count is not None and recorded_count != expected_count:
                            self.error(
                                sample_path,
                                f"{sentence_id}: lexical_unit_count {recorded_count} does not match MIPVU count {expected_count}",
                            )
                        if isinstance(recorded_count, int):
                            total_units += recorded_count
                    recorded_total = reliability_sample.get("sample_lexical_units")
                    if isinstance(recorded_total, int) and recorded_total != total_units:
                        self.error(
                            sample_path,
                            f"sample_lexical_units {recorded_total} does not match sampled sentence total {total_units}",
                        )
                    sample_rate = reliability_sample.get("sample_rate")
                    if sample_rate is not None and (
                        not isinstance(sample_rate, (int, float)) or sample_rate <= 0 or sample_rate > 1
                    ):
                        self.error(sample_path, "sample_rate must be in (0, 1]")

            report_path = quality_dir / "reliability-report.md"
            if not report_path.exists() or not report_path.read_text(encoding="utf-8").strip():
                self.error(report_path, "reliability report is required when reliability-sample.json exists")

        log_path = quality_dir / "adjudication-log.csv"
        if log_path.exists():
            try:
                with log_path.open(newline="", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    missing_columns = [
                        field for field in ADJUDICATION_LOG_REQUIRED if field not in (reader.fieldnames or [])
                    ]
                    if missing_columns:
                        self.error(log_path, f"missing column(s): {', '.join(missing_columns)}")
                        return
                    for index, row in enumerate(reader, start=2):
                        mipvu_id = (row.get("mipvu_id") or "").strip()
                        if not mipvu_id:
                            self.error(log_path, f"row {index}: missing mipvu_id")
                            continue
                        unit = mipvu_lookup.get(mipvu_id)
                        if not unit:
                            self.error(log_path, f"row {index}: mipvu_id `{mipvu_id}` not found")
                            continue
                        for field in ["document_id", "sentence_id", "lexical_unit"]:
                            if (row.get(field) or "").strip() != str(unit.get(field, "")).strip():
                                self.error(log_path, f"row {index}: `{field}` does not match MIPVU unit")
                        category = (row.get("disagreement_category") or "").strip()
                        if category and category not in RELIABILITY_DISAGREEMENT_CATEGORIES:
                            self.error(log_path, f"row {index}: invalid disagreement_category `{category}`")
                        for field in ["coder_a_decision", "coder_b_decision", "adjudicated_decision"]:
                            decision = (row.get(field) or "").strip()
                            if decision and decision not in MIPVU_DECISION_TYPES:
                                self.error(log_path, f"row {index}: invalid {field} `{decision}`")
            except csv.Error as exc:
                self.error(log_path, f"CSV parse error: {exc}")

    def validate_cmt_mappings(
        self,
        case_id: str,
        sentence_ids: set[str],
        mipvu_lookup: dict[str, dict[str, Any]],
    ) -> None:
        path = cmt_mappings_path_for(case_id)
        if not path.exists():
            return

        source_domain_ids = self.controlled_vocab_ids("source_domains")
        target_domain_ids = self.controlled_vocab_ids("target_domains")
        cluster_ids = valid_cluster_ids(case_id)
        data = read_json(path, {}) or {}
        if not isinstance(data, dict):
            self.error(path, "CMT mapping document must be an object")
            return
        if data.get("case_id") != case_id:
            self.error(path, f"case_id must be `{case_id}`")
        mappings = list(iter_cmt_mappings(data))
        if not mappings:
            self.error(path, "`mappings` must contain at least one mapping")
            return

        seen: set[str] = set()
        for index, mapping in enumerate(mappings):
            mapping_id = str(mapping.get("mapping_id") or "")
            if not mapping_id:
                self.error(path, f"mappings[{index}] missing `mapping_id`")
                continue
            if mapping_id in seen:
                self.error(path, f"duplicate mapping_id `{mapping_id}`")
            seen.add(mapping_id)

            for field in CMT_MAPPING_REQUIRED:
                if field not in mapping or mapping.get(field) in (None, "", []):
                    self.error(path, f"{mapping_id}: missing `{field}`")

            if mapping.get("case_id") != case_id:
                self.error(path, f"{mapping_id}: case_id must be `{case_id}`")
            if str(mapping.get("sentence_id") or "") not in sentence_ids:
                self.error(path, f"{mapping_id}: sentence_id not found in segmented docs")

            status = mapping.get("mapping_status")
            if status is not None and status not in CMT_MAPPING_STATUSES:
                self.error(path, f"{mapping_id}: invalid mapping_status `{status}`")

            cluster_id = mapping.get("cluster_id")
            if cluster_id and str(cluster_id) not in cluster_ids:
                self.error(path, f"{mapping_id}: invalid cluster_id `{cluster_id}`")

            source_primary = mapping.get("source_domain_primary")
            if source_primary and source_domain_ids and str(source_primary) not in source_domain_ids:
                self.error(path, f"{mapping_id}: invalid source_domain_primary `{source_primary}`")
            source_secondary = mapping.get("source_domain_secondary", [])
            secondary_values = source_secondary if isinstance(source_secondary, list) else [source_secondary]
            for value in secondary_values:
                if value and source_domain_ids and str(value) not in source_domain_ids:
                    self.error(path, f"{mapping_id}: invalid source_domain_secondary `{value}`")

            target_domain = mapping.get("target_domain")
            if target_domain and target_domain_ids and str(target_domain) not in target_domain_ids:
                self.error(path, f"{mapping_id}: invalid target_domain `{target_domain}`")

            entailments = mapping.get("entailments")
            if not isinstance(entailments, list) or not all(isinstance(item, str) and item for item in entailments):
                self.error(path, f"{mapping_id}: entailments must be a non-empty string array")

            confidence = mapping.get("confidence")
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                self.error(path, f"{mapping_id}: confidence must be in [0, 1]")

            mipvu_ids = mapping.get("mipvu_ids")
            if not isinstance(mipvu_ids, list) or not mipvu_ids:
                self.error(path, f"{mapping_id}: mipvu_ids must be a non-empty array")
                continue
            for mipvu_id in mipvu_ids:
                if not isinstance(mipvu_id, str) or not mipvu_id:
                    self.error(path, f"{mapping_id}: mipvu_ids entries must be strings")
                    continue
                unit = mipvu_lookup.get(mipvu_id)
                if not unit:
                    self.error(path, f"{mapping_id}: mipvu_id `{mipvu_id}` not found")
                    continue
                if unit.get("decision_type") not in MIPVU_METAPHOR_DECISIONS:
                    self.error(path, f"{mapping_id}: mipvu_id `{mipvu_id}` is not metaphor-related or uncertain")
                if mapping.get("document_id") and unit.get("document_id") != mapping.get("document_id"):
                    self.error(path, f"{mapping_id}: mipvu_id `{mipvu_id}` belongs to another document")
                if mapping.get("sentence_id") and unit.get("sentence_id") != mapping.get("sentence_id"):
                    self.error(path, f"{mapping_id}: mipvu_id `{mipvu_id}` belongs to another sentence")

    def validate_case(self, case_id: str, strict: bool = False) -> None:
        self.validate_manifest(case_id)
        self.validate_corpus_register(case_id)
        indexed_sentence_ids, indexed_mipvu_lookup = self.validate_local_reference_index(case_id)
        sentence_ids = self.validate_segmented(case_id) | indexed_sentence_ids
        mipvu_lookup = dict(indexed_mipvu_lookup)
        mipvu_lookup.update(self.validate_mipvu(case_id, sentence_ids, strict=strict))
        self.validate_reliability_artifacts(case_id, sentence_ids, mipvu_lookup)
        self.validate_cmt_mappings(case_id, sentence_ids, mipvu_lookup)
        cmt_data = read_json(cmt_mappings_path_for(case_id), {}) or {}
        valid_mapping_ids = {
            str(mapping.get("mapping_id"))
            for mapping in iter_cmt_mappings(cmt_data)
            if mapping.get("mapping_id")
        }
        self.validate_interpretive_artifacts(case_id, valid_mapping_ids)
        self.validate_support_artifacts(case_id, valid_mapping_ids)
        self.validate_annotated(case_id, sentence_ids, mipvu_lookup)
        self.validate_concordance_and_analysis(case_id)
        reliability = evaluate_case(ROOT, case_id)
        for message in reliability["errors"]:
            self.error(
                case_dir(case_id) / "quality" / "model-reliability",
                message,
            )
        if reliability["counts"]["invalid_submissions"]:
            self.error(
                case_dir(case_id) / "quality" / "model-reliability",
                (
                    f"{reliability['counts']['invalid_submissions']} invalid "
                    "model submission(s) are registered"
                ),
            )
        human_reliability = evaluate_human_case(ROOT, case_id)
        for message in human_reliability["errors"]:
            self.error(
                case_dir(case_id) / "quality" / "human-reliability",
                message,
            )
        if human_reliability["counts"]["invalid_submissions"]:
            self.error(
                case_dir(case_id) / "quality" / "human-reliability",
                (
                    f"{human_reliability['counts']['invalid_submissions']} invalid "
                    "human submission(s) are registered"
                ),
            )
        if human_reliability["counts"]["invalid_adjudications"]:
            self.error(
                case_dir(case_id) / "quality" / "human-reliability",
                (
                    f"{human_reliability['counts']['invalid_adjudications']} "
                    "invalid adjudication submission(s) are registered"
                ),
            )


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
    if args.case_id in (None, "x-case"):
        validator.validate_x_case_artifacts()
    if args.case_id is None:
        validator.validate_publication_package()

    if validator.errors:
        for error in validator.errors:
            print(f"ERROR: {error}")
        print(f"\nValidation failed with {len(validator.errors)} error(s).")
        return 1

    for notice in validator.notices:
        print(f"NOTICE: {notice}")
    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
