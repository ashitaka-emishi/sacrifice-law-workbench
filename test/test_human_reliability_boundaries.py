from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.human_reliability.boundaries import (
    ProtectedPathError,
    immutable_accepted_artifact_guard,
    protect_accepted_artifacts,
    safe_output_path,
)
from test.test_human_reliability_packets import ANNOTATION_ID, fixture_root


class HumanReliabilityBoundaryTest(unittest.TestCase):
    def test_rejects_protected_and_traversal_output_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _sample_path = fixture_root(Path(temp_dir), "cmt", ANNOTATION_ID)
            case_root = root / "cases" / "demo"

            allowed = safe_output_path(
                case_root,
                "quality/human-reliability/correction-candidates/demo/correction-candidates.json",
            )
            self.assertEqual(
                allowed.relative_to(case_root.resolve()).as_posix(),
                "quality/human-reliability/correction-candidates/demo/correction-candidates.json",
            )

            for relative in (
                "corpus/annotated/demo-doc-001_annotated.json",
                "quality/model-reliability/packets/packet-manifest.json",
                "quality/reliability-sample.json",
                "quality/human-reliability/../../corpus/mipvu/demo-doc-001_mipvu.json",
            ):
                with self.assertRaises(ProtectedPathError, msg=relative):
                    safe_output_path(case_root, relative)

    def test_symlink_cannot_escape_writable_subtree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _sample_path = fixture_root(Path(temp_dir), "cmt", ANNOTATION_ID)
            case_root = root / "cases" / "demo"
            writable = case_root / "quality" / "human-reliability"
            writable.mkdir(parents=True, exist_ok=True)
            (writable / "escape").symlink_to(case_root / "corpus")

            with self.assertRaises(ProtectedPathError):
                safe_output_path(
                    case_root,
                    "quality/human-reliability/escape/accepted.json",
                )

    def test_guard_restores_attempted_protected_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _sample_path = fixture_root(Path(temp_dir), "cmt", ANNOTATION_ID)
            protected = (
                root
                / "cases"
                / "demo"
                / "corpus"
                / "annotated"
                / "demo-doc-001_annotated.json"
            )
            model_artifact = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "model-reliability"
                / "packets"
                / "packet-manifest.json"
            )
            original_protected = protected.read_bytes()
            original_model_artifact = model_artifact.read_bytes()
            created = root / "cases" / "demo" / "quality" / "reliability-report.md"
            allowed = (
                root
                / "cases"
                / "demo"
                / "quality"
                / "human-reliability"
                / "packets"
                / "allowed.txt"
            )

            with self.assertRaisesRegex(
                ProtectedPathError, "attempted protected write"
            ):
                with immutable_accepted_artifact_guard(root, "demo"):
                    protected.write_text("{}\n", encoding="utf-8")
                    model_artifact.write_text("{}\n", encoding="utf-8")
                    created.write_text("not allowed\n", encoding="utf-8")
                    allowed.parent.mkdir(parents=True, exist_ok=True)
                    allowed.write_text("allowed\n", encoding="utf-8")

            self.assertEqual(protected.read_bytes(), original_protected)
            self.assertEqual(model_artifact.read_bytes(), original_model_artifact)
            self.assertFalse(created.exists())
            self.assertEqual(allowed.read_text(encoding="utf-8"), "allowed\n")

    def test_decorator_detects_buggy_study_function_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _sample_path = fixture_root(Path(temp_dir), "cmt", ANNOTATION_ID)
            protected = (
                root
                / "cases"
                / "demo"
                / "metadata"
                / "document-manifest.json"
            )
            original = protected.read_bytes()

            @protect_accepted_artifacts
            def buggy_study_script(root: Path, case_id: str) -> None:
                (root / "cases" / case_id / "metadata" / "document-manifest.json").write_text(
                    "{}\n", encoding="utf-8"
                )

            with self.assertRaisesRegex(
                ProtectedPathError, "attempted protected write"
            ):
                buggy_study_script(root, "demo")

            self.assertEqual(protected.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
