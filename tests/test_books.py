import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from typer.testing import CliRunner

from atlas.cli.app import app
from atlas.core.books import (
    AGENTS_FILENAME,
    BooksError,
    CLAUDE_FILENAME,
    COPILOT_INSTRUCTIONS_FILENAME,
    CONTRACT_FILENAME,
    INSTRUCTION_FILENAME,
    MODE_END_MARKER,
    MODE_FILENAME,
    MODE_START_MARKER,
    default_templates,
    pull_templates,
    seed_default_templates,
)


class BooksTemplateTests(unittest.TestCase):
    def _write_config(
        self,
        root: Path,
        repos: list[dict] | None = None,
        agents: list[str] | None = None,
    ) -> None:
        payload = {"repos": repos or []}
        if agents is not None:
            payload["agents"] = {"selected": agents}
        (root / "atlas.yaml").write_text(json.dumps(payload), encoding="utf-8")

    def test_seed_default_templates_creates_all_files_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            books_dir = Path(tmp) / ".atlas" / "books"
            first = seed_default_templates(books_dir)
            second = seed_default_templates(books_dir)
            expected = len(default_templates())

            self.assertEqual(len(first), expected)
            self.assertEqual(len(second), expected)
            self.assertEqual(len(list(books_dir.glob("*.md"))), expected)

    def test_pull_single_template_to_current_workspace_github(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root)
            destination = root / ".github" / "Atlas-Prompt-Creation.md"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("old", encoding="utf-8")

            summary = pull_templates(
                name="prompt-creation",
                pull_all=False,
                all_repos=False,
                start_path=root,
            )

            self.assertEqual(len(summary.copied_files), 1)
            self.assertIn(destination, summary.copied_files)
            self.assertIn("Instructions for Atlas Prompt Creation", destination.read_text("utf-8"))

    def test_pull_all_repos_copies_templates_to_each_repo_github(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_a = root / ".atlas-cache" / "repos" / "repo-a"
            repo_b = root / ".atlas-cache" / "repos" / "repo-b"
            repo_a.mkdir(parents=True, exist_ok=True)
            repo_b.mkdir(parents=True, exist_ok=True)
            repos = [
                {
                    "name": "repo-a",
                    "url": "https://example.com/repo-a.git",
                    "branch": "main",
                    "local_path": ".atlas-cache/repos/repo-a",
                    "enabled": True,
                },
                {
                    "name": "repo-b",
                    "url": "https://example.com/repo-b.git",
                    "branch": "main",
                    "local_path": ".atlas-cache/repos/repo-b",
                    "enabled": True,
                },
            ]
            self._write_config(root, repos=repos)

            summary = pull_templates(
                name=None,
                pull_all=True,
                all_repos=True,
                start_path=root,
            )

            expected_count = len(default_templates()) * 2
            self.assertEqual(len(summary.copied_files), expected_count + 6)
            self.assertTrue((repo_a / ".github" / "Atlas-Code-Review.md").exists())
            self.assertTrue((repo_b / ".github" / "Atlas-Bug-Fix.md").exists())
            self.assertTrue((repo_a / ".github" / MODE_FILENAME).exists())
            self.assertTrue((repo_a / ".github" / INSTRUCTION_FILENAME).exists())
            self.assertTrue((repo_a / ".github" / "atlas" / CONTRACT_FILENAME).exists())
            self.assertTrue((repo_b / ".github" / "copilot-instructions.md").exists())
            self.assertTrue((repo_b / CLAUDE_FILENAME).exists())
            self.assertTrue((repo_b / AGENTS_FILENAME).exists())

    def test_pull_all_uses_configured_agent_subset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, agents=["copilot"])

            summary = pull_templates(
                name=None,
                pull_all=True,
                all_repos=False,
                start_path=root,
            )

            self.assertTrue((root / ".github" / COPILOT_INSTRUCTIONS_FILENAME).exists())
            self.assertFalse((root / CLAUDE_FILENAME).exists())
            self.assertFalse((root / AGENTS_FILENAME).exists())
            self.assertTrue(any(path.name == COPILOT_INSTRUCTIONS_FILENAME for path in summary.copied_files))

    def test_pull_unknown_template_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root)
            with self.assertRaises(BooksError):
                pull_templates(
                    name="not-a-template",
                    pull_all=False,
                    all_repos=False,
                    start_path=root,
                )


class BooksCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    @contextmanager
    def _chdir(self, path: Path):
        original = Path.cwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(original)

    def test_books_list_shows_default_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "atlas.yaml").write_text(json.dumps({}), encoding="utf-8")

            with self._chdir(root):
                result = self.runner.invoke(app, ["books", "list"], catch_exceptions=False)
            self.assertEqual(result.exit_code, 0)
            self.assertIn("prompt-creation", result.stdout)
            self.assertIn("java-test-creation", result.stdout)
            self.assertIn("atlas-mode", result.stdout)
            self.assertIn("atlas-instruction", result.stdout)
            self.assertIn("atlas-agent-contract", result.stdout)

    def test_books_pull_all_copies_all_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "atlas.yaml").write_text(json.dumps({}), encoding="utf-8")

            with self._chdir(root):
                result = self.runner.invoke(
                    app,
                    ["books", "pull", "--all"],
                    catch_exceptions=False,
                )
            self.assertEqual(result.exit_code, 0)
            self.assertTrue((root / ".github" / "Atlas-Prompt-Creation.md").exists())
            self.assertTrue((root / ".github" / "Atlas-Java-Test-Creation.md").exists())
            self.assertTrue((root / ".github" / MODE_FILENAME).exists())
            self.assertTrue((root / ".github" / INSTRUCTION_FILENAME).exists())
            self.assertTrue((root / ".github" / "atlas" / CONTRACT_FILENAME).exists())
            self.assertTrue((root / ".github" / "copilot-instructions.md").exists())
            self.assertTrue((root / CLAUDE_FILENAME).exists())
            self.assertTrue((root / AGENTS_FILENAME).exists())

    def test_books_pull_all_is_idempotent_for_managed_block_and_preserves_user_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "atlas.yaml").write_text(json.dumps({}), encoding="utf-8")
            github_dir = root / ".github"
            github_dir.mkdir(parents=True, exist_ok=True)
            instructions = github_dir / "copilot-instructions.md"
            instructions.write_text("My custom note\n", encoding="utf-8")

            with self._chdir(root):
                first = self.runner.invoke(app, ["books", "pull", "--all"], catch_exceptions=False)
                second = self.runner.invoke(app, ["books", "pull", "--all"], catch_exceptions=False)

            self.assertEqual(first.exit_code, 0)
            self.assertEqual(second.exit_code, 0)
            content = instructions.read_text(encoding="utf-8")
            self.assertIn("My custom note", content)
            self.assertEqual(content.count("<!-- ATLAS:COPILOT_START -->"), 1)
            self.assertEqual(content.count("<!-- ATLAS:COPILOT_END -->"), 1)
            self.assertIn(".github/atlas/agent-contract.md", content)
            self.assertIn("selected mode directly", content.lower())

            claude = (root / CLAUDE_FILENAME).read_text(encoding="utf-8")
            self.assertEqual(claude.count("<!-- ATLAS:CLAUDE_START -->"), 1)
            self.assertEqual(claude.count("<!-- ATLAS:CLAUDE_END -->"), 1)
            self.assertIn(".github/atlas/agent-contract.md", claude)

            agents = (root / AGENTS_FILENAME).read_text(encoding="utf-8")
            self.assertEqual(agents.count("<!-- ATLAS:AGENTS_START -->"), 1)
            self.assertEqual(agents.count("<!-- ATLAS:AGENTS_END -->"), 1)
            self.assertIn(".github/atlas/agent-contract.md", agents)

    def test_init_bootstraps_mode_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._chdir(root):
                result = self.runner.invoke(
                    app, ["init", "--agents", "copilot"], catch_exceptions=False
                )
            self.assertEqual(result.exit_code, 0)
            self.assertTrue((root / ".github" / MODE_FILENAME).exists())
            self.assertTrue((root / ".github" / INSTRUCTION_FILENAME).exists())
            self.assertTrue((root / ".github" / "atlas" / CONTRACT_FILENAME).exists())
            instructions = root / ".github" / COPILOT_INSTRUCTIONS_FILENAME
            self.assertTrue(instructions.exists())
            content = instructions.read_text(encoding="utf-8")
            self.assertIn("<!-- ATLAS:COPILOT_START -->", content)
            self.assertIn("<!-- ATLAS:COPILOT_END -->", content)
            self.assertIn(".github/atlas/agent-contract.md", content)
            self.assertFalse((root / CLAUDE_FILENAME).exists())
            self.assertFalse((root / AGENTS_FILENAME).exists())

    def test_init_without_agents_fails_in_non_interactive_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._chdir(root):
                result = self.runner.invoke(app, ["init"], catch_exceptions=False)
            self.assertNotEqual(result.exit_code, 0)

    def test_init_with_multiple_agents_writes_selected_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._chdir(root):
                result = self.runner.invoke(
                    app, ["init", "--agents", "claude,codex"], catch_exceptions=False
                )
            self.assertEqual(result.exit_code, 0)
            self.assertFalse((root / ".github" / COPILOT_INSTRUCTIONS_FILENAME).exists())
            self.assertTrue((root / CLAUDE_FILENAME).exists())
            self.assertTrue((root / AGENTS_FILENAME).exists())

    def test_all_runtime_books_have_required_sections(self) -> None:
        required_sections = [
            "## Activation and Welcome",
            "## Instructions",
            "## Activation & Deactivation",
            "## While Active, I Will",
        ]

        source_dir = Path("src/atlas/templates/books")
        for path in source_dir.glob("*.md"):
            if path.name == "Atlas-Book-Template.md":
                continue
            content = path.read_text(encoding="utf-8")
            for heading in required_sections:
                self.assertIn(heading, content, f"Missing '{heading}' in {path.name}")

    def test_books_templates_do_not_contain_codebuddy(self) -> None:
        source_dir = Path("src/atlas/templates/books")
        for path in source_dir.glob("*.md"):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("CodeBuddy", content, f"Found CodeBuddy in {path.name}")

    def test_agent_contract_contains_mode_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._chdir(root):
                result = self.runner.invoke(
                    app, ["init", "--agents", "copilot"], catch_exceptions=False
                )
            self.assertEqual(result.exit_code, 0)
            contract = (root / ".github" / "atlas" / CONTRACT_FILENAME).read_text(encoding="utf-8")
            self.assertIn("Book mode selection flow", contract)
            self.assertIn("Select a mode by number or name", contract)
            self.assertIn(".github/atlas/context.md", contract)
            self.assertNotIn("Auto mode", contract)
            self.assertNotIn("Manual mode", contract)


if __name__ == "__main__":
    unittest.main()
