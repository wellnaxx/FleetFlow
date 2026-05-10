import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.adapters.driven.persistence.json.config import JSONConfig, set_json_config
from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.adapters.driven.persistence.memory.world_state_gateway import InMemoryWorldStateGateway
from src.application.services.authorization_service import AuthorizationService
from src.composition.config import AppConfig, PersistenceBackend
from src.composition.container import Container
from src.domain.services.vehicle_manager import VehicleManager


class ContainerTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_json_config(None)

    def test_container_uses_in_memory_runtime_owners(self) -> None:
        auth = MagicMock()
        auth.current_user = None
        set_json_config(
            JSONConfig(
                state_path=Path("state.json"),
                export_dir=Path("exports"),
                user_store_path=Path("users.json"),
            )
        )

        container = Container(auth, AppConfig(persistence_backend=PersistenceBackend.MEMORY))

        self.assertIsInstance(container.customer_repo, InMemoryCustomerRepository)
        self.assertIsInstance(container.package_repo, InMemoryPackageRepository)
        self.assertIsInstance(container.route_repo, InMemoryRouteRepository)
        self.assertIsInstance(container.vehicle_manager, VehicleManager)
        self.assertIsInstance(container.world_state_gateway, InMemoryWorldStateGateway)
        self.assertTrue(container.autosave_enabled)
        self.assertIsInstance(container.authz, AuthorizationService)
        self.assertIs(container.authz.current_user, auth.current_user)
        self.assertIs(container.world_state_gateway._snapshot_service, container.world_state_snapshot_service)  # type: ignore[attr-defined]
        self.assertIs(container.save_world_state_use_case._world_state_gateway, container.world_state_gateway)  # type: ignore[attr-defined]
        self.assertEqual(container.default_world_state_path, "state.json")
