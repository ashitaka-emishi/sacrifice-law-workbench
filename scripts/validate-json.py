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
        sentence_ids = self.validate_segmented(case_id)
        mipvu_lookup = self.validate_mipvu(case_id, sentence_ids, strict=strict)
        self.validate_reliability_artifacts(case_id, sentence_ids, mipvu_lookup)
        self.validate_cmt_mappings(case_id, sentence_ids, mipvu_lookup)
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
