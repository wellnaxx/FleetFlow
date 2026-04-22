import unittest
from unittest.mock import MagicMock

from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.adapters.driven.persistence.memory.world_state_gateway import InMemoryWorldStateGateway
from src.application.config.state_persistence import DEFAULT_WORLD_STATE_PATH
from src.application.services.authorization_service import AuthorizationService
from src.composition.container import Container
from src.domain.services.vehicle_manager import VehicleManager


class ContainerTests(unittest.TestCase):
    def test_container_uses_in_memory_runtime_owners(self) -> None:
        auth = MagicMock()
        auth.current_user = None

        container = Container(auth)

        self.assertIsInstance(container.customer_repo, InMemoryCustomerRepository)
        self.assertIsInstance(container.package_repo, InMemoryPackageRepository)
        self.assertIsInstance(container.route_repo, InMemoryRouteRepository)
        self.assertIsInstance(container.vehicle_manager, VehicleManager)
        self.assertIsInstance(container.world_state_gateway, InMemoryWorldStateGateway)
        self.assertIsInstance(container.authz, AuthorizationService)
        self.assertIs(container.authz.current_user, auth.current_user)
        self.assertIs(container.save_world_state_use_case._world_state_gateway, container.world_state_gateway)  # type: ignore[attr-defined]
        self.assertEqual(container.default_world_state_path, DEFAULT_WORLD_STATE_PATH)
