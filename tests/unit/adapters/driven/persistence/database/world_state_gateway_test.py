import unittest
from unittest.mock import MagicMock

from src.adapters.driven.persistence.database.graph_loaders.world_graph_loader import HydratedWorldGraph
from src.adapters.driven.persistence.database.world_state_gateway import PostgresWorldStateGateway
from src.application.dto.world_state_snapshot_dto import CountersSnapshot, WorldStateSnapshot
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
        builder.build_world_state_snapshot.return_value = snapshot

        gateway = PostgresWorldStateGateway(
            snapshot_builder=builder,
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

    def test_apply_snapshot_is_not_implemented(self) -> None:
        gateway = PostgresWorldStateGateway(snapshot_builder=MagicMock())

        with self.assertRaises(NotImplementedError):
            gateway.apply_snapshot(MagicMock(spec=WorldStateSnapshot))
