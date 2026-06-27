from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.model_reliability.generate_packets import generate_packets
from scripts.model_reliability.run_external_model import (
    ExternalModelRunnerError,
    call_anthropic,
    call_openai,
    load_dotenv_values,
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
    root: Path,
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
    manifest = json.loads(
        (
            root
            / "cases"
            / "demo"
            / "quality"
            / "model-reliability"
            / "packets"
            / "packet-manifest.json"
        ).read_text(encoding="utf-8")
    )
    prompt = next(item for item in manifest["prompts"] if item["task_layer"] == "cmt")
    submission["sample_id"] = manifest["sample_id"]
    submission["sample_version"] = manifest["sample_version"]
    submission["packet_hash"] = manifest["packet_hash"]
    submission["prompt_hash"] = prompt["hash"]
    submission["code_revision"] = manifest["code_revision"]
    submission["source_language"] = manifest["source_language"]
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
            self.assertIn("Controlled values", prompt)
            self.assertIn("cmt.source_domain_primary", prompt)
            self.assertIn("uncertainty.status", prompt)

    def test_dry_run_templates_include_layer_specific_required_fields(self) -> None:
        expected_fields = {
            "identification": ("identification",),
            "cmt": ("cmt",),
            "interpretation": ("interpretation",),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)

            for layer, fields in expected_fields.items():
                output = base / "reports" / "tmp" / layer
                result = main(
                    [
                        "--root",
                        str(root),
                        "--case",
                        "demo",
                        "--task-layer",
                        layer,
                        "--provider",
                        "openai",
                        "--model",
                        "gpt-test",
                        "--run-id",
                        f"dry-run-{layer}",
                        "--completed-at",
                        "2026-06-18T12:00:00Z",
                        "--output-root",
                        str(output),
                        "--dry-run",
                    ]
                )

                self.assertEqual(result, 0)
                template_path = next(output.glob("*.json"))
                item = json.loads(template_path.read_text(encoding="utf-8"))["items"][0]
                for field in fields:
                    self.assertIn(field, item)
                if layer == "identification":
                    self.assertIn("decision", item["lexical_units"][0])
                    self.assertIn("boundary_decision", item["lexical_units"][0])
                if layer == "cmt":
                    self.assertIn("source_domain_primary", item["cmt"])
                    self.assertIn("conceptual_metaphor", item["cmt"])
                if layer == "interpretation":
                    self.assertIn("functions", item["interpretation"])
                    self.assertIn("agency", item["interpretation"])
                    self.assertIn("absence", item["interpretation"])

    def test_mock_response_validates_without_calling_external_api(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            output = base / "reports" / "tmp" / "model-reliability"
            mock = adjusted_valid_mock(
                base / "valid.json",
                root=root,
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
                root=root,
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

    def test_mock_response_reports_malformed_cmt_errors_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            bad_path = adjusted_valid_mock(
                base / "bad-cmt.json",
                root=root,
                provider="openai",
                model="gpt-test",
                model_version=None,
                run_id="bad-cmt-001",
                submission_id="demo-bad-cmt-001",
                completed_at="2026-06-18T12:00:00Z",
            )
            bad = json.loads(bad_path.read_text(encoding="utf-8"))
            bad["items"][0]["cmt"]["target_domain"] = {"label": "hope"}
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
                    "bad-cmt-001",
                    "--submission-id",
                    "demo-bad-cmt-001",
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
            self.assertIn("target_domain", errors[0].read_text(encoding="utf-8"))

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

    def test_openai_key_can_be_read_from_default_dotenv_without_leaking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            output = base / "reports" / "tmp" / "model-reliability"
            secret = "dotenv-secret-openai"
            (root / ".env").write_text(f"OPENAI_API_KEY={secret}\n", encoding="utf-8")
            mock = adjusted_valid_mock(
                base / "valid.json",
                root=root,
                provider="openai",
                model="gpt-test",
                model_version=None,
                run_id="dotenv-001",
                submission_id="demo-dotenv-001",
                completed_at="2026-06-18T12:00:00Z",
            )
            captured: dict[str, str] = {}

            def fake_call_openai(**kwargs: object) -> str:
                captured["api_key"] = str(kwargs["api_key"])
                return mock.read_text(encoding="utf-8")

            stdout = StringIO()
            with patch.dict(os.environ, {}, clear=True), patch(
                "scripts.model_reliability.run_external_model.call_openai",
                side_effect=fake_call_openai,
            ), redirect_stdout(stdout):
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
                        "dotenv-001",
                        "--submission-id",
                        "demo-dotenv-001",
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
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(captured["api_key"], secret)
            rendered_output = stdout.getvalue()
            self.assertNotIn(secret, rendered_output)
            for path in output.glob("*"):
                self.assertNotIn(secret, path.read_text(encoding="utf-8"))

    def test_exported_environment_key_wins_over_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            output = base / "reports" / "tmp" / "model-reliability"
            (root / ".env").write_text("OPENAI_API_KEY=dotenv-secret\n", encoding="utf-8")
            mock = adjusted_valid_mock(
                base / "valid.json",
                root=root,
                provider="openai",
                model="gpt-test",
                model_version=None,
                run_id="env-wins-001",
                submission_id="demo-env-wins-001",
                completed_at="2026-06-18T12:00:00Z",
            )
            captured: dict[str, str] = {}

            def fake_call_openai(**kwargs: object) -> str:
                captured["api_key"] = str(kwargs["api_key"])
                return mock.read_text(encoding="utf-8")

            with patch.dict(os.environ, {"OPENAI_API_KEY": "exported-secret"}, clear=True), patch(
                "scripts.model_reliability.run_external_model.call_openai",
                side_effect=fake_call_openai,
            ), redirect_stdout(StringIO()):
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
                        "env-wins-001",
                        "--submission-id",
                        "demo-env-wins-001",
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
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(captured["api_key"], "exported-secret")

    def test_alternate_env_file_supplies_custom_api_key_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            output = base / "reports" / "tmp" / "model-reliability"
            env_file = base / "provider.env"
            env_file.write_text("CUSTOM_OPENAI_KEY=alternate-secret\n", encoding="utf-8")
            mock = adjusted_valid_mock(
                base / "valid.json",
                root=root,
                provider="openai",
                model="gpt-test",
                model_version=None,
                run_id="alternate-env-001",
                submission_id="demo-alternate-env-001",
                completed_at="2026-06-18T12:00:00Z",
            )
            captured: dict[str, str] = {}

            def fake_call_openai(**kwargs: object) -> str:
                captured["api_key"] = str(kwargs["api_key"])
                return mock.read_text(encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True), patch(
                "scripts.model_reliability.run_external_model.call_openai",
                side_effect=fake_call_openai,
            ), redirect_stdout(StringIO()):
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
                        "alternate-env-001",
                        "--submission-id",
                        "demo-alternate-env-001",
                        "--completed-at",
                        "2026-06-18T12:00:00Z",
                        "--language-capability",
                        "fr",
                        "--language-capability",
                        "en",
                        "--setting",
                        "temperature=0",
                        "--no-disable-tools-note",
                        "--api-key-env",
                        "CUSTOM_OPENAI_KEY",
                        "--env-file",
                        str(env_file),
                        "--output-root",
                        str(output),
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(captured["api_key"], "alternate-secret")

    def test_no_env_file_disables_default_dotenv_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            (root / ".env").write_text("OPENAI_API_KEY=dotenv-secret\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True), redirect_stderr(StringIO()):
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
                        "--no-env-file",
                    ]
                )

            self.assertEqual(result, 2)

    def test_missing_dotenv_file_is_safe_when_mocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = runner_root(base)
            output = base / "reports" / "tmp" / "model-reliability"
            mock = adjusted_valid_mock(
                base / "valid.json",
                root=root,
                provider="anthropic",
                model="claude-test",
                model_version="fixture-v1",
                run_id="mock-001",
                submission_id="demo-mock-001",
                completed_at="2026-06-18T12:00:00Z",
            )

            with patch.dict(os.environ, {}, clear=True):
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

    def test_alternate_dotenv_parser_supports_comments_and_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv = Path(temp_dir) / "provider.env"
            dotenv.write_text(
                "\n".join(
                    [
                        "# local provider keys",
                        "OPENAI_API_KEY=\"quoted secret\" # comment",
                        "ANTHROPIC_API_KEY='anthropic#secret'",
                        "export CUSTOM_KEY=custom-value",
                        "BACKSLASH_KEY=\"keeps\\q-unknown\"",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            values = load_dotenv_values(dotenv)

            self.assertEqual(values["OPENAI_API_KEY"], "quoted secret")
            self.assertEqual(values["ANTHROPIC_API_KEY"], "anthropic#secret")
            self.assertEqual(values["CUSTOM_KEY"], "custom-value")
            self.assertEqual(values["BACKSLASH_KEY"], "keeps\\q-unknown")

    def test_openai_request_uses_responses_api_without_tools(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(
            url: str,
            headers: dict,
            body: dict,
            *,
            timeout_seconds: float = 180.0,
        ) -> dict:
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = body
            captured["timeout_seconds"] = timeout_seconds
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
                timeout_seconds=600.0,
            )

        self.assertEqual(text, '{"schema_version":"1.0.0"}')
        self.assertEqual(captured["url"], "https://api.openai.com/v1/responses")
        body = captured["body"]
        self.assertIsInstance(body, dict)
        self.assertNotIn("tools", body)
        self.assertNotIn("secret-key", json.dumps(body))
        self.assertEqual(captured["timeout_seconds"], 600.0)

    def test_anthropic_request_uses_messages_api_without_tools(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(
            url: str,
            headers: dict,
            body: dict,
            *,
            timeout_seconds: float = 180.0,
        ) -> dict:
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = body
            captured["timeout_seconds"] = timeout_seconds
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
                timeout_seconds=600.0,
            )

        self.assertEqual(text, '{"schema_version":"1.0.0"}')
        self.assertEqual(captured["url"], "https://api.anthropic.com/v1/messages")
        body = captured["body"]
        self.assertIsInstance(body, dict)
        self.assertNotIn("tools", body)
        self.assertNotIn("secret-key", json.dumps(body))
        self.assertEqual(captured["timeout_seconds"], 600.0)

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
