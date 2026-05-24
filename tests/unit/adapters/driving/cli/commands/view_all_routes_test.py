import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.view_all_routes import ViewAllRoutes
from src.application.use_cases.pagination import PageResult


class TestViewAllRoutes_Should(unittest.TestCase):
    def make_cmd(self) -> ViewAllRoutes:
        cmd = ViewAllRoutes.__new__(ViewAllRoutes)
        cmd._params = ()  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_VIEW_ALL")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ROUTE_VIEW_ALL", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_no_routes_available(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.return_value = PageResult(items=(), total=None, limit=None, offset=0)  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "No routes available.")
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_with_multiple_routes(self) -> None:
        cmd = self.make_cmd()

        mock_route1 = MagicMock()
        mock_route1.info.return_value = "Route 1 Info"

        mock_route2 = MagicMock()
        mock_route2.info.return_value = "Route 2 Info"

        cmd._use_case.execute.return_value = PageResult(  # type: ignore[reportAttributeAccessIssue]
            items=(mock_route1, mock_route2),
            total=None,
            limit=None,
            offset=0,
        )

        result = cmd.execute()

        self.assertEqual(result, "Route 1 Info\n\nRoute 2 Info")
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        mock_route1.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        mock_route2.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_execute_propagates_errors_from_use_case(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.side_effect = RuntimeError("db down")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db down", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_no_mutates_flags(self) -> None:
        self.assertFalse(getattr(ViewAllRoutes, "mutates_state", False))
        self.assertFalse(getattr(ViewAllRoutes, "mutates_session", False))
