import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.view_unassigned_packages import ViewUnassignedPackages


class ViewUnassignedPackages_Should(unittest.TestCase):
    def make_cmd(
        self,
        params: list[str] | None = None,
        *,
        authorized: bool = True,
    ) -> ViewUnassignedPackages:
        cmd = ViewUnassignedPackages.__new__(ViewUnassignedPackages)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]

        cmd._authz = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._authz.has.return_value = authorized  # type: ignore[reportAttributeAccessIssue]

        return cmd

    def test_execute_without_permission_raises(self) -> None:
        cmd = self.make_cmd(authorized=False)

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("PACKAGE_VIEW_UNASSIGNED", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    def test_no_packages_returns_friendly_message(self) -> None:
        cmd = self.make_cmd(authorized=True)
        cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()

        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        self.assertEqual(out, "No unassigned packages.")

    def test_formats_multiple_packages_separated_by_blank_line(self) -> None:
        cmd = self.make_cmd(authorized=True)

        p1 = MagicMock()
        p2 = MagicMock()
        p3 = MagicMock()
        p1.info.return_value = "PKG#1 info"
        p2.info.return_value = "PKG#2 info"
        p3.info.return_value = "PKG#3 info"

        cmd._use_case.execute.return_value = [  # type: ignore[reportAttributeAccessIssue]
            p1,
            p2,
            p3,
        ]

        out = cmd.execute()

        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        p1.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        p2.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        p3.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

        self.assertEqual(out, "PKG#1 info\n\nPKG#2 info\n\nPKG#3 info")

    def test_execute_propagates_errors_from_use_case(self) -> None:
        cmd = self.make_cmd(authorized=True)
        cmd._use_case.execute.side_effect = RuntimeError("db down")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db down", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_ignores_params_if_present(self) -> None:
        cmd = self.make_cmd(params=["ignored", "also-ignored"], authorized=True)
        cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_no_mutates_flags(self) -> None:
        self.assertFalse(getattr(ViewUnassignedPackages, "mutates_state", False))
        self.assertFalse(getattr(ViewUnassignedPackages, "mutates_session", False))
