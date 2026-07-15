import unittest
from datetime import datetime

from src.adapters.driving.cli.rendering.package_info_renderer import render_package_info
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode


class PackageInfoRendererShould(unittest.TestCase):
    def test_render_unassigned_package_with_missing_optional_contact_fields(self) -> None:
        customer = Customer(ContactInfo("Dan"), 1)
        package = DeliveryPackage(LocationCode("SYD"), LocationCode("BRI"), 500, customer, 7)

        result = render_package_info(package)

        self.assertEqual(
            result,
            "Package 7: SYD -> BRI, 500.0kg\n"
            "Customer: Dan (No email provided, No phone number provided)\n"
            "Assigned route: Not assigned\n"
            "Expected arrival: Not assigned",
        )

    def test_render_partially_hydrated_route_and_expected_arrival(self) -> None:
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), 1)
        package = DeliveryPackage(
            LocationCode("SYD"),
            LocationCode("BRI"),
            500,
            customer,
            7,
            route_id=21,
        )
        package.expected_arrival = datetime(2026, 7, 15, 14, 30)

        result = render_package_info(package)

        self.assertEqual(
            result,
            "Package 7: SYD -> BRI, 500.0kg\n"
            "Customer: Dan (dan@e.com, 0484568777)\n"
            "Assigned route: 21\n"
            "Expected arrival: 2026-07-15 14:30",
        )
