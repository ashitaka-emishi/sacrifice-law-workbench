from __future__ import annotations

import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.human_reliability.classify_disagreements import (
    classify_disagreements,
    compute_case_disagreements,
)
from scripts.human_reliability.compare_references import (
    compute_case_reference_comparison,
)
from scripts.human_reliability.compute_agreement import compute_case_agreement
from scripts.human_reliability.generate_adjudication_queue import (
    AdjudicationQueueError,
    build_queue,
    generate_case_adjudication_queue,
    priority,
)
from scripts.human_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from test.test_human_reliability_disagreements import upstream_artifacts
from test.test_human_reliability_ingestion import ingestion_root, valid_submission
from test.test_human_reliability_packets import write_json


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def packet_item() -> dict:
    return {
        "item_id": "demo-item-cmt",
        "document_id": "demo-doc-001",
        "sentence_id": "demo-sentence-001",
        "sentence_source_text": "La cité porte l'espoir.",
        "lexical_units": [
            {
                "lexical_unit_id": "demo-unit-001",
                "source_text": "porte",
            }
        ],
        "context_scope": "complete_sentence",
        "rights_constraints": ["synthetic-test-only"],
    }


def model_agreement() -> dict:
    summary = {
        "comparison_family": "model_vs_reference",
        "left_id": "model-run-a",
        "right_id": "accepted-reference",
        "case_id": "demo",
        "source_language": "fr",
        "document_id": "demo-doc-001",
        "task_layer": "cmt",
        "field": "cmt.target_domain",
        "comparable_count": 1,
        "exact_match_count": 1,
        "metric": {
            "name": "observed_agreement",
            "status": "defined",
            "value": 1.0,
            "undefined_reason": None,
        },
        "cohens_kappa": {
            "status": "undefined",
            "value": None,
            "undefined_reason": "one item",
        },
    }
    return {
        "run_ids": ["model-run-a", "model-run-b"],
        "comparison_families": {
            "model_vs_model": {"pairs": []},
            "model_vs_reference": {
                "runs": [
                    {
                        "run_id": "model-run-a",
                        "reference_id": "accepted-reference",
                        "summaries": [summary],
                    }
                ]
            },
        },
    }


class HumanAdjudicationQueueTest(unittest.TestCase):
    def test_build_queue_preserves_evidence_and_adds_claim_and_model_summaries(self) -> None:
        agreement, comparison, sample = upstream_artifacts()
        log = classify_disagreements(agreement, comparison, sample)
        traces = [
            {
                "case_id": "demo",
                "claim_id": "demo-claim-001",
                "claim_text": "The text frames the polity through a body mapping.",
                "claim_status": "interpretation",
                "support_dimension": "sacred_object",
                "sentence_id": "demo-sentence-001",
                "mapping_id": "another-reference",
                "mipvu_ids": [],
            }
        ]

        result = build_queue(
            log,
            {"demo-item-cmt": packet_item()},
            claim_traces=traces,
            model_agreement=model_agreement(),
            model_source="cases/demo/quality/model-reliability/comparisons/agreement-results.json",
        )

        self.assertEqual(3, result["summary"]["queue_count"])
        self.assertTrue(all(row["source_text"] == "La cité porte l'espoir." for row in result["entries"]))
        self.assertTrue(all(len(row["coder_values"]) == 2 for row in result["entries"]))
        self.assertTrue(all(row["affected_claims"][0]["claim_id"] == "demo-claim-001" for row in result["entries"]))
        target = next(row for row in result["entries"] if row["field"] == "cmt.target_domain")
        self.assertEqual("available", target["model_summary"]["status"])
        self.assertEqual(1, target["model_summary"]["matching_summary_count"])
        self.assertEqual("available", target["reference_summary"]["status"])
        self.assertEqual("hope", target["reference_summary"]["value"])
        self.assertIn("metaphor-mapping", target["affected_claim_dimensions"])
        self.assertEqual("pending-independent-adjudication", target["review_status"])
        self.assertNotIn("adjudication_decision", target)
        schema = json.loads(
            (
                SOURCE_ROOT / "schemas" / "human-reliability"
                / "adjudication-queue-schema.json"
            ).read_text()
        )
        Draft202012Validator(schema).validate(result)

    def test_queue_id_is_stable_when_ranking_changes(self) -> None:
        agreement, comparison, sample = upstream_artifacts()
        log = classify_disagreements(agreement, comparison, sample)
        packets = {"demo-item-cmt": packet_item()}
        first = build_queue(log, packets)
        target_id = next(
            row["queue_id"]
            for row in first["entries"]
            if row["field"] == "cmt.target_domain"
        )
        changed = copy.deepcopy(log)
        added = copy.deepcopy(changed["disagreements"][0])
        added.update(
            {
                "disagreement_id": "human-disagreement-ffffffffffffffff",
                "source_pattern_id": "new-higher-priority-pattern",
                "field": "interpretation.violence_logic",
                "category": "violence_obligation",
                "field_category": "violence_obligation",
                "agreement_pattern": "both_against_reference",
                "adjudication_priority": "high",
            }
        )
        changed["disagreements"].append(added)
        changed["summary"]["total_disagreements"] += 1
        second = build_queue(changed, packets)
        changed_target = next(row for row in second["entries"] if row["field"] == "cmt.target_domain")
        self.assertEqual(target_id, changed_target["queue_id"])
        self.assertNotEqual(
            next(row["queue_rank"] for row in first["entries"] if row["field"] == "cmt.target_domain"),
            changed_target["queue_rank"],
        )

    def test_priority_policy_escalates_required_dimensions(self) -> None:
        base = {
            "adjudication_priority": "low",
            "agreement_pattern": "reference_unavailable",
            "claim_impact": "ordinary",
            "source_language_risk": {"level": "material"},
            "possible_codebook_ambiguity": False,
            "coder_values": [
                {"coder_id": "a", "value": "present"},
                {"coder_id": "b", "value": "absent"},
            ],
        }
        cases = [
            ("interpretation.sacred_object", "interpretation", "presence-disagreement"),
            ("interpretation.agents", "agency_absence", "agency-absence"),
            ("interpretation.purification", "interpretation", "purification"),
            ("interpretation.violence_logic", "violence_obligation", "violence"),
        ]
        for field, category, reason in cases:
            with self.subTest(field=field):
                level, _, reasons = priority(
                    {**base, "field": field, "field_category": category}, [], []
                )
                self.assertEqual("high", level)
                self.assertIn(reason, reasons)
        level, _, reasons = priority(
            {
                **base,
                "field": "cmt.target_domain",
                "field_category": "domains",
                "agreement_pattern": "both_against_reference",
                "source_language_risk": {"level": "low"},
            },
            [],
            [],
        )
        self.assertEqual("high", level)
        self.assertIn("both-against-reference", reasons)
        level, _, reasons = priority(
            {
                **base,
                "field": "uncertainty",
                "field_category": "confidence",
                "adjudication_priority": "medium",
                "agreement_pattern": "uncertain_vs_confident",
            },
            [],
            [],
        )
        self.assertEqual("high", level)
        self.assertIn("language-uncertainty-split", reasons)

    def test_build_rejects_missing_packet_and_duplicate_disagreement_ids(self) -> None:
        agreement, comparison, sample = upstream_artifacts()
        log = classify_disagreements(agreement, comparison, sample)
        with self.assertRaisesRegex(AdjudicationQueueError, "absent from the packet"):
            build_queue(log, {})
        duplicate = copy.deepcopy(log)
        duplicate["disagreements"].append(copy.deepcopy(duplicate["disagreements"][0]))
        duplicate["summary"]["total_disagreements"] += 1
        with self.assertRaisesRegex(AdjudicationQueueError, "duplicate IDs"):
            build_queue(duplicate, {"demo-item-cmt": packet_item()})

    def test_compute_writes_schema_valid_queue_without_modifying_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base, "cmt")
            annotated = (
                root / "cases" / "demo" / "corpus" / "annotated"
                / "demo-doc-001_annotated.json"
            )
            before = annotated.read_bytes()
            left = valid_submission(root, "coder-fr-001", "cmt")
            right = valid_submission(root, "coder-fr-002", "cmt")
            right["responses"][0]["cmt_response"]["target_domain"] = "hope"
            for submission in (left, right):
                source = base / f"{submission['coder_id']}.json"
                write_json(source, submission)
                ingest_submission(root, "demo", cohort_path, parse_json_submission(source))
            compute_case_agreement(root, "demo", "demo-fr-cmt-cohort", "1.0.0")
            compute_case_reference_comparison(root, "demo", "demo-fr-cmt-cohort", "1.0.0")
            compute_case_disagreements(root, "demo", "demo-fr-cmt-cohort", "1.0.0")

            result = generate_case_adjudication_queue(
                root, "demo", "demo-fr-cmt-cohort", "1.0.0"
            )

            self.assertEqual(before, annotated.read_bytes())
            self.assertGreater(result["summary"]["queue_count"], 0)
            self.assertTrue(all(row["model_summary"]["status"] == "unavailable" for row in result["entries"]))
            output = (
                root / "cases" / "demo" / "quality" / "human-reliability"
                / "comparisons" / "demo-fr-cmt-cohort-1.0.0"
            )
            schema = json.loads(
                (
                    SOURCE_ROOT / "schemas" / "human-reliability"
                    / "adjudication-queue-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(result)
            self.assertTrue((output / "adjudication-queue.json").is_file())
            with (output / "adjudication-queue.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(result["summary"]["queue_count"], len(rows))
            self.assertTrue(all(row["source_text"] for row in rows))

    def test_compute_rejects_packet_payload_tampering_and_unsafe_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root, cohort_path = ingestion_root(base, "cmt")
            for coder_id in ("coder-fr-001", "coder-fr-002"):
                source = base / f"{coder_id}.json"
                write_json(source, valid_submission(root, coder_id, "cmt"))
                ingest_submission(root, "demo", cohort_path, parse_json_submission(source))
            compute_case_agreement(root, "demo", "demo-fr-cmt-cohort", "1.0.0")
            compute_case_reference_comparison(root, "demo", "demo-fr-cmt-cohort", "1.0.0")
            compute_case_disagreements(root, "demo", "demo-fr-cmt-cohort", "1.0.0")
            original_cohort = cohort_path.read_bytes()
            cohort = json.loads(original_cohort)
            cohort["storage_policy"] = "local_only"
            write_json(cohort_path, cohort)
            with self.assertRaisesRegex(AdjudicationQueueError, "approval.manifest_sha256"):
                generate_case_adjudication_queue(
                    root, "demo", "demo-fr-cmt-cohort", "1.0.0"
                )
            cohort_path.write_bytes(original_cohort)
            packet_path = next(
                (
                    root / "cases" / "demo" / "quality" / "human-reliability"
                    / "packets"
                ).glob("*/*.jsonl")
            )
            packet_path.write_text(packet_path.read_text() + "\n", encoding="utf-8")
            with self.assertRaisesRegex(AdjudicationQueueError, "payload hash"):
                generate_case_adjudication_queue(
                    root, "demo", "demo-fr-cmt-cohort", "1.0.0"
                )
            with self.assertRaisesRegex(AdjudicationQueueError, "unsafe cohort_id"):
                generate_case_adjudication_queue(root, "demo", "../bad", "1.0.0")


if __name__ == "__main__":
    unittest.main()
