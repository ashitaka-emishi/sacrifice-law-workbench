from __future__ import annotations

import copy
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from scripts.model_reliability.generate_packets import generate_packets
from scripts.model_reliability.ingest_submission import (
    IngestionError,
    ingest_submission,
    parse_csv_submission,
    parse_json_submission,
)
from test.test_model_reliability_packets import fixture_root, write_json


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def ingestion_root(base: Path) -> Path:
    root = fixture_root(base)
    target_schemas = root / "schemas" / "model-reliability"
    target_schemas.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_ROOT / "schemas" / "model-reliability", target_schemas)
    write_json(
        root / "config" / "controlled-vocabularies.json",
        {
            "source_domains": [{"id": "body", "label": "body"}],
            "target_domains": [{"id": "nation", "label": "nation"}],
        },
    )
    write_json(
        root / "cases" / "demo" / "config" / "case-clusters.json",
        [{"id": "demo-cluster", "name": "Demo cluster"}],
    )
    generate_packets(root, "demo", revision="deadbeef")
    return root


def valid_submission(root: Path, suffix: str = "001") -> dict:
    packet_root = root / "cases" / "demo" / "quality" / "model-reliability" / "packets"
    manifest = json.loads((packet_root / "packet-manifest.json").read_text(encoding="utf-8"))
    prompt = next(item for item in manifest["prompts"] if item["task_layer"] == "cmt")
    packet_item = json.loads((packet_root / "cmt-packet.jsonl").read_text(encoding="utf-8"))
    item = copy.deepcopy(packet_item)
    item.update(
        {
            "cmt": {
                "source_domain_primary": "body",
                "source_domain_secondary": [],
                "target_domain": "nation",
                "conceptual_metaphor": "NATION IS BODY",
                "entailments": ["collective action supports the polity"],
                "cluster_id": "demo-cluster",
            },
            "confidence": 0.8,
            "uncertainty": {"status": "low", "note": "A literal reading remains possible."},
            "rival_reading": "A literal statement of support.",
            "case_fields": {},
        }
    )
    return {
        "schema_version": "1.0.0",
        "submission_id": f"submission-{suffix}",
        "case_id": "demo",
        "sample_id": manifest["sample_id"],
        "sample_version": manifest["sample_version"],
        "packet_id": manifest["packet_id"],
        "packet_hash": manifest["packet_hash"],
        "prompt_id": prompt["id"],
        "prompt_hash": prompt["hash"],
        "source_language": manifest["source_language"],
        "code_revision": manifest["code_revision"],
        "run": {
            "run_id": f"run-{suffix}",
            "provider": "manual-provider",
            "model": "manual-model",
            "model_version": None,
            "completed_at": "2026-06-18T12:00:00Z",
            "language_capabilities": ["fr", "en"],
            "settings": {"temperature": 0},
        },
        "items": [item],
    }


def corpus_snapshot(root: Path) -> dict[str, bytes]:
    case = root / "cases" / "demo"
    return {
        path.relative_to(case).as_posix(): path.read_bytes()
        for parent in ("metadata", "corpus", "analysis")
        for path in (case / parent).rglob("*")
        if path.is_file()
    }


def write_csv_submission(root: Path, submission: dict, directory: Path) -> tuple[Path, Path]:
    contract = json.loads(
        (root / "schemas" / "model-reliability" / "submission-csv-contract.json").read_text()
    )
    metadata_fields = contract["files"]["metadata"]["required_columns"]
    item_fields = contract["files"]["items"]["required_columns"]
    run = submission["run"]
    metadata = {
        **{field: submission.get(field, "") for field in metadata_fields},
        "run_id": run["run_id"],
        "provider": run["provider"],
        "model": run["model"],
        "model_version": run.get("model_version") or "",
        "completed_at": run["completed_at"],
        "language_capabilities": json.dumps(run["language_capabilities"], separators=(",", ":")),
        "settings": json.dumps(run["settings"], separators=(",", ":")),
    }
    json_fields = {
        "span_ids",
        "lexical_units",
        "source_risk_flags",
        "identification",
        "cmt",
        "interpretation",
        "uncertainty",
        "case_fields",
    }
    rows = []
    for item in submission["items"]:
        row = {}
        for field in item_fields:
            value = item.get(field, "")
            row[field] = json.dumps(value, ensure_ascii=False, separators=(",", ":")) if field in json_fields and value != "" else value
        rows.append(row)
    directory.mkdir(parents=True, exist_ok=True)
    metadata_path = directory / "metadata.csv"
    items_path = directory / "items.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=metadata_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerow(metadata)
    with items_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=item_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return metadata_path, items_path


class SubmissionIngestionTest(unittest.TestCase):
    def test_ingests_valid_json_and_preserves_protected_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = ingestion_root(base)
            source = base / "incoming.json"
            write_json(source, valid_submission(root))
            before = corpus_snapshot(root)

            report = ingest_submission(root, "demo", parse_json_submission(source))

            self.assertEqual(report["status"], "valid")
            self.assertEqual(report["errors"], [])
            self.assertEqual(before, corpus_snapshot(root))
            model_root = root / "cases" / "demo" / "quality" / "model-reliability"
            raw = model_root / "submissions" / "raw" / report["registration_id"] / "submission.json"
            self.assertEqual(raw.read_bytes(), source.read_bytes())
            normalized = json.loads(
                (model_root / "normalized" / "normalized-runs.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(normalized["runs"]), 1)

            for artifact, schema_name in (
                (report, "ingestion-report-schema.json"),
                (
                    json.loads((model_root / "submissions" / "submission-register.json").read_text()),
                    "submission-register-schema.json",
                ),
                (normalized, "normalized-runs-schema.json"),
            ):
                schema = json.loads((root / "schemas" / "model-reliability" / schema_name).read_text())
                Draft202012Validator(schema, format_checker=FormatChecker()).validate(artifact)

    def test_normalizes_valid_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = ingestion_root(base)
            metadata_path, items_path = write_csv_submission(
                root, valid_submission(root, "csv"), base / "incoming"
            )
            contract = json.loads(
                (root / "schemas" / "model-reliability" / "submission-csv-contract.json").read_text()
            )

            parsed = parse_csv_submission(metadata_path, items_path, contract)
            report = ingest_submission(root, "demo", parsed)

            self.assertEqual(report["status"], "valid")
            self.assertEqual(parsed.envelope["run"]["model_version"], None)
            self.assertIsInstance(parsed.envelope["items"][0]["cmt"], dict)
            self.assertEqual(len(report["raw_item_rows"]), 1)

    def test_invalid_csv_rows_are_preserved_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = ingestion_root(base)
            submission = valid_submission(root, "bad-csv")
            submission["items"].append(copy.deepcopy(submission["items"][0]))
            unknown = copy.deepcopy(submission["items"][0])
            unknown["item_id"] = "unknown-item"
            unknown["span_ids"] = ["unknown-span"]
            unknown["lexical_units"][0]["span_id"] = "unknown-span"
            unknown["cmt"]["cluster_id"] = "unknown-cluster"
            submission["items"].append(unknown)
            metadata_path, items_path = write_csv_submission(root, submission, base / "incoming")
            with items_path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["cmt"] = "{"
            with items_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            contract = json.loads(
                (root / "schemas" / "model-reliability" / "submission-csv-contract.json").read_text()
            )

            report = ingest_submission(
                root, "demo", parse_csv_submission(metadata_path, items_path, contract)
            )

            self.assertEqual(report["status"], "invalid")
            self.assertEqual(len(report["raw_item_rows"]), 3)
            self.assertEqual(len(report["item_results"]), 3)
            self.assertTrue(any("invalid JSON cell" in error for error in report["errors"]))
            self.assertTrue(any("duplicate item ID" in error for error in report["errors"]))
            self.assertTrue(any("unknown packet item ID" in error for error in report["errors"]))
            self.assertTrue(any("unknown cluster ID" in error for error in report["errors"]))
            model_root = root / "cases" / "demo" / "quality" / "model-reliability"
            normalized = json.loads(
                (model_root / "normalized" / "normalized-runs.json").read_text(encoding="utf-8")
            )
            self.assertEqual(normalized["runs"], [])
            markdown = (
                model_root
                / "normalized"
                / "validation-reports"
                / f"{report['registration_id']}.md"
            ).read_text(encoding="utf-8")
            self.assertIn("## Errors", markdown)

    def test_rejects_packet_mismatch_and_incomplete_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = ingestion_root(base)
            submission = valid_submission(root, "mismatch")
            submission["packet_hash"] = "sha256:" + "0" * 64
            submission["items"] = []
            source = base / "mismatch.json"
            write_json(source, submission)

            report = ingest_submission(root, "demo", parse_json_submission(source))

            self.assertEqual(report["status"], "invalid")
            self.assertTrue(any("packet_hash" in error for error in report["errors"]))
            self.assertTrue(any("exactly one task layer" in error for error in report["errors"]))

    def test_identical_raw_input_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = ingestion_root(base)
            source = base / "same.json"
            write_json(source, valid_submission(root, "same"))

            first = ingest_submission(root, "demo", parse_json_submission(source))
            second = ingest_submission(root, "demo", parse_json_submission(source))

            self.assertEqual(first, second)
            register = json.loads(
                (
                    root
                    / "cases"
                    / "demo"
                    / "quality"
                    / "model-reliability"
                    / "submissions"
                    / "submission-register.json"
                ).read_text()
            )
            self.assertEqual(len(register["submissions"]), 1)
            raw_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "submissions"
                / "raw"
                / first["registration_id"]
                / "submission.json"
            )
            raw_path.chmod(0o644)
            raw_path.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(IngestionError, "raw registration was altered"):
                ingest_submission(root, "demo", parse_json_submission(source))

    def test_corrected_submission_can_reuse_ids_from_invalid_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = ingestion_root(base)
            corrected = valid_submission(root, "corrected")
            invalid = copy.deepcopy(corrected)
            invalid["packet_hash"] = "sha256:" + "0" * 64
            invalid_path = base / "invalid.json"
            corrected_path = base / "corrected.json"
            write_json(invalid_path, invalid)
            write_json(corrected_path, corrected)

            first = ingest_submission(root, "demo", parse_json_submission(invalid_path))
            second = ingest_submission(root, "demo", parse_json_submission(corrected_path))

            self.assertEqual(first["status"], "invalid")
            self.assertEqual(second["status"], "valid")

    def test_refuses_sensitive_input_before_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = ingestion_root(base)
            submission = valid_submission(root, "secret")
            submission["run"]["settings"] = {"api_key": "do-not-store"}
            source = base / "secret.json"
            write_json(source, submission)

            with self.assertRaisesRegex(IngestionError, "credentials"):
                ingest_submission(root, "demo", parse_json_submission(source))

            self.assertFalse(
                (
                    root
                    / "cases"
                    / "demo"
                    / "quality"
                    / "model-reliability"
                    / "submissions"
                ).exists()
            )


if __name__ == "__main__":
    unittest.main()
