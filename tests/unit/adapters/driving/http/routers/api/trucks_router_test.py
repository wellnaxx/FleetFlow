import unittest
from datetime import datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.routers.api import trucks_router as trucks_router_module
from src.adapters.driving.http.routers.api.trucks_router import trucks_router
from src.application.queries.trucks.view_all_trucks import VIEW_ALL_TRUCKS, ViewAllTrucksQuery
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.ports.input.query_bus import QueryBus


class TrucksRouterShould(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(trucks_router)
        register_exception_handlers(self.app)
        self.query_bus = MagicMock(spec=QueryBus)
        self.app.dependency_overrides[trucks_router_module.get_authenticated_query_bus] = lambda: (
            self.query_bus
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_trucks_returns_truck_responses(self) -> None:
        truck = Truck(vehicle_id=1, name="Scania", capacity=42000, max_range=8000)
        truck.current_location = "SYD"
        self.query_bus.dispatch.return_value = [truck]

        response = self.client.get("/trucks/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "vehicle_id": 1,
                    "name": "Scania",
                    "capacity": 42000,
                    "max_range": 8000,
                    "status": "Free",
                    "current_location": "SYD",
                    "route_id": None,
                    "busy_from": None,
                    "busy_until": None,
                    "in_transit_to": None,
                }
            ],
        )
        self._assert_listing_dispatched()

    def test_list_trucks_returns_empty_list(self) -> None:
        self.query_bus.dispatch.return_value = []

        response = self.client.get("/trucks/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self._assert_listing_dispatched()

    def test_list_trucks_maps_assignment_fields(self) -> None:
        busy_from = datetime(2026, 5, 25, 9, 30)
        busy_until = datetime(2026, 5, 25, 15, 45)
        route = DeliveryRoute("SYD", "MEL", route_id=21)
        truck = Truck(vehicle_id=2, name="Actros", capacity=38000, max_range=7000)
        truck.status = TruckStatus.ON_THE_WAY
        truck.current_location = "CBR"
        truck.route = route
        truck.busy_from = busy_from
        truck.busy_until = busy_until
        truck.in_transit_to = "MEL"
        self.query_bus.dispatch.return_value = [truck]

        response = self.client.get("/trucks/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["vehicle_id"], 2)
        self.assertEqual(response.json()[0]["name"], "Actros")
        self.assertEqual(response.json()[0]["status"], "On the way")
        self.assertEqual(response.json()[0]["current_location"], "CBR")
        self.assertEqual(response.json()[0]["route_id"], 21)
        self.assertEqual(response.json()[0]["busy_from"], "2026-05-25T09:30:00")
        self.assertEqual(response.json()[0]["busy_until"], "2026-05-25T15:45:00")
        self.assertEqual(response.json()[0]["in_transit_to"], "MEL")
        self._assert_listing_dispatched()

    def test_list_trucks_returns_forbidden_for_permission_error(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: TRUCK_VIEW")

        response = self.client.get("/trucks/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: TRUCK_VIEW")
        self._assert_listing_dispatched()

    def test_list_trucks_returns_generic_error_for_database_failure(self) -> None:
        self.query_bus.dispatch.side_effect = DatabaseError.read_failed(Exception("boom"))

        response = self.client.get("/trucks/")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Database operation failed.")
        self._assert_listing_dispatched()

    def _assert_listing_dispatched(self) -> None:
        """Assert dispatch of the canonical fieldless truck query."""
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_TRUCKS,
            query=ViewAllTrucksQuery(),
        )
