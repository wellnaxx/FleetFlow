import unittest
from decimal import Decimal

from src.adapters.driven.persistence.database.graph_loaders.shared import (
    link_packages_to_routes,
    link_route_trucks,
    map_joined_package_rows,
    map_packages_with_existing_customers,
)
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.truck_model import TruckModel
from src.domain.value_objects.contact_info import ContactInfo
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

    def test_map_packages_with_existing_customers_preserves_partial_route_id(self) -> None:
        customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))

        packages, package_route_ids = map_packages_with_existing_customers(
            [self._package_row(11, customer_id=7, route_id=21)],
            {7: customer},
        )

        package = packages[11]
        self.assertIs(package.customer, customer)
        self.assertIsNone(package.route)
        self.assertEqual(package.route_id, 21)
        self.assertEqual(package_route_ids, {11: 21})

    def test_map_joined_package_rows_preserves_partial_route_id(self) -> None:
        packages, customers, package_route_ids = map_joined_package_rows(
            [self._package_row(11, customer_id=7, route_id=21)]
        )

        package = packages[11]
        self.assertIsNone(package.route)
        self.assertEqual(package.route_id, 21)
        self.assertIs(package.customer, customers[7])
        self.assertEqual(package_route_ids, {11: 21})

    def test_link_packages_to_routes_hydrates_route_reference_without_losing_route_id(self) -> None:
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)
        packages, _, package_route_ids = map_joined_package_rows(
            [self._package_row(11, customer_id=7, route_id=21)]
        )
        package = packages[11]

        link_packages_to_routes({21: route}, packages, package_route_ids)

        self.assertIs(package.route, route)
        self.assertEqual(package.route_id, 21)
        self.assertEqual(route.packages, [package])

    def _package_row(self, package_id: int, *, customer_id: int, route_id: int | None) -> dict[str, object]:
        return {
            "package_id": package_id,
            "start_location": "SYD",
            "end_location": "MEL",
            "weight": Decimal("12.50"),
            "status": ItemStatus.IN_PROGRESS.value,
            "current_location": "SYD",
            "expected_arrival": None,
            "customer_id": customer_id,
            "route_id": route_id,
            "customer_name": "Alice",
            "customer_email": "alice@example.com",
            "customer_phone": "0412345678",
        }
