from __future__ import annotations

import copy
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.model_reliability.classify_disagreements import (
    compute_case_disagreements,
)
from scripts.model_reliability.compare_runs import compute_case_agreement
from scripts.model_reliability.generate_review_queue import (
    ReviewQueueError,
    build_queue,
    generate_case_review_queue,
)
from scripts.model_reliability.ingest_submission import (
    ingest_submission,
    parse_json_submission,
)
from test.test_model_reliability_ingestion import FIXTURE_ROOT, ingestion_root


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def review_queue_root(base: Path, include_invalid: bool = False) -> Path:
    root = ingestion_root(base)
    if include_invalid:
        ingest_submission(
            root,
            "demo",
            parse_json_submission(
                FIXTURE_ROOT / "submissions" / "unknown-ids.json"
            ),
        )
    normalized = (
        root
        / "cases"
        / "demo"
        / "quality"
        / "model-reliability"
        / "normalized"
        / "normalized-runs.json"
    )
    normalized.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        FIXTURE_ROOT / "comparison" / "comparison-inputs.json",
        normalized,
    )
    audit = root / "publication" / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "claim-traceability.json").write_text(
        json.dumps(
            {
                "case_id": "demo",
                "traces": [
                    {
                        "trace_id": "demo-trace-001",
                        "case_id": "demo",
                        "claim_id": "demo-claim-hope",
                        "claim_text": "The carrying metaphor frames collective hope.",
                        "claim_status": "interpretation",
                        "support_dimension": "sacred_object",
                        "document_id": "demo-doc-001",
                        "sentence_id": "demo-doc-001_s01_p01_s01",
                        "cluster_id": "demo-carrying-hope",
                        "mipvu_ids": [
                            "demo-doc-001_s01_p01_s01_lu002"
                        ],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    compute_case_agreement(root, "demo")
    compute_case_disagreements(root, "demo")
    return root


class ModelReliabilityReviewQueueTest(unittest.TestCase):
    def test_generates_self_contained_schema_valid_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir))
            corpus_root = root / "cases" / "demo" / "corpus"
            before = {
                path.relative_to(corpus_root).as_posix(): path.read_bytes()
                for path in corpus_root.rglob("*")
                if path.is_file()
            }

            queue = generate_case_review_queue(root, "demo")

            after = {
                path.relative_to(corpus_root).as_posix(): path.read_bytes()
                for path in corpus_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            self.assertEqual(queue["summary"]["queue_count"], len(queue["entries"]))
            self.assertGreater(len(queue["entries"]), 0)
            target = next(
                entry
                for entry in queue["entries"]
                if entry["field"] == "cmt.target_domain"
            )
            self.assertEqual(target["source_text"], "La cité porte l'espoir.")
            self.assertEqual(target["gloss_en"], "The city carries hope.")
            self.assertEqual(target["focal_text"], "porte")
            self.assertEqual(target["reference_value"], "hope")
            self.assertEqual(target["rights_status"], "synthetic-cc0")
            self.assertEqual(
                target["affected_claims"][0]["claim_id"], "demo-claim-hope"
            )
            self.assertIn("cross-case:metaphor-mapping", target["cross_case_impacts"])
            self.assertEqual(target["decision_authority"], "human-only")
            self.assertEqual(target["review_status"], "pending-human-review")

            schema = json.loads(
                (
                    SOURCE_ROOT
                    / "schemas"
                    / "model-reliability"
                    / "review-queue-schema.json"
                ).read_text()
            )
            Draft202012Validator(schema).validate(queue)

    def test_queue_is_deterministic_and_csv_matches_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir))

            first = generate_case_review_queue(root, "demo")
            first_bytes = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "review-queue"
                / "model-review-queue.json"
            ).read_bytes()
            second = generate_case_review_queue(root, "demo")
            second_bytes = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "review-queue"
                / "model-review-queue.json"
            ).read_bytes()

            self.assertEqual(first, second)
            self.assertEqual(first_bytes, second_bytes)
            ranks = [entry["queue_rank"] for entry in first["entries"]]
            self.assertEqual(ranks, list(range(1, len(ranks) + 1)))
            scores = [entry["priority_score"] for entry in first["entries"]]
            self.assertEqual(scores, sorted(scores, reverse=True))
            csv_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "review-queue"
                / "model-review-queue.csv"
            )
            with csv_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(
                [row["queue_id"] for row in rows],
                [entry["queue_id"] for entry in first["entries"]],
            )

    def test_no_majority_vote_or_adjudication_decision_is_emitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir))

            queue = generate_case_review_queue(root, "demo")

            forbidden = {
                "adjudication_decision",
                "accepted_value",
                "majority_decision",
                "recommended_value",
            }
            for entry in queue["entries"]:
                self.assertTrue(forbidden.isdisjoint(entry))
                self.assertIn("diagnostic only", entry["adjudication_note"])
            serialized = json.dumps(queue).lower()
            self.assertNotIn('"majority_decision"', serialized)
            self.assertNotIn('"accepted_value"', serialized)

    def test_claim_and_cross_case_impact_raise_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir))
            log_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "comparisons"
                / "disagreement-log.json"
            )
            log = json.loads(log_path.read_text())
            target = next(
                record
                for record in log["disagreements"]
                if record["field"] == "cmt.target_domain"
            )
            target["review_priority"] = "medium"

            queue = build_queue(root, "demo", log)

            queued = next(
                entry
                for entry in queue["entries"]
                if entry["field"] == "cmt.target_domain"
            )
            self.assertEqual(queued["priority"], "high")
            self.assertIn("claim-audit-impact", queued["priority_reasons"])
            self.assertIn("cross-case-impact", queued["priority_reasons"])

    def test_local_only_rights_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir))
            manifest_path = (
                root
                / "cases"
                / "demo"
                / "metadata"
                / "document-manifest.json"
            )
            manifest = json.loads(manifest_path.read_text())
            manifest["documents"][0]["rights_status"] = "gitignored-local-fair-use"
            manifest["documents"][0]["storage_policy"] = "local-only"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

            queue = generate_case_review_queue(root, "demo")

            self.assertTrue(
                all(
                    entry["rights_status"] == "gitignored-local-fair-use"
                    and entry["storage_policy"] == "local-only"
                    for entry in queue["entries"]
                )
            )

    def test_invalid_submission_context_is_self_contained(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir), include_invalid=True)

            queue = generate_case_review_queue(root, "demo")

            invalid = next(
                entry
                for entry in queue["entries"]
                if entry["category"] == "hallucination-instability"
                and entry["item_id"] == "unknown-item"
            )
            self.assertEqual(invalid["source_text"], "La cité porte l'espoir.")
            self.assertEqual(invalid["gloss_en"], "The city carries hope.")
            self.assertEqual(invalid["focal_text"], "")
            self.assertEqual(invalid["decision_authority"], "human-only")

    def test_rejects_wrong_case_and_untrusted_generator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = review_queue_root(Path(temp_dir))
            log_path = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "comparisons"
                / "disagreement-log.json"
            )
            log = json.loads(log_path.read_text())

            wrong_case = copy.deepcopy(log)
            wrong_case["case_id"] = "other"
            with self.assertRaisesRegex(ReviewQueueError, "case_id"):
                build_queue(root, "demo", wrong_case)

            wrong_generator = copy.deepcopy(log)
            wrong_generator["generator"] = "untrusted"
            with self.assertRaisesRegex(ReviewQueueError, "classification stage"):
                build_queue(root, "demo", wrong_generator)

            invalid_runs = copy.deepcopy(log)
            invalid_runs["run_ids"] = ["duplicate", "duplicate"]
            with self.assertRaisesRegex(ReviewQueueError, "invalid run_ids"):
                build_queue(root, "demo", invalid_runs)

            bad_summary = copy.deepcopy(log)
            bad_summary["summary"]["total_disagreements"] += 1
            with self.assertRaisesRegex(ReviewQueueError, "does not reconcile"):
                build_queue(root, "demo", bad_summary)

            duplicate = copy.deepcopy(log)
            duplicate["disagreements"].append(
                copy.deepcopy(duplicate["disagreements"][0])
            )
            duplicate["summary"]["total_disagreements"] += 1
            with self.assertRaisesRegex(ReviewQueueError, "duplicate"):
                build_queue(root, "demo", duplicate)

            malformed = copy.deepcopy(log)
            malformed["disagreements"][0] = "not-an-object"
            with self.assertRaisesRegex(ReviewQueueError, "non-object"):
                build_queue(root, "demo", malformed)


if __name__ == "__main__":
    unittest.main()
