import unittest
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.routers.api import state_router as state_router_module
from src.adapters.driving.http.routers.api.state_router import state_router
from src.adapters.driving.http.schemas.state import WorldStatePathRequest
from src.application.commands.state.load_world import LOAD_WORLD, LoadWorldCommand
from src.application.commands.state.save_world import SAVE_WORLD, SaveWorldCommand
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.world_state_errors import (
    WorldStateCorruptionError,
    WorldStateFileNotFoundError,
    WorldStatePersistenceError,
    WorldStateRuntimeSwapError,
)
from src.ports.input.command_bus import CommandBus


class StateRouterShould(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(state_router)
        register_exception_handlers(self.app)
        self.command_bus = MagicMock(spec=CommandBus)
        self.app.dependency_overrides[state_router_module.get_authenticated_command_bus] = lambda: (
            self.command_bus
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_save_world_returns_snapshot_metadata(self) -> None:
        self.command_bus.dispatch.return_value = "C:/snapshots/world.json"

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"path": "C:/snapshots/world.json", "message": "World state saved."},
        )
        self._assert_save_dispatched()

    def test_save_world_rejects_invalid_path_before_dispatch(self) -> None:
        response = self.client.post("/state/save", json={"path": "../world.json"})

        self.assertEqual(response.status_code, 422)
        self.command_bus.dispatch.assert_not_called()

    def test_save_world_returns_forbidden_for_permission_error(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: APP_SAVE_STATE")

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: APP_SAVE_STATE")
        self._assert_save_dispatched()

    def test_save_world_returns_bad_request_for_validation_error(self) -> None:
        self.command_bus.dispatch.side_effect = ValidationError("Invalid snapshot path.")

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid snapshot path.")
        self._assert_save_dispatched()

    def test_save_world_returns_generic_error_for_persistence_failure(self) -> None:
        self.command_bus.dispatch.side_effect = WorldStatePersistenceError(
            "C:/secret/path/world.json denied"
        )

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")
        self._assert_save_dispatched()

    def test_save_world_returns_generic_error_for_database_failure(self) -> None:
        self.command_bus.dispatch.side_effect = DatabaseError.write_failed(
            Exception("secret connection info")
        )

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")
        self._assert_save_dispatched()

    def test_load_world_returns_snapshot_metadata(self) -> None:
        self.command_bus.dispatch.return_value = "C:/snapshots/world.json"

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"path": "C:/snapshots/world.json", "message": "World state loaded."},
        )
        self.command_bus.dispatch.assert_called_once_with(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path=self._resolved_world_path()),
        )

    def test_load_world_returns_forbidden_for_permission_error(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: APP_LOAD_STATE")

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: APP_LOAD_STATE")
        self._assert_load_dispatched()

    def test_load_world_returns_not_found_without_leaking_path(self) -> None:
        self.command_bus.dispatch.side_effect = WorldStateFileNotFoundError(
            "missing C:/secret/world.json"
        )

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "World state snapshot not found.")
        self._assert_load_dispatched()

    def test_load_world_returns_bad_request_for_corrupt_snapshot_without_leaking_path(self) -> None:
        self.command_bus.dispatch.side_effect = WorldStateCorruptionError(
            "bad C:/secret/world.json",
            reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
        )

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "World state snapshot is malformed.")
        self._assert_load_dispatched()

    def test_load_world_returns_bad_request_for_validation_error(self) -> None:
        self.command_bus.dispatch.side_effect = ValidationError("Invalid world state snapshot.")

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid world state snapshot.")
        self._assert_load_dispatched()

    def test_load_world_returns_generic_error_for_database_failure(self) -> None:
        self.command_bus.dispatch.side_effect = DatabaseError.read_failed(
            Exception("secret connection info")
        )

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")
        self._assert_load_dispatched()

    def test_load_world_returns_generic_error_for_persistence_failure(self) -> None:
        self.command_bus.dispatch.side_effect = WorldStatePersistenceError(
            "C:/secret/world.json denied"
        )

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")
        self._assert_load_dispatched()

    def test_load_world_returns_generic_error_for_runtime_swap_failure(self) -> None:
        self.command_bus.dispatch.side_effect = WorldStateRuntimeSwapError(
            "rollback failed with secret state"
        )

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")
        self._assert_load_dispatched()

    def _assert_load_dispatched(self) -> None:
        """Assert the endpoint dispatched the canonical world-load command."""
        self.command_bus.dispatch.assert_called_once_with(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path=self._resolved_world_path()),
        )

    def _assert_save_dispatched(self) -> None:
        """Assert the endpoint dispatched the canonical world-save command."""
        self.command_bus.dispatch.assert_called_once_with(
            key=SAVE_WORLD,
            command=SaveWorldCommand(path=self._resolved_world_path()),
        )

    @staticmethod
    def _resolved_world_path() -> str:
        """Return the path produced by HTTP request validation for the fixture input."""
        return WorldStatePathRequest(path="world.json").path
