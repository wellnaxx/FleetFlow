"""Tests for fleet-overview HTTP routing and event publication."""

import unittest
from datetime import datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.dependencies.auth import AuthenticatedHTTPPrincipal
from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.routers.api import fleet_router as fleet_router_module
from src.adapters.driving.http.routers.api.fleet_router import fleet_router
from src.application.exceptions.application_errors import ValidationError
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
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.fleet.get_overview import GetFleetOverviewUseCase
from src.composition.container import Container
from src.domain.enums.route_status import RouteStatus
from src.domain.value_objects.location_code import LocationCode

GENERATED_AT = datetime(2030, 1, 1, 12, 0)


class FleetRouterShould(unittest.TestCase):
    """Verify fleet-overview HTTP mapping, validation, and event drainage."""

    def setUp(self) -> None:
        """Create an isolated FastAPI app with overridden route dependencies."""
        self.app = FastAPI()
        self.app.include_router(fleet_router)
        register_exception_handlers(self.app)
        self.use_case = MagicMock(spec=GetFleetOverviewUseCase)
        self.event_collector = MagicMock()
        self.app.dependency_overrides[fleet_router_module.get_fleet_overview_use_case] = lambda: self.use_case
        self.app.dependency_overrides[fleet_router_module.get_event_collector] = lambda: self.event_collector
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        """Remove dependency overrides from the isolated application."""
        self.app.dependency_overrides.clear()

    def test_returns_nested_overview_and_forwards_explicit_limit(self) -> None:
        """Serialize the complete projection and forward the requested limit."""
        self.use_case.execute.return_value = _fleet_overview()

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
        self.use_case.execute.assert_called_once_with(active_route_limit=25)
        self.event_collector.drain.assert_called_once_with((self.use_case,))

    def test_uses_default_active_route_limit(self) -> None:
        """Use the endpoint's documented default when no query value is supplied."""
        self.use_case.execute.return_value = _fleet_overview()

        response = self.client.get("/fleet/overview")

        self.assertEqual(response.status_code, 200)
        self.use_case.execute.assert_called_once_with(active_route_limit=10)
        self.event_collector.drain.assert_called_once_with((self.use_case,))

    def test_rejects_active_route_limit_outside_supported_range(self) -> None:
        """Reject limits outside 1 through 100 before executing the use case."""
        for limit in (0, 101):
            with self.subTest(limit=limit):
                response = self.client.get(
                    "/fleet/overview",
                    params={"active_route_limit": limit},
                )

                self.assertEqual(response.status_code, 422)

        self.use_case.execute.assert_not_called()
        self.event_collector.drain.assert_not_called()

    def test_maps_known_use_case_failures_and_drains_events(self) -> None:
        """Map application and persistence failures after draining pending events."""
        cases = (
            (PermissionError("Missing permission: FLEET_OVERVIEW_VIEW"), 403, "Missing permission"),
            (ValidationError("invalid overview request"), 400, "invalid overview request"),
            (DatabaseError.read_failed(Exception("boom")), 500, "Database operation failed."),
        )

        for error, expected_status, expected_detail in cases:
            with self.subTest(error=error):
                self.use_case.reset_mock()
                self.event_collector.reset_mock()
                self.use_case.execute.side_effect = error

                response = self.client.get("/fleet/overview")

                self.assertEqual(response.status_code, expected_status)
                self.assertIn(expected_detail, response.json()["detail"])
                self.use_case.execute.assert_called_once_with(active_route_limit=10)
                self.event_collector.drain.assert_called_once_with((self.use_case,))


class FleetOverviewDependencyShould(unittest.TestCase):
    """Verify request-scoped fleet use-case construction."""

    def test_uses_container_query_clock_and_principal_authorization(self) -> None:
        """Bind the HTTP request principal to the configured overview query."""
        query = MagicMock()
        clock = MagicMock()
        authz = MagicMock(spec=AuthorizationService)
        principal = cast(
            AuthenticatedHTTPPrincipal,
            SimpleNamespace(authz=authz),
        )
        container = cast(
            Container,
            SimpleNamespace(
                fleet_overview_query=query,
                clock=clock,
            ),
        )

        use_case = fleet_router_module.get_fleet_overview_use_case(
            principal=principal,
            container=container,
        )

        self.assertIs(
            use_case._overview_query,  # pyright: ignore[reportPrivateUsage]
            query,
        )
        self.assertIs(use_case.authz, authz)
        self.assertIs(
            use_case._clock,  # pyright: ignore[reportPrivateUsage]
            clock,
        )


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
