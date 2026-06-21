from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.local_corpus_reference_index import (
    iter_prohibited_fields,
    sha256_bytes,
    sha256_json_artifact,
)
from scripts.pipeline_common import (
    ROOT,
    documents,
    annotated_path_for,
    cmt_mappings_path_for,
    iter_cmt_mappings,
    iter_instances_from_annotated,
    read_json,
)


VALIDATOR_PATH = ROOT / "scripts" / "validate-json.py"
INDEX_PATH = ROOT / "cases" / "hitler" / "metadata" / "local-corpus-reference-index.json"


def load_validator_module():
    scripts_path = str(ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location("validate_json_reference_test", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_index(artifact_hash: str | None = None) -> dict:
    artifact_hash = artifact_hash or sha256_bytes(b"")
    record_hash = sha256_bytes(b"record")
    return {
        "version": "1.0",
        "case_id": "demo",
        "status": "public-safe-reference-index",
        "rights_boundary": {},
        "artifacts": [
            {
                "document_id": "demo-doc",
                "segmented_artifact": {
                    "path": "cases/demo/corpus/segmented/demo-doc.json",
                    "sha256": artifact_hash,
                },
                "mipvu_artifact": {
                    "path": "cases/demo/corpus/mipvu/demo-doc_mipvu.json",
                    "sha256": artifact_hash,
                },
            }
        ],
        "sentences": [
            {
                "sentence_id": "demo-doc_s01",
                "document_id": "demo-doc",
                "record_sha256": record_hash,
            }
        ],
        "mipvu_units": [
            {
                "mipvu_id": "demo-doc_s01_lu001",
                "document_id": "demo-doc",
                "sentence_id": "demo-doc_s01",
                "decision_type": "mipvu_indirect",
                "record_sha256": record_hash,
            }
        ],
    }


class LocalCorpusReferenceIndexTest(unittest.TestCase):
    def test_committed_index_is_text_free_and_complete(self) -> None:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        self.assertEqual([], list(iter_prohibited_fields(data)))
        self.assertEqual(8, len(data["artifacts"]))
        self.assertEqual(65, len(data["sentences"]))
        self.assertEqual(70, len(data["mipvu_units"]))

        expected_sentences: set[str] = set()
        expected_mipvu: set[str] = set()
        cmt = read_json(cmt_mappings_path_for("hitler"), {}) or {}
        for mapping in iter_cmt_mappings(cmt):
            expected_sentences.add(str(mapping["sentence_id"]))
            expected_mipvu.update(str(value) for value in mapping["mipvu_ids"])
        for doc in documents("hitler"):
            annotated = read_json(annotated_path_for("hitler", doc), {}) or {}
            for instance, container_sentence_id in iter_instances_from_annotated(annotated):
                expected_sentences.add(str(instance.get("sentence_id") or container_sentence_id))
                expected_mipvu.update(str(value) for value in instance.get("mipvu_ids", []))

        self.assertEqual(expected_sentences, {item["sentence_id"] for item in data["sentences"]})
        self.assertEqual(expected_mipvu, {item["mipvu_id"] for item in data["mipvu_units"]})

    def test_clean_checkout_uses_index_with_notice(self) -> None:
        module = load_validator_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "cases" / "demo" / "metadata" / "local-corpus-reference-index.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(fixture_index()), encoding="utf-8")
            with (
                patch.object(module, "ROOT", root),
                patch.object(module, "case_dir", lambda case_id: root / "cases" / case_id),
                patch.object(module, "documents", lambda case_id: [{"document_id": "demo-doc"}]),
                patch.object(
                    module,
                    "segmented_path_for",
                    lambda case_id, doc: root / "cases" / case_id / "corpus" / "segmented" / "demo-doc.json",
                ),
                patch.object(
                    module,
                    "mipvu_path_for",
                    lambda case_id, doc: root / "cases" / case_id / "corpus" / "mipvu" / "demo-doc_mipvu.json",
                ),
            ):
                validator = module.Validator()
                sentence_ids, lookup = validator.validate_local_reference_index("demo")
            self.assertEqual([], validator.errors)
            self.assertEqual({"demo-doc_s01"}, sentence_ids)
            self.assertIn("demo-doc_s01_lu001", lookup)
            self.assertTrue(any("public-safe index" in notice for notice in validator.notices))

    def test_index_rejects_unknown_sentence_relationship(self) -> None:
        module = load_validator_module()
        data = fixture_index()
        data["mipvu_units"][0]["sentence_id"] = "demo-doc_typo"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "cases" / "demo" / "metadata" / "local-corpus-reference-index.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(data), encoding="utf-8")
            with (
                patch.object(module, "ROOT", root),
                patch.object(module, "case_dir", lambda case_id: root / "cases" / case_id),
                patch.object(module, "documents", lambda case_id: [{"document_id": "demo-doc"}]),
                patch.object(
                    module,
                    "segmented_path_for",
                    lambda case_id, doc: root / "cases" / case_id / "corpus" / "segmented" / "demo-doc.json",
                ),
                patch.object(
                    module,
                    "mipvu_path_for",
                    lambda case_id, doc: root / "cases" / case_id / "corpus" / "mipvu" / "demo-doc_mipvu.json",
                ),
            ):
                validator = module.Validator()
                validator.validate_local_reference_index("demo")
            self.assertTrue(any("unknown sentence_id `demo-doc_typo`" in error for error in validator.errors))

    def test_authorized_local_artifact_hash_mismatch_fails(self) -> None:
        module = load_validator_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "cases" / "demo" / "metadata" / "local-corpus-reference-index.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(fixture_index("0" * 64)), encoding="utf-8")
            segmented = root / "cases" / "demo" / "corpus" / "segmented" / "demo-doc.json"
            mipvu = root / "cases" / "demo" / "corpus" / "mipvu" / "demo-doc_mipvu.json"
            segmented.parent.mkdir(parents=True)
            mipvu.parent.mkdir(parents=True)
            segmented.write_text("{}", encoding="utf-8")
            mipvu.write_text("{}", encoding="utf-8")
            with (
                patch.object(module, "ROOT", root),
                patch.object(module, "case_dir", lambda case_id: root / "cases" / case_id),
                patch.object(module, "documents", lambda case_id: [{"document_id": "demo-doc"}]),
                patch.object(
                    module,
                    "segmented_path_for",
                    lambda case_id, doc: root / "cases" / case_id / "corpus" / "segmented" / "demo-doc.json",
                ),
                patch.object(
                    module,
                    "mipvu_path_for",
                    lambda case_id, doc: root / "cases" / case_id / "corpus" / "mipvu" / "demo-doc_mipvu.json",
                ),
            ):
                validator = module.Validator()
                validator.validate_local_reference_index("demo")
            self.assertEqual(2, sum("SHA-256 does not match" in error for error in validator.errors))

    def test_artifact_hash_ignores_only_volatile_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "first.json"
            second = Path(temp_dir) / "second.json"
            first.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-01-01",
                        "raw_path": "/machine/a/source.txt",
                        "pipeline_log": [{"generated_at": "2026-01-01"}],
                        "sections": [{"text": "source-derived content"}],
                    }
                ),
                encoding="utf-8",
            )
            second.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-02-02",
                        "raw_path": "/machine/b/source.txt",
                        "pipeline_log": [{"generated_at": "2026-02-02"}],
                        "sections": [{"text": "source-derived content"}],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(sha256_json_artifact(first), sha256_json_artifact(second))
            second.write_text(
                json.dumps({"sections": [{"text": "changed source-derived content"}]}),
                encoding="utf-8",
            )
            self.assertNotEqual(sha256_json_artifact(first), sha256_json_artifact(second))

    def test_unknown_cmt_mipvu_id_still_fails(self) -> None:
        module = load_validator_module()
        mapping = {
            "mapping_id": "demo-cmt-1",
            "case_id": "demo",
            "document_id": "demo-doc",
            "sentence_id": "demo-doc_s01",
            "mipvu_ids": ["demo-doc_s01_lu999"],
            "expression": "invented",
            "source_domain_primary": "source",
            "target_domain": "target",
            "conceptual_metaphor": "TARGET IS SOURCE",
            "entailments": ["invented entailment"],
            "cluster_id": "demo-cluster",
            "confidence": 0.5,
            "rival_reading": "literal",
            "justification": "fixture",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cmt.json"
            path.write_text(json.dumps({"case_id": "demo", "mappings": [mapping]}), encoding="utf-8")
            with (
                patch.object(module, "cmt_mappings_path_for", lambda case_id: path),
                patch.object(module, "valid_cluster_ids", lambda case_id: {"demo-cluster"}),
            ):
                validator = module.Validator()
                validator.validate_cmt_mappings(
                    "demo",
                    {"demo-doc_s01"},
                    {
                        "demo-doc_s01_lu001": {
                            "document_id": "demo-doc",
                            "sentence_id": "demo-doc_s01",
                            "decision_type": "mipvu_indirect",
                        }
                    },
                )
            self.assertTrue(any("mipvu_id `demo-doc_s01_lu999` not found" in error for error in validator.errors))


if __name__ == "__main__":
    unittest.main()
