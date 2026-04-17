import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.view_routes_in_progress import ViewRoutesInProgress


class ViewRoutesInProgress_Should(unittest.TestCase):
    def make_cmd(self) -> ViewRoutesInProgress:
        cmd = ViewRoutesInProgress.__new__(ViewRoutesInProgress)
        cmd._params = []  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def _mk_route(self, text: str) -> MagicMock:
        r = MagicMock()
        r.info.return_value = text
        return r

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_no_routes_returns_friendly_message(self, mock_dt: MagicMock) -> None:
        fixed_now = datetime(2025, 9, 27, 10, 0, 0)
        mock_dt.now.return_value = fixed_now

        cmd = self.make_cmd()
        cmd._app_data.view_routes_in_progress.return_value = []  # type: ignore[reportPrivateUsage]

        out = cmd.execute()

        cmd._app_data.view_routes_in_progress.assert_called_once_with(now=fixed_now)  # type: ignore[reportPrivateUsage]
        self.assertEqual(out, "No routes in progress.")

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_formats_in_transit_and_at_stop(self, mock_dt: MagicMock) -> None:
        fixed_now = datetime(2025, 9, 27, 11, 30)
        mock_dt.now.return_value = fixed_now

        cmd = self.make_cmd()

        route1 = self._mk_route("Route 7: SYD → MEL")
        pos1 = SimpleNamespace(kind="IN_TRANSIT", from_city="SYD", to_city="MEL", next_eta="2025-10-12 06:00")

        route2 = self._mk_route("Route 9: MEL → ADL")
        pos2 = SimpleNamespace(kind="AT_STOP", stop_city="MEL")

        cmd._app_data.view_routes_in_progress.return_value = [  # type: ignore[reportPrivateUsage]
            (route1, pos1),
            (route2, pos2),
        ]

        out = cmd.execute()

        cmd._app_data.view_routes_in_progress.assert_called_once_with(now=fixed_now)  # type: ignore[reportPrivateUsage]

        lines = out.split("\n")
        self.assertEqual(lines[0], "Route 7: SYD → MEL")
        self.assertEqual(lines[1], "  >> Currently between SYD → MEL, ETA 2025-10-12 06:00")
        self.assertEqual(lines[2], "")
        self.assertEqual(lines[3], "Route 9: MEL → ADL")
        self.assertEqual(lines[4], "  >> Currently at stop: MEL")
        self.assertEqual(lines[5], "")

        # Ensure info() was called on each route
        route1.info.assert_called_once_with()
        route2.info.assert_called_once_with()

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_unknown_pos_kind_includes_only_route_info_and_blank_line(self, mock_dt: MagicMock) -> None:
        mock_dt.now.return_value = datetime(2025, 9, 27, 12, 0)
        cmd = self.make_cmd()

        route = self._mk_route("Route 1: A → B")
        pos = SimpleNamespace(kind="SOMETHING_ELSE")

        cmd._app_data.view_routes_in_progress.return_value = [(route, pos)]  # type: ignore[reportPrivateUsage]

        out = cmd.execute()
        lines = out.split("\n")
        # Only route line + blank line
        self.assertEqual(lines, ["Route 1: A → B", ""])
        route.info.assert_called_once_with()

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_multiple_entries_have_blank_separators(self, mock_dt: MagicMock) -> None:
        mock_dt.now.return_value = datetime(2025, 9, 27, 13, 0)
        cmd = self.make_cmd()

        r1 = self._mk_route("R1")
        p1 = SimpleNamespace(kind="AT_STOP", stop_city="X")

        r2 = self._mk_route("R2")
        p2 = SimpleNamespace(kind="AT_STOP", stop_city="Y")

        cmd._app_data.view_routes_in_progress.return_value = [(r1, p1), (r2, p2)]  # type: ignore[reportPrivateUsage]
        out = cmd.execute()

        # Expect two blank lines (one after each entry)
        blanks = [i for i, line in enumerate(out.split("\n")) if line == ""]
        self.assertGreaterEqual(len(blanks), 2)

    def test_no_mutates_flags(self) -> None:
        self.assertFalse(getattr(ViewRoutesInProgress, "mutates_session", False))
        # mutates_state is not declared; ensure it isn't present (or False)
        self.assertFalse(getattr(ViewRoutesInProgress, "mutates_state", False))
