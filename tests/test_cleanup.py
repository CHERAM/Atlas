import json
import tempfile
import unittest
from pathlib import Path

from atlas.core.cleanup import remove_cache_only, remove_hard_reset


class CleanupTests(unittest.TestCase):
    def _write_config(self, root: Path) -> None:
        config_path = root / "atlas.yaml"
        config_path.write_text(json.dumps({}), encoding="utf-8")

    def _create_dirs(self, root: Path) -> tuple[Path, Path, Path]:
        cache_dir = root / ".atlas-cache"
        github_dir = root / ".github" / "atlas"
        cache_dir.mkdir(parents=True, exist_ok=True)
        github_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "dummy.txt").write_text("x", encoding="utf-8")
        (github_dir / "context.md").write_text("x", encoding="utf-8")
        return cache_dir, github_dir, root / "atlas.yaml"

    def test_remove_cache_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root)
            cache_dir, github_dir, config_path = self._create_dirs(root)

            removed = remove_cache_only(start_path=root)

            self.assertIn(cache_dir, removed)
            self.assertFalse(cache_dir.exists())
            self.assertTrue(github_dir.exists())
            self.assertTrue(config_path.exists())

    def test_remove_hard_reset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root)
            cache_dir, github_dir, config_path = self._create_dirs(root)

            removed = remove_hard_reset(start_path=root)

            self.assertIn(cache_dir, removed)
            self.assertIn(github_dir, removed)
            self.assertIn(config_path, removed)
            self.assertFalse(cache_dir.exists())
            self.assertFalse(github_dir.exists())
            self.assertFalse(config_path.exists())


if __name__ == "__main__":
    unittest.main()
