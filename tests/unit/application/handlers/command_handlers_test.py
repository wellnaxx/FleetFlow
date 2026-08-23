"""Unit tests for command-to-use-case argument adaptation."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.commands.routes.assign_truck_to_route import AssignTruckToRouteCommand
from src.application.commands.routes.create_route import CreateRouteCommand
from src.application.commands.routes.remove_route import RemoveRouteCommand
from src.application.commands.state.load_world import LoadWorldCommand
from src.application.commands.state.save_world import SaveWorldCommand
from src.application.handlers.commands.routes.assign_truck_to_route import AssignTruckToRouteCommandHandler
from src.application.handlers.commands.routes.create_route import CreateRouteCommandHandler
from src.application.handlers.commands.routes.remove_route import RemoveRouteCommandHandler
from src.application.handlers.commands.state.load_world import LoadWorldCommandHandler
from src.application.handlers.commands.state.save_world import SaveWorldCommandHandler

NOW = datetime(2026, 8, 6, 12, 30)


class CommandHandlersShould(unittest.TestCase):
    """Verify that command handlers delegate once with the intended arguments."""

    def test_assign_truck_delegates_identifiers_and_time(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = AssignTruckToRouteCommandHandler(use_case).execute(
            AssignTruckToRouteCommand(truck_id=2, route_id=3, now=NOW)
        )

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(truck_id=2, route_id=3, now=NOW)

    def test_create_route_delegates_immutable_path_and_departure(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected
        command = CreateRouteCommand(locations=("SYD", "CBR", "MEL"), departure_time=NOW)

        result = CreateRouteCommandHandler(use_case).execute(command)

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(("SYD", "CBR", "MEL"), NOW)

    def test_remove_route_delegates_identifier_and_returns_route(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = RemoveRouteCommandHandler(use_case).execute(RemoveRouteCommand(route_id=8))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(8)

    def test_load_world_delegates_path_and_returns_resolved_path(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = "C:/snapshots/world.json"

        result = LoadWorldCommandHandler(use_case).execute(LoadWorldCommand(path="world.json"))

        self.assertEqual(result, "C:/snapshots/world.json")
        use_case.execute.assert_called_once_with("world.json")

    def test_save_world_delegates_path_and_returns_resolved_path(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = "C:/snapshots/world.json"

        result = SaveWorldCommandHandler(use_case).execute(SaveWorldCommand(path="world.json"))

        self.assertEqual(result, "C:/snapshots/world.json")
        use_case.execute.assert_called_once_with("world.json")


if __name__ == "__main__":
    unittest.main()
