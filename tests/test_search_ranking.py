import unittest

from atlas.search.ranking import rank_chunks
from atlas.storage.models import ChunkView
from atlas.storage.vector_store import VectorHit


class SearchRankingPathTests(unittest.TestCase):
    def test_repo_source_paths_are_normalized_for_display(self) -> None:
        hit = VectorHit(chunk_id="c1", score=0.8)
        chunk = ChunkView(
            chunk_id="c1",
            document_id="d1",
            source_type="repo",
            source_name="repo-a",
            repo_name="repo-a",
            workspace_relative_path=".codebuddy-cache/repos/repo-a/src/app.py",
            source_relative_path="src/app.py",
            file_type="code",
            language_hint="py",
            title_hint="app",
            section_title=None,
            chunk_index=0,
            start_line=1,
            end_line=10,
            text="def main(): pass",
            token_estimate=5,
            content_hash="h1",
            metadata_json="{}",
        )

        results = rank_chunks([hit], [chunk], critical_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].file_path, "src/app.py")


if __name__ == "__main__":
    unittest.main()
