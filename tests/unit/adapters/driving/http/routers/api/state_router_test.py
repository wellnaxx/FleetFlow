import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.routers.api import state_router as state_router_module
from src.adapters.driving.http.routers.api.state_router import state_router
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.world_state_errors import (
    WorldStateCorruptionError,
    WorldStateFileNotFoundError,
    WorldStatePersistenceError,
    WorldStateRuntimeSwapError,
)


class StateRouterShould(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(state_router)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_save_world_returns_snapshot_metadata(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = "C:/snapshots/world.json"
        self.app.dependency_overrides[state_router_module.get_save_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"path": "C:/snapshots/world.json", "message": "World state saved."},
        )
        saved_path = use_case.execute.call_args.args[0]
        self.assertEqual(Path(saved_path).name, "world.json")

    def test_save_world_rejects_invalid_path_before_use_case(self) -> None:
        use_case = MagicMock()
        self.app.dependency_overrides[state_router_module.get_save_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/save", json={"path": "../world.json"})

        self.assertEqual(response.status_code, 422)
        use_case.execute.assert_not_called()

    def test_save_world_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: APP_SAVE_STATE")
        self.app.dependency_overrides[state_router_module.get_save_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: APP_SAVE_STATE")

    def test_save_world_returns_bad_request_for_validation_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = ValidationError("Invalid snapshot path.")
        self.app.dependency_overrides[state_router_module.get_save_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid snapshot path.")

    def test_save_world_returns_generic_error_for_persistence_failure(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = WorldStatePersistenceError("C:/secret/path/world.json denied")
        self.app.dependency_overrides[state_router_module.get_save_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")

    def test_save_world_returns_generic_error_for_database_failure(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = DatabaseError.write_failed(Exception("secret connection info"))
        self.app.dependency_overrides[state_router_module.get_save_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")

    def test_save_world_returns_generic_error_for_world_state_persistence_failure(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = WorldStatePersistenceError("C:/secret/world.json denied")
        self.app.dependency_overrides[state_router_module.get_save_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/save", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")

    def test_load_world_returns_snapshot_metadata(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = "C:/snapshots/world.json"
        self.app.dependency_overrides[state_router_module.get_load_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"path": "C:/snapshots/world.json", "message": "World state loaded."},
        )
        loaded_path = use_case.execute.call_args.args[0]
        self.assertEqual(Path(loaded_path).name, "world.json")

    def test_load_world_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: APP_LOAD_STATE")
        self.app.dependency_overrides[state_router_module.get_load_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: APP_LOAD_STATE")

    def test_load_world_returns_not_found_without_leaking_path(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = WorldStateFileNotFoundError("missing C:/secret/world.json")
        self.app.dependency_overrides[state_router_module.get_load_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "World state snapshot not found.")

    def test_load_world_returns_bad_request_for_corrupt_snapshot_without_leaking_path(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = WorldStateCorruptionError("bad C:/secret/world.json")
        self.app.dependency_overrides[state_router_module.get_load_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "World state snapshot is malformed.")

    def test_load_world_returns_bad_request_for_validation_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = ValidationError("Invalid world state snapshot.")
        self.app.dependency_overrides[state_router_module.get_load_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid world state snapshot.")

    def test_load_world_returns_generic_error_for_database_failure(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = DatabaseError.read_failed(Exception("secret connection info"))
        self.app.dependency_overrides[state_router_module.get_load_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")

    def test_load_world_returns_generic_error_for_persistence_failure(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = WorldStatePersistenceError("C:/secret/world.json denied")
        self.app.dependency_overrides[state_router_module.get_load_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")

    def test_load_world_returns_generic_error_for_runtime_swap_failure(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = WorldStateRuntimeSwapError("rollback failed with secret state")
        self.app.dependency_overrides[state_router_module.get_load_world_state_use_case] = lambda: use_case

        response = self.client.post("/state/load", json={"path": "world.json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "World state persistence failed.")
