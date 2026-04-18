import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.view_routes_in_progress import ViewRoutesInProgress


class ViewRoutesInProgress_Should(unittest.TestCase):
    def make_cmd(self, *, authorized: bool = True) -> ViewRoutesInProgress:
        cmd = ViewRoutesInProgress.__new__(ViewRoutesInProgress)
        cmd._params = ()  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]

        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data.authz = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data.authz.has.return_value = authorized  # type: ignore[reportAttributeAccessIssue]

        cmd._auth = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def _mk_route(self, text: str) -> MagicMock:
        r = MagicMock()
        r.info.return_value = text
        return r

    def test_execute_without_permission_raises(self) -> None:
        cmd = self.make_cmd(authorized=False)

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ROUTE_VIEW_IN_PROGRESS", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_no_routes_returns_friendly_message(self, mock_dt: MagicMock) -> None:
        fixed_now = datetime(2025, 9, 27, 10, 0, 0)
        mock_dt.now.return_value = fixed_now

        cmd = self.make_cmd(authorized=True)
        cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()

        cmd._use_case.execute.assert_called_once_with(fixed_now)  # type: ignore[reportUnknownMemberType]
        self.assertEqual(out, "No routes in progress.")

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_formats_in_transit_and_at_stop(self, mock_dt: MagicMock) -> None:
        fixed_now = datetime(2025, 9, 27, 11, 30)
        mock_dt.now.return_value = fixed_now

        cmd = self.make_cmd(authorized=True)

        route1 = self._mk_route("Route 7: SYD → MEL")
        pos1 = SimpleNamespace(kind="IN_TRANSIT", from_city="SYD", to_city="MEL", next_eta="2025-10-12 06:00")

        route2 = self._mk_route("Route 9: MEL → ADL")
        pos2 = SimpleNamespace(kind="AT_STOP", stop_city="MEL")

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

        route1.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        route2.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_unknown_pos_kind_includes_only_route_info_and_blank_line(self, mock_dt: MagicMock) -> None:
        mock_dt.now.return_value = datetime(2025, 9, 27, 12, 0)
        cmd = self.make_cmd(authorized=True)

        route = self._mk_route("Route 1: A → B")
        pos = SimpleNamespace(kind="SOMETHING_ELSE")

        cmd._use_case.execute.return_value = [(route, pos)]  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()
        lines = out.split("\n")

        self.assertEqual(lines, ["Route 1: A → B", ""])
        route.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_multiple_entries_have_blank_separators(self, mock_dt: MagicMock) -> None:
        mock_dt.now.return_value = datetime(2025, 9, 27, 13, 0)
        cmd = self.make_cmd(authorized=True)

        r1 = self._mk_route("R1")
        p1 = SimpleNamespace(kind="AT_STOP", stop_city="X")

        r2 = self._mk_route("R2")
        p2 = SimpleNamespace(kind="AT_STOP", stop_city="Y")

        cmd._use_case.execute.return_value = [(r1, p1), (r2, p2)]  # type: ignore[reportAttributeAccessIssue]
        out = cmd.execute()

        blanks = [i for i, line in enumerate(out.split("\n")) if line == ""]
        self.assertGreaterEqual(len(blanks), 2)

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_execute_propagates_errors_from_use_case(self, mock_dt: MagicMock) -> None:
        fixed_now = datetime(2025, 9, 27, 14, 0)
        mock_dt.now.return_value = fixed_now

        cmd = self.make_cmd(authorized=True)
        cmd._use_case.execute.side_effect = RuntimeError("db down")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db down", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(fixed_now)  # type: ignore[reportUnknownMemberType]

    def test_no_mutates_flags(self) -> None:
        self.assertFalse(getattr(ViewRoutesInProgress, "mutates_session", False))
        self.assertFalse(getattr(ViewRoutesInProgress, "mutates_state", False))
