import unittest
from datetime import datetime
from unittest.mock import patch

from src.adapters.driving.cli.rendering.route_info_renderer import render_route_info
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.value_objects.location_code import LocationCode

EVENT_TIME = datetime(2025, 1, 1, 7, 0)
LOCATIONS = (LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"))
DISTANCES = {
    ("AAA", "BBB"): 100,
    ("BBB", "CCC"): 200,
}


def _get_distance(start: str | LocationCode, end: str | LocationCode) -> int:
    return DISTANCES[(str(LocationCode(start)), str(LocationCode(end)))]


class RouteInfoRendererShould(unittest.TestCase):
    @patch("src.domain.entities.delivery_route.Map.get_locations", return_value=LOCATIONS)
    @patch("src.domain.entities.delivery_route.Map.get_distance", side_effect=_get_distance)
    def test_info_contains_key_lines(self, *_: object) -> None:
        base = datetime(2025, 1, 1, 8, 0)
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)
        route.schedule(base, occurred_at=EVENT_TIME)

        info = render_route_info(route)

        self.assertIn(f"Route ID: {route.route_id}", info)
        self.assertIn("Truck ID: Not assigned", info)
        self.assertIn("Start: AAA", info)
        self.assertIn("End: CCC", info)
        self.assertIn("Departure:", info)
        self.assertIn("Total Distance: 300 km", info)
        self.assertIn("Stops:", info)
        self.assertIn("Assigned weight: 0.00 kg", info)

        self.assertTrue(
            any(
                status_line in info
                for status_line in [
                    "Status: AT_STOP",
                    "Status: IN_TRANSIT",
                    "Status: BEFORE_START",
                    "Status: AFTER_END",
                ]
            )
        )
