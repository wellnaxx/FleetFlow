import unittest
from unittest.mock import MagicMock

from src.adapters.driven.persistence.database.graph_loaders.world_graph_loader import HydratedWorldGraph
from src.adapters.driven.persistence.database.world_state_gateway import PostgresWorldStateGateway
from src.application.dto.reconciled_world_dto import ReconciledWorld
from src.application.dto.world_state_snapshot_dto import CountersSnapshot, WorldStateSnapshot
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.application.services.world_state_schema import SUPPORTED_SCHEMA_VERSIONS
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


class PostgresWorldStateGatewayTests(unittest.TestCase):
    def test_build_snapshot_loads_graph_and_builds_snapshot(self) -> None:
        customer = MagicMock(spec=Customer)
        package = MagicMock(spec=DeliveryPackage)
        route = MagicMock(spec=DeliveryRoute)
        truck = MagicMock(spec=Truck)
        counters = CountersSnapshot(
            next_customer_id=2,
            next_package_id=3,
            next_route_id=4,
        )
        snapshot = MagicMock(spec=WorldStateSnapshot)
        graph = HydratedWorldGraph(
            customers={1: customer},
            packages={2: package},
            routes={3: route},
            trucks={4: truck},
        )
        builder = MagicMock()
        graph_loader = MagicMock(return_value=graph)
        counter_loader = MagicMock(return_value=counters)
        preparer = MagicMock()
        importer = MagicMock()
        builder.build_world_state_snapshot.return_value = snapshot

        gateway = PostgresWorldStateGateway(
            snapshot_builder=builder,
            snapshot_preparer=preparer,
            importer=importer,
            graph_loader=graph_loader,
            counter_loader=counter_loader,
        )

        result = gateway.build_snapshot()

        self.assertIs(result, snapshot)
        graph_loader.assert_called_once_with()
        counter_loader.assert_called_once_with()
        builder.build_world_state_snapshot.assert_called_once()

        kwargs = builder.build_world_state_snapshot.call_args.kwargs
        self.assertEqual(list(kwargs["customers"]), [customer])
        self.assertEqual(list(kwargs["packages"]), [package])
        self.assertEqual(list(kwargs["routes"]), [route])
        self.assertEqual(list(kwargs["trucks"]), [truck])
        self.assertEqual(kwargs["counters"], counters)
        self.assertEqual(kwargs["schema_version"], 2)

    def test_apply_snapshot_prepares_and_imports_snapshot(self) -> None:
        snapshot = MagicMock(spec=WorldStateSnapshot)
        reconciled_world = MagicMock(spec=ReconciledWorld)
        preparer = MagicMock()
        importer = MagicMock()
        preparer.prepare.return_value = reconciled_world

        gateway = PostgresWorldStateGateway(
            snapshot_builder=MagicMock(),
            snapshot_preparer=preparer,
            importer=importer,
        )

        gateway.apply_snapshot(snapshot)

        preparer.prepare.assert_called_once()
        self.assertIs(preparer.prepare.call_args.args[0], snapshot)
        self.assertEqual(preparer.prepare.call_args.args[1], SUPPORTED_SCHEMA_VERSIONS)
        importer.import_world.assert_called_once_with(reconciled_world)

    def test_apply_snapshot_wraps_invalid_snapshot_errors(self) -> None:
        snapshot = MagicMock(spec=WorldStateSnapshot)
        preparer = MagicMock()
        importer = MagicMock()
        preparer.prepare.side_effect = ValueError("bad route")

        gateway = PostgresWorldStateGateway(
            snapshot_builder=MagicMock(),
            snapshot_preparer=preparer,
            importer=importer,
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            gateway.apply_snapshot(snapshot)

        self.assertIn("Invalid world state snapshot: bad route", str(ctx.exception))
        importer.import_world.assert_not_called()
