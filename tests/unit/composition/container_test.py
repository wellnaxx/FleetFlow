import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.world_state_gateway import PostgresWorldStateGateway
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
        self.assertIs(container.state_cases.save._world_state_gateway, container.world_state_gateway)  # type: ignore[attr-defined]
        self.assertEqual(container.default_world_state_path, "state.json")

    @patch("src.composition.container.PostgresUnitOfWork")
    @patch("src.composition.container.PostgresTruckRepository")
    @patch("src.composition.container.PostgresRouteRepository")
    @patch("src.composition.container.PostgresCustomerRepository")
    @patch("src.composition.container.PostgresPackageRepository")
    def test_container_uses_postgres_runtime_owners(
        self,
        package_repo_cls: MagicMock,
        customer_repo_cls: MagicMock,
        route_repo_cls: MagicMock,
        truck_repo_cls: MagicMock,
        unit_of_work_cls: MagicMock,
    ) -> None:
        auth = MagicMock()
        auth.current_user = None
        truck_repo = MagicMock()
        truck_repo.list_fleet.return_value = [object()]
        truck_repo_cls.return_value = truck_repo
        set_json_config(
            JSONConfig(
                state_path=Path("state.json"),
                export_dir=Path("exports"),
                user_store_path=Path("users.json"),
            )
        )

        container = Container(auth, AppConfig(persistence_backend=PersistenceBackend.POSTGRES))

        self.assertIs(container.package_repo, package_repo_cls.return_value)
        self.assertIs(container.customer_repo, customer_repo_cls.return_value)
        self.assertIs(container.route_repo, route_repo_cls.return_value)
        self.assertIs(container.truck_repo, truck_repo)
        self.assertIs(container.unit_of_work, unit_of_work_cls.return_value)
        self.assertIsInstance(container.world_state_gateway, PostgresWorldStateGateway)
        self.assertFalse(container.autosave_enabled)
        self.assertIsNone(container.world_state_runtime)
        self.assertIsNone(container.world_state_snapshot_service)
        self.assertIs(container.state_cases.save._world_state_gateway, container.world_state_gateway)  # type: ignore[attr-defined]
