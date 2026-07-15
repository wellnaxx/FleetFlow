import unittest
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.view_all_trucks import ViewAllTrucks


class ViewAllTrucks_Should(unittest.TestCase):
    def make_cmd(self) -> ViewAllTrucks:
        cmd = ViewAllTrucks.__new__(ViewAllTrucks)
        cmd._params = ()  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: TRUCK_VIEW")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("TRUCK_VIEW", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_no_trucks_exist(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "No trucks.")
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_all_trucks.render_truck_info")
    def test_with_multiple_trucks(self, mock_render: MagicMock) -> None:
        cmd = self.make_cmd()
        truck1 = MagicMock()
        truck2 = MagicMock()
        mock_render.side_effect = ["Truck 1 Info", "Truck 2 Info"]
        cmd._use_case.execute.return_value = [truck1, truck2]  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "Truck 1 Info\n\nTruck 2 Info")
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        self.assertEqual(mock_render.call_args_list, [call(truck1), call(truck2)])
