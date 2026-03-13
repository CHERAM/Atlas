import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from typer.testing import CliRunner

from atlas.cli.app import app
from atlas.core.books import (
    BooksError,
    INSTRUCTION_FILENAME,
    PERSONA_END_MARKER,
    PERSONA_FILENAME,
    PERSONA_START_MARKER,
    default_templates,
    pull_templates,
    seed_default_templates,
)


class BooksTemplateTests(unittest.TestCase):
    def _write_config(self, root: Path, repos: list[dict] | None = None) -> None:
        payload = {"repos": repos or []}
        (root / "atlas.yaml").write_text(json.dumps(payload), encoding="utf-8")

    def test_seed_default_templates_creates_all_files_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            books_dir = Path(tmp) / ".atlas" / "books"
            first = seed_default_templates(books_dir)
            second = seed_default_templates(books_dir)

            self.assertEqual(len(first), 7)
            self.assertEqual(len(second), 7)
            self.assertEqual(len(list(books_dir.glob("*.md"))), 7)

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
            self.assertEqual(len(summary.copied_files), expected_count + 4)
            self.assertTrue((repo_a / ".github" / "Atlas-Code-Review.md").exists())
            self.assertTrue((repo_b / ".github" / "Atlas-Bug-Fix.md").exists())
            self.assertTrue((repo_a / ".github" / PERSONA_FILENAME).exists())
            self.assertTrue((repo_a / ".github" / INSTRUCTION_FILENAME).exists())
            self.assertTrue((repo_b / ".github" / "copilot-instructions.md").exists())

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
            self.assertIn("atlas-persona", result.stdout)
            self.assertIn("atlas-instruction", result.stdout)

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
            self.assertTrue((root / ".github" / PERSONA_FILENAME).exists())
            self.assertTrue((root / ".github" / INSTRUCTION_FILENAME).exists())
            self.assertTrue((root / ".github" / "copilot-instructions.md").exists())

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
            self.assertEqual(content.count(PERSONA_START_MARKER), 1)
            self.assertEqual(content.count(PERSONA_END_MARKER), 1)
            self.assertIn("Continue in Auto or Manual mode?", content)
            self.assertIn("In Manual mode, do not run shell commands.", content)
            self.assertIn('`atlas search "<prompt>"`', content)
            self.assertIn('`atlas context "<prompt>"`', content)
            self.assertIn("Context ready? yes/no", content)
            self.assertIn("types `capabilities` (or `strengths`)", content)

    def test_init_bootstraps_persona_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._chdir(root):
                result = self.runner.invoke(app, ["init"], catch_exceptions=False)
            self.assertEqual(result.exit_code, 0)
            self.assertTrue((root / ".github" / PERSONA_FILENAME).exists())
            self.assertTrue((root / ".github" / INSTRUCTION_FILENAME).exists())
            instructions = root / ".github" / "copilot-instructions.md"
            self.assertTrue(instructions.exists())
            content = instructions.read_text(encoding="utf-8")
            self.assertIn(PERSONA_START_MARKER, content)
            self.assertIn(PERSONA_END_MARKER, content)
            self.assertIn("Persona Strengths", content)
            self.assertIn("Continue in Auto or Manual mode?", content)
            self.assertIn("In Manual mode, do not run shell commands.", content)

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
            self.assertIn("## My ", content, f"Missing process section in {path.name}")

    def test_books_templates_do_not_contain_codebuddy(self) -> None:
        source_dir = Path("src/atlas/templates/books")
        for path in source_dir.glob("*.md"):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("CodeBuddy", content, f"Found CodeBuddy in {path.name}")


if __name__ == "__main__":
    unittest.main()
