from __future__ import annotations

import copy
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from scripts.human_reliability.generate_packets import (
    canonical_json_bytes,
    generate_packets,
    sha256_bytes,
)
from scripts.human_reliability.ingest_submission import (
    IngestionError,
    cohort_hash,
    cohort_ingestion_summary,
    ingest_submission,
    parse_csv_submission,
    parse_json_submission,
    refresh_ingestion_status,
)
from scripts.human_reliability.submission_contract import load_csv_contract
from test.test_human_reliability_packets import (
    ANNOTATION_ID,
    fixture_root,
    packet_dir,
    write_json,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def ingestion_root(base: Path, layer: str = "cmt") -> tuple[Path, Path]:
    span_id = ANNOTATION_ID if layer == "cmt" else None
    root, sample_path = fixture_root(base, layer, span_id)
    schema_target = root / "schemas" / "human-reliability"
    schema_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_ROOT / "schemas" / "human-reliability", schema_target)
    manifest = generate_packets(
        root,
        "demo",
        sample_path=sample_path,
        revision="fixture-human-ingestion-v1",
    )
    cohort = {
        "schema_version": "1.0.0",
        "status": "approved",
        "cohort_id": f"demo-fr-{layer}-cohort",
        "cohort_version": "1.0.0",
        "case_id": "demo",
        "sample_id": manifest["sample_id"],
        "sample_version": manifest["sample_version"],
        "packet_id": manifest["packet_id"],
        "packet_manifest": (
            packet_dir(root, layer) / "packet-manifest.json"
        ).relative_to(root / "cases" / "demo").as_posix(),
        "source_language": "fr",
        "task_layer": layer,
        "codebook_version": manifest["codebook_version"],
        "training_version": "human-training-v1",
        "calibration_id": "calibration-fr-v1",
        "required_primary_coders": 2,
        "primary_coder_ids": ["coder-fr-001", "coder-fr-002"],
        "ai_assistance_allowed": False,
        "storage_policy": "repository_allowed",
        "rights_constraints": manifest["rights_constraints"],
        "approval": {
            "approved_by": "fixture-coordinator",
            "approved_at": "2026-06-21T00:00:00Z",
            "manifest_sha256": None,
        },
    }
    cohort["approval"]["manifest_sha256"] = cohort_hash(cohort)
    cohort_path = (
        root
        / "cases"
        / "demo"
        / "quality"
        / "human-reliability"
        / "cohorts"
        / f"{cohort['cohort_id']}-{cohort['cohort_version']}.json"
    )
    write_json(cohort_path, cohort)
    return root, cohort_path


def valid_submission(root: Path, coder_id: str = "coder-fr-001", layer: str = "cmt") -> dict:
    template = json.loads(
        (packet_dir(root, layer) / f"{layer}-response-template.json").read_text(encoding="utf-8")
    )
    packet_manifest = json.loads(
        (packet_dir(root, layer) / "packet-manifest.json").read_text(encoding="utf-8")
    )
    template.update(
        {
            "submission_id": f"submission-{coder_id}",
            "cohort_id": f"demo-fr-{layer}-cohort",
            "cohort_version": "1.0.0",
            "packet_hash": packet_manifest["packet_hash"],
            "coder_id": coder_id,
            "qualification_attested": True,
            "source_language_qualified": True,
            "training_version": "human-training-v1",
            "training_completed_at": "2026-06-20T12:00:00Z",
            "calibration_id": "calibration-fr-v1",
            "calibration_completed_at": "2026-06-20T13:00:00Z",
            "conflict_status": "none_declared",
            "conflict_details": None,
            "independence_attested": True,
            "ai_assistance_used": False,
            "completed_at": "2026-06-21T12:00:00Z",
        }
    )
    response = template["responses"][0]
    response.update(
        {
            "disposition": "coded",
            "confidence": 0.8,
            "uncertainty": "low",
            "uncertainty_note": "A conventional reading remains possible.",
            "out_of_scope_reason": None,
            "notes": "Synthetic fixture response.",
        }
    )
    if layer == "cmt":
        response["cmt_response"] = {
            "source_domain_primary": "carrying",
            "source_domain_secondary": ["body"],
            "target_domain": "nation",
            "conceptual_mapping": "NATION IS A DEFENDED BODY",
            "entailments": ["collective action protects the polity"],
            "cluster_id": "fixture-cluster",
            "rival_reading": "Literal political defense.",
        }
    else:
        for unit in response["lexical_unit_responses"]:
            unit.update(
                {
                    "boundary_response": "exact",
                    "decision_type": "mipvu_indirect",
                    "contextual_meaning": "A contextual meaning.",
                    "basic_meaning": "A basic meaning.",
                    "basic_meaning_source": "Synthetic lexicon.",
                    "contrast_explanation": "The meanings contrast.",
                    "comparison_basis": "Comparison across domains.",
                }
            )
    return template


def corpus_snapshot(root: Path) -> dict[str, bytes]:
    case = root / "cases" / "demo"
    return {
        path.relative_to(case).as_posix(): path.read_bytes()
        for parent in ("metadata", "corpus", "analysis")
        for path in (case / parent).rglob("*")
        if path.is_file()
    }


def write_identification_csv(path: Path, submission: dict) -> None:
    contract = load_csv_contract()
    fields = (
        contract["metadata_columns"]
        + contract["common_response_columns"]
        + contract["layer_columns"]["identification"]
    )
    response = submission["responses"][0]
    rows = []
    for unit in response["lexical_unit_responses"]:
        row = {
            **{field: submission.get(field, "") for field in contract["metadata_columns"]},
            **{
                field: response.get(field, "")
                for field in contract["common_response_columns"]
            },
            **unit,
        }
        for field in (
            "qualification_attested",
            "source_language_qualified",
            "independence_attested",
            "ai_assistance_used",
        ):
            row[field] = str(row[field]).lower()
        row["conflict_details"] = ""
        row["source_span_id"] = response.get("source_span_id") or ""
        row["out_of_scope_reason"] = ""
        row["case_fields"] = json.dumps(response["case_fields"], separators=(",", ":"))
        rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class HumanReliabilityIngestionTest(unittest.TestCase):
    def test_valid_json_is_preserved_and_two_distinct_coders_complete_ingestion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            before = corpus_snapshot(root)
            first_path = base / "first.json"
            second_path = base / "second.json"
            write_json(first_path, valid_submission(root))
            write_json(second_path, valid_submission(root, "coder-fr-002"))

            first = ingest_submission(root, "demo", cohort_path, parse_json_submission(first_path))
            second = ingest_submission(root, "demo", cohort_path, parse_json_submission(second_path))

            self.assertEqual("valid", first["status"])
            self.assertEqual("partial", first["cohort_ingestion_state"])
            self.assertEqual("complete", second["cohort_ingestion_state"])
            self.assertEqual(before, corpus_snapshot(root))
            human_root = root / "cases" / "demo" / "quality" / "human-reliability"
            raw = human_root / "submissions" / "raw" / first["registration_id"] / "submission.json"
            self.assertEqual(first_path.read_bytes(), raw.read_bytes())
            normalized = json.loads(
                (human_root / "normalized" / "normalized-coder-runs.json").read_text()
            )
            self.assertEqual(2, len(normalized["runs"]))

            artifacts = (
                (second, "ingestion-report-schema.json"),
                (
                    json.loads((human_root / "submissions" / "submission-register.json").read_text()),
                    "submission-register-schema.json",
                ),
                (normalized, "normalized-coder-runs-schema.json"),
                (
                    json.loads((human_root / "ingestion-status.json").read_text()),
                    "ingestion-status-schema.json",
                ),
            )
            for artifact, schema_name in artifacts:
                schema = json.loads(
                    (root / "schemas" / "human-reliability" / schema_name).read_text()
                )
                Draft202012Validator(schema, format_checker=FormatChecker()).validate(artifact)

    def test_identification_csv_preserves_rows_and_groups_lexical_units(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base, "identification")
            source = base / "identification.csv"
            write_identification_csv(source, valid_submission(root, layer="identification"))

            parsed = parse_csv_submission(source, load_csv_contract())
            report = ingest_submission(root, "demo", cohort_path, parsed)

            self.assertEqual("valid", report["status"])
            self.assertEqual(2, len(report["raw_rows"]))
            self.assertEqual(1, len(parsed.envelope["responses"]))
            self.assertEqual(
                2,
                len(parsed.envelope["responses"][0]["lexical_unit_responses"]),
            )

    def test_invalid_ids_vocabulary_duplicates_and_comments_are_audited(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            submission = valid_submission(root)
            response = submission["responses"][0]
            response["cmt_response"]["source_domain_primary"] = "invented-domain"
            response["notes"] = "bad\u0000comment"
            submission["responses"].append(copy.deepcopy(response))
            unknown = copy.deepcopy(response)
            unknown["item_id"] = "unknown-item"
            submission["responses"].append(unknown)
            source = base / "invalid.json"
            write_json(source, submission)

            report = ingest_submission(root, "demo", cohort_path, parse_json_submission(source))

            self.assertEqual("invalid", report["status"])
            self.assertEqual("invalid", report["cohort_ingestion_state"])
            self.assertTrue(any("unknown packet item ID" in error for error in report["errors"]))
            self.assertTrue(any("duplicate item ID" in error for error in report["errors"]))
            self.assertTrue(any("unknown controlled value" in error for error in report["errors"]))
            self.assertTrue(any("control character" in error for error in report["errors"]))
            normalized = json.loads(
                (
                    root
                    / "cases"
                    / "demo"
                    / "quality"
                    / "human-reliability"
                    / "normalized"
                    / "normalized-coder-runs.json"
                ).read_text()
            )
            self.assertEqual([], normalized["runs"])
            self.assertEqual(3, len(report["raw_rows"]))

    def test_corrected_attempt_supersedes_invalid_state_and_raw_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            corrected = valid_submission(root)
            invalid = copy.deepcopy(corrected)
            invalid["packet_hash"] = "sha256:" + "0" * 64
            invalid_path = base / "invalid.json"
            corrected_path = base / "corrected.json"
            write_json(invalid_path, invalid)
            write_json(corrected_path, corrected)

            first = ingest_submission(root, "demo", cohort_path, parse_json_submission(invalid_path))
            second = ingest_submission(root, "demo", cohort_path, parse_json_submission(corrected_path))

            self.assertEqual("invalid", first["cohort_ingestion_state"])
            self.assertEqual("partial", second["cohort_ingestion_state"])
            repeated = ingest_submission(
                root, "demo", cohort_path, parse_json_submission(corrected_path)
            )
            self.assertEqual(second, repeated)
            raw = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "submissions"
                / "raw"
                / second["registration_id"]
                / "submission.json"
            )
            raw.chmod(0o644)
            raw.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(IngestionError, "raw registration was altered"):
                ingest_submission(
                    root, "demo", cohort_path, parse_json_submission(corrected_path)
                )

    def test_duplicate_valid_coder_does_not_satisfy_two_coder_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            first_path = base / "first.json"
            duplicate_path = base / "duplicate.json"
            write_json(first_path, valid_submission(root))
            duplicate = valid_submission(root)
            duplicate["submission_id"] = "submission-coder-fr-001-second"
            write_json(duplicate_path, duplicate)

            first = ingest_submission(root, "demo", cohort_path, parse_json_submission(first_path))
            second = ingest_submission(
                root, "demo", cohort_path, parse_json_submission(duplicate_path)
            )

            self.assertEqual("partial", first["cohort_ingestion_state"])
            self.assertEqual("invalid", second["status"])
            self.assertEqual("invalid", second["cohort_ingestion_state"])
            self.assertTrue(any("duplicate valid submission for coder" in error for error in second["errors"]))

    def test_rights_policy_rejects_repository_storage_for_restricted_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            cohort = json.loads(cohort_path.read_text())
            manifest_path = root / "cases" / "demo" / cohort["packet_manifest"]
            manifest = json.loads(manifest_path.read_text())
            manifest["rights_constraints"] = ["local-only-source"]
            unsigned = {key: value for key, value in manifest.items() if key != "packet_hash"}
            manifest["packet_hash"] = sha256_bytes(canonical_json_bytes(unsigned))
            write_json(manifest_path, manifest)
            cohort["rights_constraints"] = ["local-only-source"]
            cohort["approval"]["manifest_sha256"] = cohort_hash(cohort)
            write_json(cohort_path, cohort)
            source = base / "submission.json"
            write_json(source, valid_submission(root))

            with self.assertRaisesRegex(IngestionError, "storage_policy `local_only`"):
                ingest_submission(root, "demo", cohort_path, parse_json_submission(source))

    def test_rejects_cohort_changed_after_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base)
            cohort = json.loads(cohort_path.read_text())
            cohort["primary_coder_ids"].append("coder-fr-003")
            write_json(cohort_path, cohort)
            source = base / "submission.json"
            write_json(source, valid_submission(root))

            with self.assertRaisesRegex(IngestionError, "manifest_sha256"):
                ingest_submission(root, "demo", cohort_path, parse_json_submission(source))

    def test_absent_state_has_no_submissions(self) -> None:
        cohort = {
            "cohort_id": "fixture-cohort",
            "cohort_version": "1",
            "required_primary_coders": 2,
        }
        self.assertEqual("absent", cohort_ingestion_summary([], cohort)["state"])

    def test_status_can_be_written_before_any_human_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, cohort_path = ingestion_root(Path(temp_dir))

            summary = refresh_ingestion_status(root, "demo", cohort_path)

            self.assertEqual("absent", summary["state"])
            status_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "ingestion-status.json"
            )
            self.assertTrue(status_path.is_file())


if __name__ == "__main__":
    unittest.main()
