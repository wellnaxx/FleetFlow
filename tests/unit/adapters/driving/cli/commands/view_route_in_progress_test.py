import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.view_routes_in_progress import ViewRoutesInProgress


class ViewRoutesInProgress_Should(unittest.TestCase):
    def make_cmd(self) -> ViewRoutesInProgress:
        cmd = ViewRoutesInProgress.__new__(ViewRoutesInProgress)
        cmd._params = ()  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def _mk_route(self) -> MagicMock:
        return MagicMock()

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_VIEW_IN_PROGRESS")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ROUTE_VIEW_IN_PROGRESS", str(ctx.exception))
        cmd._use_case.execute.assert_called_once()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_no_routes_returns_friendly_message(self, mock_dt: MagicMock) -> None:
        fixed_now = datetime(2025, 9, 27, 10, 0, 0)
        mock_dt.now.return_value = fixed_now

        cmd = self.make_cmd()
        cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()

        cmd._use_case.execute.assert_called_once_with(fixed_now)  # type: ignore[reportUnknownMemberType]
        self.assertEqual(out, "No routes in progress.")

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.render_route_info")
    def test_formats_in_transit_and_at_stop(
        self,
        mock_render: MagicMock,
        mock_dt: MagicMock,
    ) -> None:
        fixed_now = datetime(2025, 9, 27, 11, 30)
        mock_dt.now.return_value = fixed_now

        cmd = self.make_cmd()

        route1 = self._mk_route()
        pos1 = SimpleNamespace(kind="IN_TRANSIT", from_city="SYD", to_city="MEL", next_eta="2025-10-12 06:00")

        route2 = self._mk_route()
        pos2 = SimpleNamespace(kind="AT_STOP", stop_city="MEL")

        mock_render.side_effect = ["Route 7: SYD → MEL", "Route 9: MEL → ADL"]
        cmd._use_case.execute.return_value = [  # type: ignore[reportAttributeAccessIssue]
            (route1, pos1),
            (route2, pos2),
        ]

        out = cmd.execute()

        cmd._use_case.execute.assert_called_once_with(fixed_now)  # type: ignore[reportUnknownMemberType]

        lines = out.split("\n")
        self.assertEqual(lines[0], "Route 7: SYD → MEL")
        self.assertEqual(lines[1], "  >> Currently between SYD → MEL, ETA 2025-10-12 06:00")
        self.assertEqual(lines[2], "")
        self.assertEqual(lines[3], "Route 9: MEL → ADL")
        self.assertEqual(lines[4], "  >> Currently at stop: MEL")
        self.assertEqual(lines[5], "")

        mock_render.assert_any_call(route1, position=pos1)
        mock_render.assert_any_call(route2, position=pos2)

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.render_route_info")
    def test_unknown_pos_kind_includes_only_route_info_and_blank_line(
        self,
        mock_render: MagicMock,
        mock_dt: MagicMock,
    ) -> None:
        mock_dt.now.return_value = datetime(2025, 9, 27, 12, 0)
        cmd = self.make_cmd()

        route = self._mk_route()
        pos = SimpleNamespace(kind="SOMETHING_ELSE")
        mock_render.return_value = "Route 1: A → B"

        cmd._use_case.execute.return_value = [(route, pos)]  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()
        lines = out.split("\n")

        self.assertEqual(lines, ["Route 1: A → B", ""])
        mock_render.assert_called_once_with(route, position=pos)

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.render_route_info")
    def test_multiple_entries_have_blank_separators(
        self,
        mock_render: MagicMock,
        mock_dt: MagicMock,
    ) -> None:
        mock_dt.now.return_value = datetime(2025, 9, 27, 13, 0)
        cmd = self.make_cmd()

        r1 = self._mk_route()
        p1 = SimpleNamespace(kind="AT_STOP", stop_city="X")

        r2 = self._mk_route()
        p2 = SimpleNamespace(kind="AT_STOP", stop_city="Y")
        mock_render.side_effect = ["R1", "R2"]

        cmd._use_case.execute.return_value = [(r1, p1), (r2, p2)]  # type: ignore[reportAttributeAccessIssue]
        out = cmd.execute()

        blanks = [i for i, line in enumerate(out.split("\n")) if line == ""]
        self.assertGreaterEqual(len(blanks), 2)

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_execute_propagates_errors_from_use_case(self, mock_dt: MagicMock) -> None:
        fixed_now = datetime(2025, 9, 27, 14, 0)
        mock_dt.now.return_value = fixed_now

        cmd = self.make_cmd()
        cmd._use_case.execute.side_effect = RuntimeError("db down")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db down", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(fixed_now)  # type: ignore[reportUnknownMemberType]

    def test_no_mutates_flags(self) -> None:
        self.assertFalse(getattr(ViewRoutesInProgress, "mutates_session", False))
        self.assertFalse(getattr(ViewRoutesInProgress, "mutates_state", False))
