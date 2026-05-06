import unittest

from src.adapters.driven.persistence.database.graph_loaders.shared import link_route_trucks
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel
from src.domain.value_objects.location_code import LocationCode


class GraphLoaderSharedHelpersShould(unittest.TestCase):
    def test_link_route_trucks_raises_when_route_id_is_missing(self) -> None:
        routes = {
            21: DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21),
        }
        trucks = {
            1001: Truck(1001, TruckModel.SCANIA, 42000, 8000),
        }

        with self.assertRaises(ValueError) as ctx:
            link_route_trucks(routes, trucks, {22: 1001})

        self.assertIn("Route truck mapping references missing route 22.", str(ctx.exception))
