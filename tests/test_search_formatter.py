import unittest

from atlas.search.formatter import format_search_results
from atlas.search.models import SearchResult


class SearchFormatterTests(unittest.TestCase):
    def test_format_search_results_includes_required_fields(self) -> None:
        results = [
            SearchResult(
                result_id="abc",
                repo_name="repo-a",
                file_path="src/app.py",
                start_line=10,
                end_line=20,
                snippet="def main():\n    return 1",
                score=0.91,
                reason="vector=0.910, section-context",
                category="execution",
                is_critical=True,
            )
        ]

        rendered = format_search_results(results)

        self.assertIn("repo-a :: src/app.py", rendered)
        self.assertIn("lines: 10-20", rendered)
        self.assertIn("score: 0.910", rendered)
        self.assertIn("reason: vector=0.910, section-context", rendered)
        self.assertIn("snippet:", rendered)

    def test_format_search_results_empty_message(self) -> None:
        self.assertEqual(format_search_results([]), "No search results found.")


if __name__ == "__main__":
    unittest.main()
