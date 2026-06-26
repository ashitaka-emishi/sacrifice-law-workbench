from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.model_reliability.generate_packets import generate_packets
from scripts.model_reliability.run_external_model import (
    ExternalModelRunnerError,
    call_anthropic,
    call_openai,
    main,
)
from test.test_model_reliability_packets import fixture_root


SOURCE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = SOURCE_ROOT / "test" / "fixtures" / "model-reliability"


def runner_root(base: Path) -> Path:
    root = fixture_root(base)
    target_schemas = root / "schemas" / "model-reliability"
    target_schemas.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_ROOT / "schemas" / "model-reliability", target_schemas)
    generate_packets(root, "demo", revision="fixture-revision-v1")
    return root


def adjusted_valid_mock(
    path: Path,
    *,
    provider: str,
    model: str,
    model_version: str | None,
    run_id: str,
    submission_id: str,
    completed_at: str,
) -> Path:
    submission = json.loads(
        (FIXTURE_ROOT / "submissions" / "valid-cmt.json").read_text(
            encoding="utf-8"
        )
    )
    submission["submission_id"] = submission_id
    submission["run"] = {
        "run_id": run_id,
        "provider": provider,
        "model": model,
        "model_version": model_version,
        "completed_at": completed_at,
        "language_capabilities": ["fr", "en"],
        "settings": {"temperature": 0},
    }
    path.write_text(json.dumps(submission), encoding="utf-8")
    return path


class ExternalModelRunnerTest(unittest.TestCase):
    def test_dry_run_writes_template_and_provider_prompt_without_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            output = base / "reports" / "tmp" / "model-reliability"

            result = main(
                [
                    "--root",
                    str(root),
                    "--case",
                    "demo",
                    "--task-layer",
                    "cmt",
                    "--provider",
                    "openai",
                    "--model",
                    "gpt-test",
                    "--run-id",
                    "dry-run-001",
                    "--completed-at",
                    "2026-06-18T12:00:00Z",
                    "--output-root",
                    str(output),
                    "--dry-run",
                ]
            )

            self.assertEqual(result, 0)
            templates = sorted(output.glob("*.json"))
            prompts = sorted(output.glob("*.prompt.txt"))
            self.assertEqual(len(templates), 1)
            self.assertEqual(len(prompts), 1)
            template = json.loads(templates[0].read_text(encoding="utf-8"))
            self.assertEqual(template["packet_id"], "demo-multi-model-v1-packet")
            self.assertEqual(template["prompt_id"], "cmt-v1")
            self.assertEqual(template["items"][0]["task_layer"], "cmt")
            prompt = prompts[0].read_text(encoding="utf-8")
            self.assertIn("Blind packet JSONL", prompt)
            self.assertEqual(prompt.count("## Blind packet JSONL"), 1)
            self.assertIn("Return exactly one raw JSON object", prompt)
            self.assertIn("Do not add accepted annotations", prompt)

    def test_mock_response_validates_without_calling_external_api(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            output = base / "reports" / "tmp" / "model-reliability"
            mock = adjusted_valid_mock(
                base / "valid.json",
                provider="anthropic",
                model="claude-test",
                model_version="fixture-v1",
                run_id="mock-001",
                submission_id="demo-mock-001",
                completed_at="2026-06-18T12:00:00Z",
            )

            result = main(
                [
                    "--root",
                    str(root),
                    "--case",
                    "demo",
                    "--task-layer",
                    "cmt",
                    "--provider",
                    "anthropic",
                    "--model",
                    "claude-test",
                    "--model-version",
                    "fixture-v1",
                    "--run-id",
                    "mock-001",
                    "--submission-id",
                    "demo-mock-001",
                    "--completed-at",
                    "2026-06-18T12:00:00Z",
                    "--language-capability",
                    "fr",
                    "--language-capability",
                    "en",
                    "--setting",
                    "temperature=0",
                    "--no-disable-tools-note",
                    "--output-root",
                    str(output),
                    "--mock-response",
                    str(mock),
                ]
            )

            self.assertEqual(result, 0)
            written = sorted(output.glob("*.json"))
            self.assertEqual(len(written), 1)
            self.assertFalse(list(output.glob("*.validation-errors.txt")))

    def test_mock_response_reports_validation_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            bad_path = adjusted_valid_mock(
                base / "bad.json",
                provider="openai",
                model="gpt-test",
                model_version=None,
                run_id="bad-001",
                submission_id="demo-bad-001",
                completed_at="2026-06-18T12:00:00Z",
            )
            bad = json.loads(bad_path.read_text(encoding="utf-8"))
            bad["packet_hash"] = "sha256:" + "0" * 64
            bad_path.write_text(json.dumps(bad), encoding="utf-8")
            output = base / "reports" / "tmp" / "model-reliability"

            result = main(
                [
                    "--root",
                    str(root),
                    "--case",
                    "demo",
                    "--task-layer",
                    "cmt",
                    "--provider",
                    "openai",
                    "--model",
                    "gpt-test",
                    "--run-id",
                    "bad-001",
                    "--submission-id",
                    "demo-bad-001",
                    "--completed-at",
                    "2026-06-18T12:00:00Z",
                    "--language-capability",
                    "fr",
                    "--language-capability",
                    "en",
                    "--setting",
                    "temperature=0",
                    "--no-disable-tools-note",
                    "--output-root",
                    str(output),
                    "--mock-response",
                    str(bad_path),
                ]
            )

            self.assertEqual(result, 1)
            errors = sorted(output.glob("*.validation-errors.txt"))
            self.assertEqual(len(errors), 1)
            self.assertIn("packet_hash", errors[0].read_text(encoding="utf-8"))

    def test_rejects_sensitive_settings_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            output = base / "reports" / "tmp" / "model-reliability"

            with redirect_stderr(StringIO()):
                result = main(
                    [
                        "--root",
                        str(root),
                        "--case",
                        "demo",
                        "--task-layer",
                        "cmt",
                        "--provider",
                        "openai",
                        "--model",
                        "gpt-test",
                        "--setting",
                        "api_key=\"do-not-write\"",
                        "--output-root",
                        str(output),
                        "--mock-response",
                        str(FIXTURE_ROOT / "submissions" / "valid-cmt.json"),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertFalse(output.exists())

    def test_openai_request_uses_responses_api_without_tools(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(url: str, headers: dict, body: dict) -> dict:
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = body
            return {"output_text": '{"schema_version":"1.0.0"}'}

        with patch(
            "scripts.model_reliability.run_external_model._request_json",
            side_effect=fake_request,
        ):
            text = call_openai(
                api_key="secret-key",
                model="gpt-test",
                system="system",
                user="user",
                settings={"temperature": 0, "max_output_tokens": 1000},
            )

        self.assertEqual(text, '{"schema_version":"1.0.0"}')
        self.assertEqual(captured["url"], "https://api.openai.com/v1/responses")
        body = captured["body"]
        self.assertIsInstance(body, dict)
        self.assertNotIn("tools", body)
        self.assertNotIn("secret-key", json.dumps(body))

    def test_anthropic_request_uses_messages_api_without_tools(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(url: str, headers: dict, body: dict) -> dict:
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = body
            return {"content": [{"type": "text", "text": '{"schema_version":"1.0.0"}'}]}

        with patch(
            "scripts.model_reliability.run_external_model._request_json",
            side_effect=fake_request,
        ):
            text = call_anthropic(
                api_key="secret-key",
                model="claude-test",
                system="system",
                user="user",
                settings={"temperature": 0, "max_tokens": 1000},
            )

        self.assertEqual(text, '{"schema_version":"1.0.0"}')
        self.assertEqual(captured["url"], "https://api.anthropic.com/v1/messages")
        body = captured["body"]
        self.assertIsInstance(body, dict)
        self.assertNotIn("tools", body)
        self.assertNotIn("secret-key", json.dumps(body))

    def test_anthropic_rejects_non_integer_max_tokens(self) -> None:
        with self.assertRaisesRegex(ExternalModelRunnerError, "max_tokens"):
            call_anthropic(
                api_key="secret-key",
                model="claude-test",
                system="system",
                user="user",
                settings={"max_tokens": "many"},
            )


if __name__ == "__main__":
    unittest.main()
