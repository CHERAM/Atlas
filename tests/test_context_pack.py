import unittest

from atlas.context.assembler import ContextAssembler
from atlas.context.writer import ContextWriter
from atlas.search.models import SearchResult


class ContextPackTests(unittest.TestCase):
    def test_context_pack_sections_and_critical_split(self) -> None:
        results = [
            SearchResult(
                result_id="1",
                repo_name="repo-a",
                file_path="README.md",
                start_line=1,
                end_line=12,
                snippet="Architecture summary",
                score=0.95,
                reason="architecture-doc-boost",
                category="architecture",
                is_critical=True,
            ),
            SearchResult(
                result_id="2",
                repo_name="repo-b",
                file_path="src/main.py",
                start_line=20,
                end_line=50,
                snippet="Execution path",
                score=0.7,
                reason="vector=0.700",
                category="execution",
                is_critical=False,
            ),
        ]

        pack = ContextAssembler().assemble(query="sample query", results=results)

        self.assertEqual(pack.query, "sample query")
        self.assertTrue(pack.critical_snippets)
        self.assertEqual(pack.critical_snippets[0].repo_name, "repo-a")
        self.assertTrue(pack.supporting_snippets)
        self.assertEqual(pack.supporting_snippets[0].repo_name, "repo-b")

        rendered = ContextWriter()._to_markdown(pack)

        self.assertIn("## Query", rendered)
        self.assertIn("## Relevant Repositories", rendered)
        self.assertIn("## Architecture Overview", rendered)
        self.assertIn("## Critical Snippets", rendered)
        self.assertIn("## Supporting Snippets", rendered)
        self.assertIn("## Cross-Repo Notes", rendered)
        self.assertIn("## Suggested Prompt For AI Agent Usage", rendered)

    def test_context_rebalances_when_all_results_marked_critical(self) -> None:
        results = [
            SearchResult(
                result_id="1",
                repo_name="repo-a",
                file_path="README.md",
                start_line=1,
                end_line=5,
                snippet="Architecture summary",
                score=0.9,
                reason="r1",
                category="architecture",
                is_critical=True,
            ),
            SearchResult(
                result_id="2",
                repo_name="repo-b",
                file_path="src/app.py",
                start_line=10,
                end_line=20,
                snippet="Execution summary",
                score=0.8,
                reason="r2",
                category="execution",
                is_critical=True,
            ),
        ]

        pack = ContextAssembler().assemble(
            query="sample query",
            results=results,
            allow_all_critical=False,
        )
        self.assertTrue(pack.critical_snippets)
        self.assertTrue(pack.supporting_snippets)

        allow_all = ContextAssembler().assemble(
            query="sample query",
            results=results,
            allow_all_critical=True,
        )
        self.assertEqual(len(allow_all.critical_snippets), 2)
        self.assertFalse(allow_all.supporting_snippets)

    def test_context_dedupes_prompt_and_cross_repo_paths(self) -> None:
        results = [
            SearchResult(
                result_id="1",
                repo_name="repo-a",
                file_path="README.md",
                start_line=1,
                end_line=5,
                snippet="Architecture summary",
                score=0.9,
                reason="r1",
                category="architecture",
                is_critical=True,
            ),
            SearchResult(
                result_id="2",
                repo_name="repo-a",
                file_path="README.md",
                start_line=6,
                end_line=10,
                snippet="Architecture summary details",
                score=0.85,
                reason="r2",
                category="architecture",
                is_critical=True,
            ),
        ]

        pack = ContextAssembler().assemble(query="sample query", results=results)
        self.assertEqual(len(pack.critical_snippets), 1)
        self.assertIn("README.md", pack.suggested_handoff_prompt)
        self.assertEqual(pack.suggested_handoff_prompt.count("README.md"), 1)


if __name__ == "__main__":
    unittest.main()
