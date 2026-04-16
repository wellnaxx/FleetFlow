import unittest
from unittest.mock import MagicMock

from adapters.driving.cli.commands.view_unassigned_packages import ViewUnassignedPackages


class ViewUnassignedPackages_Should(unittest.TestCase):
    def make_cmd(self, params: list[str] | None = None) -> ViewUnassignedPackages:
        cmd = ViewUnassignedPackages.__new__(ViewUnassignedPackages)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_no_packages_returns_friendly_message(self) -> None:
        cmd = self.make_cmd()
        cmd._app_data.view_unassigned_packages.return_value = []  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()

        cmd._app_data.view_unassigned_packages.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        self.assertEqual(out, "No unassigned packages.")

    def test_formats_multiple_packages_separated_by_blank_line(self) -> None:
        cmd = self.make_cmd()

        p1 = MagicMock()
        p2 = MagicMock()
        p3 = MagicMock()
        p1.info.return_value = "PKG#1 info"  # type: ignore[reportAttributeAccessIssue]
        p2.info.return_value = "PKG#2 info"  # type: ignore[reportAttributeAccessIssue]
        p3.info.return_value = "PKG#3 info"  # type: ignore[reportAttributeAccessIssue]

        cmd._app_data.view_unassigned_packages.return_value = [p1, p2, p3]  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()

        # Ensure info() was called on each package
        p1.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        p2.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        p3.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

        # Expect exactly two blank-line separators, no trailing newline
        self.assertEqual(out, "PKG#1 info\n\nPKG#2 info\n\nPKG#3 info")

    def test_execute_propagates_errors_from_app_data(self) -> None:
        cmd = self.make_cmd()
        cmd._app_data.view_unassigned_packages.side_effect = RuntimeError("db down")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db down", str(ctx.exception))

    def test_ignores_params_if_present(self) -> None:
        cmd = self.make_cmd(params=["ignored", "also-ignored"])
        cmd._app_data.view_unassigned_packages.return_value = []  # type: ignore[reportAttributeAccessIssue]
        _ = cmd.execute()
        cmd._app_data.view_unassigned_packages.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_no_mutates_flags(self) -> None:
        self.assertFalse(getattr(ViewUnassignedPackages, "mutates_state", False))
        self.assertFalse(getattr(ViewUnassignedPackages, "mutates_session", False))
