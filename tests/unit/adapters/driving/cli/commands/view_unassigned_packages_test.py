import unittest
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.view_unassigned_packages import ViewUnassignedPackages
from src.application.use_cases.pagination import PageResult


class ViewUnassignedPackages_Should(unittest.TestCase):
    def make_cmd(
        self,
        params: list[str] | None = None,
    ) -> ViewUnassignedPackages:
        cmd = ViewUnassignedPackages.__new__(ViewUnassignedPackages)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: PACKAGE_VIEW_UNASSIGNED")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("PACKAGE_VIEW_UNASSIGNED", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        cmd._event_collector.drain.assert_called_once_with((cmd._use_case,))  # type: ignore[reportUnknownMemberType]

    def test_no_packages_returns_friendly_message(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.return_value = PageResult(items=(), total=None, limit=None, offset=0)  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()

        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        self.assertEqual(out, "No unassigned packages.")

    @patch("src.adapters.driving.cli.commands.view_unassigned_packages.render_package_info")
    def test_formats_multiple_packages_separated_by_blank_line(self, mock_render: MagicMock) -> None:
        cmd = self.make_cmd()

        p1 = MagicMock()
        p2 = MagicMock()
        p3 = MagicMock()
        mock_render.side_effect = ["PKG#1 info", "PKG#2 info", "PKG#3 info"]

        cmd._use_case.execute.return_value = PageResult(  # type: ignore[reportAttributeAccessIssue]
            items=(p1, p2, p3),
            total=None,
            limit=None,
            offset=0,
        )

        out = cmd.execute()

        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        self.assertEqual(mock_render.call_args_list, [call(p1), call(p2), call(p3)])

        self.assertEqual(out, "PKG#1 info\n\nPKG#2 info\n\nPKG#3 info")

    def test_execute_propagates_errors_from_use_case(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.side_effect = RuntimeError("db down")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db down", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        cmd._event_collector.drain.assert_called_once_with((cmd._use_case,))  # type: ignore[reportUnknownMemberType]

    def test_ignores_params_if_present(self) -> None:
        cmd = self.make_cmd(params=["ignored", "also-ignored"])
        cmd._use_case.execute.return_value = PageResult(items=(), total=None, limit=None, offset=0)  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_no_mutates_flags(self) -> None:
        self.assertFalse(getattr(ViewUnassignedPackages, "mutates_state", False))
        self.assertFalse(getattr(ViewUnassignedPackages, "mutates_session", False))
