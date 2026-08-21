"""Tests for fleet-overview HTTP routing."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.routers.api import fleet_router as fleet_router_module
from src.adapters.driving.http.routers.api.fleet_router import fleet_router
from src.application.exceptions.application_errors import ValidationError
from src.application.queries.fleet.get_fleet_overview import (
    GET_FLEET_OVERVIEW,
    GetFleetOverviewQuery,
)
from src.application.results.fleet_overview import (
    ActiveRouteOverview,
    AssignedTruckOverview,
    FleetOverview,
    InTransitPosition,
    PackageOverview,
    PackageStatusCounts,
    RouteOverview,
    RouteStatusCounts,
    TruckOverview,
    TruckStatusCounts,
)
from src.domain.enums.route_status import RouteStatus
from src.domain.value_objects.location_code import LocationCode
from src.ports.input.query_bus import QueryBus

GENERATED_AT = datetime(2030, 1, 1, 12, 0)


class FleetRouterShould(unittest.TestCase):
    """Verify fleet-overview query mapping, validation, and serialization."""

    def setUp(self) -> None:
        """Create an isolated FastAPI app with an overridden query bus."""
        self.app = FastAPI()
        self.app.include_router(fleet_router)
        register_exception_handlers(self.app)
        self.query_bus = MagicMock(spec=QueryBus)
        self.app.dependency_overrides[fleet_router_module.get_authenticated_query_bus] = lambda: self.query_bus
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        """Remove dependency overrides from the isolated application."""
        self.app.dependency_overrides.clear()

    def test_returns_nested_overview_and_dispatches_explicit_limit(self) -> None:
        """Serialize the complete projection and forward the requested limit."""
        self.query_bus.dispatch.return_value = _fleet_overview()

        response = self.client.get("/fleet/overview", params={"active_route_limit": 25})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["generated_at"], "2030-01-01T12:00:00")
        self.assertEqual(body["packages"]["by_status"]["total"], 6)
        self.assertEqual(body["routes"]["by_status"]["total"], 4)
        self.assertEqual(body["trucks"]["by_status"]["total"], 3)
        self.assertEqual(body["active_routes"][0]["route_id"], 21)
        self.assertEqual(body["active_routes"][0]["status"], "IN_PROGRESS")
        self.assertEqual(
            body["active_routes"][0]["position"],
            {
                "from_location": "SYD",
                "to_location": "MEL",
                "next_eta": "2030-01-01T14:00:00",
                "kind": "in_transit",
            },
        )
        self.assertEqual(body["active_routes"][0]["capacity_utilization_percent"], 25.0)
        self._assert_query(25)

    def test_uses_default_active_route_limit(self) -> None:
        """Use the endpoint's documented default when no value is supplied."""
        self.query_bus.dispatch.return_value = _fleet_overview()

        response = self.client.get("/fleet/overview")

        self.assertEqual(response.status_code, 200)
        self._assert_query(10)

    def test_rejects_active_route_limit_outside_supported_range(self) -> None:
        """Reject limits outside 1 through 100 before query dispatch."""
        for limit in (0, 101):
            with self.subTest(limit=limit):
                response = self.client.get(
                    "/fleet/overview",
                    params={"active_route_limit": limit},
                )

                self.assertEqual(response.status_code, 422)

        self.query_bus.dispatch.assert_not_called()

    def test_maps_known_query_failures(self) -> None:
        """Map application and persistence failures from query dispatch."""
        cases = (
            (PermissionError("Missing permission: FLEET_OVERVIEW_VIEW"), 403, "Missing permission"),
            (ValidationError("invalid overview request"), 400, "invalid overview request"),
            (DatabaseError.read_failed(Exception("boom")), 500, "Database operation failed."),
        )

        for error, expected_status, expected_detail in cases:
            with self.subTest(error=error):
                self.query_bus.reset_mock()
                self.query_bus.dispatch.side_effect = error

                response = self.client.get("/fleet/overview")

                self.assertEqual(response.status_code, expected_status)
                self.assertIn(expected_detail, response.json()["detail"])
                self._assert_query(10)

    def _assert_query(self, active_route_limit: int) -> None:
        """Assert one fleet-overview dispatch with the expected route limit."""
        self.query_bus.dispatch.assert_called_once()
        self.assertIs(self.query_bus.dispatch.call_args.kwargs["key"], GET_FLEET_OVERVIEW)
        query = self.query_bus.dispatch.call_args.kwargs["query"]
        self.assertIsInstance(query, GetFleetOverviewQuery)
        self.assertEqual(query.active_route_limit, active_route_limit)


def _fleet_overview() -> FleetOverview:
    """Return representative nested data for fleet-router response mapping."""
    return FleetOverview(
        generated_at=GENERATED_AT,
        packages=PackageOverview(
            by_status=PackageStatusCounts(todo=2, in_progress=1, done=3),
            unassigned=2,
            past_due=1,
        ),
        routes=RouteOverview(
            by_status=RouteStatusCounts(
                planned=1,
                scheduled=1,
                in_progress=1,
                completed=1,
            ),
            past_due=1,
        ),
        trucks=TruckOverview(
            by_status=TruckStatusCounts(free=2, on_the_way=1),
            unknown_location=1,
        ),
        active_routes=(
            ActiveRouteOverview(
                route_id=21,
                status=RouteStatus.IN_PROGRESS,
                start_location=LocationCode("SYD"),
                end_location=LocationCode("MEL"),
                position=InTransitPosition(
                    from_location=LocationCode("SYD"),
                    to_location=LocationCode("MEL"),
                    next_eta=datetime(2030, 1, 1, 14, 0),
                ),
                assigned_package_count=2,
                truck=AssignedTruckOverview(truck_id=1001, capacity=1_000),
                maximum_segment_load=250,
            ),
        ),
    )


if __name__ == "__main__":
    unittest.main()
