import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.adapters.driven.persistence.database.graph_loaders.world_graph_loader import HydratedWorldGraph
from src.adapters.driven.persistence.database.world_state_gateway import PostgresWorldStateGateway
from src.adapters.driven.persistence.memory.truck_repository import InMemoryTruckRepository
from src.application.dto.world_state_snapshot_dto import CountersSnapshot
from src.application.services.vehicle_manager import VehicleManager
from src.application.services.world_snapshot_validator import WorldStateSnapshotValidator
from src.application.services.world_state_linker import WorldStateSnapshotLinker
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.application.services.world_state_snapshot_builder import WorldStateSnapshotBuilder
from src.application.services.world_state_snapshot_preparer import WorldStateSnapshotPreparer
from src.application.services.world_state_snapshot_rebuilder import WorldStateSnapshotRebuilder
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.value_objects.contact_info import ContactInfo


class PostgresWorldStateGatewayRoundTripTests(unittest.TestCase):
    def test_exported_snapshot_can_be_prepared_for_import(self) -> None:
        truck_repo = InMemoryTruckRepository()
        vehicle_manager = VehicleManager(truck_repo)
        truck = vehicle_manager.find_by_id(1001)
        if truck is None:
            self.fail("Default fleet did not include truck 1001.")

        departure = datetime(2030, 1, 1, 9, 0)
        customer = Customer(ContactInfo("Alice Example", "alice@example.com", "0412345678"), customer_id=7)
        route = DeliveryRoute("SYD", "MEL", departure_time=departure, route_id=21)
        package = DeliveryPackage("SYD", "MEL", 12.5, customer, package_id=11)
        customer.restore_package_link(package)
        route.restore_package_link(package)
        route.truck = truck
        truck.assign(route)
        truck.current_location = "SYD"

        graph = HydratedWorldGraph(
            customers={customer.customer_id: customer},
            packages={package.package_id: package},
            routes={route.route_id: route},
            trucks={fleet_truck.vehicle_id: fleet_truck for fleet_truck in vehicle_manager.list_fleet()},
        )
        counters = CountersSnapshot(next_customer_id=8, next_package_id=12, next_route_id=22)
        importer = MagicMock()
        gateway = PostgresWorldStateGateway(
            snapshot_builder=WorldStateSnapshotBuilder(),
            snapshot_preparer=WorldStateSnapshotPreparer(
                reconciler=WorldStateReconciliationService(),
                validator=WorldStateSnapshotValidator(vehicle_manager=vehicle_manager),
                rebuilder=WorldStateSnapshotRebuilder(),
                linker=WorldStateSnapshotLinker(vehicle_manager=vehicle_manager),
            ),
            importer=importer,
            graph_loader=MagicMock(return_value=graph),
            counter_loader=MagicMock(return_value=counters),
        )

        snapshot = gateway.build_snapshot()
        gateway.apply_snapshot(snapshot)

        importer.import_world.assert_called_once()
        reconciled_world = importer.import_world.call_args.args[0]
        self.assertEqual(
            reconciled_world.counters,
            counters,
            f"expected counters to equal {counters}, got {reconciled_world.counters}",
        )
        self.assertEqual(
            tuple(reconciled_world.customers),
            (7,),
            f"expected customer ids (7,), got {tuple(reconciled_world.customers)}",
        )
        self.assertEqual(
            tuple(reconciled_world.packages),
            (11,),
            f"expected package ids (11,), got {tuple(reconciled_world.packages)}",
        )
        self.assertEqual(
            tuple(reconciled_world.routes),
            (21,),
            f"expected route ids (21,), got {tuple(reconciled_world.routes)}",
        )
        self.assertEqual(
            len(reconciled_world.truck_bindings),
            40,
            f"expected one truck binding per fleet truck, got {len(reconciled_world.truck_bindings)}",
        )
        binding = reconciled_world.truck_bindings[0]
        self.assertEqual(
            binding.truck.vehicle_id,
            1001,
            f"expected first truck binding to target 1001, got {binding.truck.vehicle_id}",
        )
        self.assertIs(
            binding.route,
            reconciled_world.routes[21],
            "expected route 21 to be the same object as the first truck binding route",
        )
