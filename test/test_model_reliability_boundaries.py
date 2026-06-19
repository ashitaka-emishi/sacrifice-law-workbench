from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.model_reliability.boundaries import (
    ProtectedPathError,
    immutable_reference_guard,
    review_candidate_path,
    safe_output_path,
)
from test.test_model_reliability_packets import fixture_root


class ModelReliabilityBoundaryTest(unittest.TestCase):
    def test_rejects_protected_and_traversal_output_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
            case_root = root / "cases" / "demo"
            for relative in (
                "corpus/mipvu/accepted.json",
                "analysis/analysis.json",
                "quality/adjudication-log.csv",
                "quality/model-reliability/../../corpus/annotated.json",
            ):
                with self.assertRaises(ProtectedPathError, msg=relative):
                    safe_output_path(case_root, relative)

    def test_symlink_cannot_escape_writable_subtree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
            case_root = root / "cases" / "demo"
            writable = case_root / "quality" / "model-reliability"
            writable.mkdir(parents=True, exist_ok=True)
            (writable / "escape").symlink_to(case_root / "corpus")
            with self.assertRaises(ProtectedPathError):
                safe_output_path(
                    case_root,
                    "quality/model-reliability/escape/accepted.json",
                )

    def test_review_candidates_have_a_dedicated_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
            case_root = root / "cases" / "demo"
            candidate = review_candidate_path(
                case_root, "model-review-queue.json"
            )
            self.assertEqual(
                candidate.relative_to(case_root.resolve()).as_posix(),
                "quality/model-reliability/review-queue/model-review-queue.json",
            )
            with self.assertRaises(ProtectedPathError):
                review_candidate_path(case_root, "../accepted.json")

    def test_guard_restores_attempted_protected_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = fixture_root(Path(temp_dir))
            protected = (
                root
                / "cases"
                / "demo"
                / "corpus"
                / "mipvu"
                / "demo-doc-001_mipvu.json"
            )
            original = protected.read_bytes()
            created = root / "publication" / "model-write.txt"
            created_directory = root / "publication" / "model-output"
            created_symlink = root / "publication" / "accepted-link"
            self.assertFalse((root / "publication").exists())
            with self.assertRaisesRegex(
                ProtectedPathError, "attempted protected write"
            ):
                with immutable_reference_guard(root, "demo"):
                    protected.write_text("{}\n", encoding="utf-8")
                    created.parent.mkdir(parents=True)
                    created.write_text("not allowed\n", encoding="utf-8")
                    created_directory.mkdir()
                    (created_directory / "candidate.json").write_text(
                        "{}\n", encoding="utf-8"
                    )
                    created_symlink.symlink_to(protected)
            self.assertEqual(protected.read_bytes(), original)
            self.assertFalse(created.exists())
            self.assertFalse(created_directory.exists())
            self.assertFalse(created_symlink.exists())
            self.assertFalse((root / "publication").exists())


if __name__ == "__main__":
    unittest.main()
