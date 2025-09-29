import unittest
from unittest.mock import MagicMock

from src.commands.view_unassigned_packages import ViewUnassignedPackages


class ViewUnassignedPackages_Should(unittest.TestCase):
    def make_cmd(self, params=None):
        cmd = ViewUnassignedPackages.__new__(ViewUnassignedPackages)
        cmd._params = params or []
        cmd._app_data = MagicMock()
        return cmd

    def test_no_packages_returns_friendly_message(self):
        cmd = self.make_cmd()
        cmd._app_data.view_unassigned_packages.return_value = []

        out = cmd.execute()

        cmd._app_data.view_unassigned_packages.assert_called_once_with()
        self.assertEqual(out, "No unassigned packages.")

    def test_formats_multiple_packages_separated_by_blank_line(self):
        cmd = self.make_cmd()

        p1 = MagicMock()
        p2 = MagicMock()
        p3 = MagicMock()
        p1.info.return_value = "PKG#1 info"
        p2.info.return_value = "PKG#2 info"
        p3.info.return_value = "PKG#3 info"

        cmd._app_data.view_unassigned_packages.return_value = [p1, p2, p3]

        out = cmd.execute()

        # Ensure info() was called on each package
        p1.info.assert_called_once_with()
        p2.info.assert_called_once_with()
        p3.info.assert_called_once_with()

        # Expect exactly two blank-line separators, no trailing newline
        self.assertEqual(out, "PKG#1 info\n\nPKG#2 info\n\nPKG#3 info")

    def test_execute_propagates_errors_from_app_data(self):
        cmd = self.make_cmd()
        cmd._app_data.view_unassigned_packages.side_effect = RuntimeError("db down")

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db down", str(ctx.exception))

    def test_ignores_params_if_present(self):
        cmd = self.make_cmd(params=["ignored", "also-ignored"])
        cmd._app_data.view_unassigned_packages.return_value = []
        _ = cmd.execute()
        cmd._app_data.view_unassigned_packages.assert_called_once_with()

    def test_no_mutates_flags(self):
        self.assertFalse(getattr(ViewUnassignedPackages, "mutates_state", False))
        self.assertFalse(getattr(ViewUnassignedPackages, "mutates_session", False))
