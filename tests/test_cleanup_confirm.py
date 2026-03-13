import unittest

import typer

from atlas.cli.commands.clean import _confirm as clean_confirm
from atlas.cli.commands.reset import _confirm as reset_confirm


class ConfirmTests(unittest.TestCase):
    def test_confirm_force_skips_prompt(self) -> None:
        called = {"value": False}

        def fake_confirm(_message: str, default: bool = False) -> bool:
            called["value"] = True
            return False

        clean_confirm(True, "msg", confirm_fn=fake_confirm)
        reset_confirm(True, "msg", confirm_fn=fake_confirm)
        self.assertFalse(called["value"])

    def test_confirm_requires_yes(self) -> None:
        def fake_confirm(_message: str, default: bool = False) -> bool:
            return False

        with self.assertRaises(typer.Exit):
            clean_confirm(False, "msg", confirm_fn=fake_confirm)

        with self.assertRaises(typer.Exit):
            reset_confirm(False, "msg", confirm_fn=fake_confirm)


if __name__ == "__main__":
    unittest.main()
