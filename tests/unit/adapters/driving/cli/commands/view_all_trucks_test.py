import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.view_all_trucks import ViewAllTrucks


class ViewAllTrucks_Should(unittest.TestCase):
    def make_cmd(self) -> ViewAllTrucks:
        cmd = ViewAllTrucks.__new__(ViewAllTrucks)
        cmd._params = ()  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
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

    def test_with_multiple_trucks(self) -> None:
        cmd = self.make_cmd()
        truck1 = MagicMock()
        truck1.info.return_value = "Truck 1 Info"
        truck2 = MagicMock()
        truck2.info.return_value = "Truck 2 Info"
        cmd._use_case.execute.return_value = [truck1, truck2]  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "Truck 1 Info\n\nTruck 2 Info")
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
