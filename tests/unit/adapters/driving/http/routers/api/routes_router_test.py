import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.routers.api import routes_router as routes_router_module
from src.adapters.driving.http.routers.api.routes_router import routes_router
from src.application.commands.routes.assign_packages_to_route import (
    ASSIGN_PACKAGES_TO_ROUTE,
    AssignPackagesToRouteCommand,
)
from src.application.commands.routes.assign_truck_to_route import (
    ASSIGN_TRUCK_TO_ROUTE,
    AssignTruckToRouteCommand,
)
from src.application.commands.routes.create_route import CREATE_ROUTE, CreateRouteCommand
from src.application.commands.routes.remove_route import REMOVE_ROUTE, RemoveRouteCommand
from src.application.exceptions.application_errors import ConflictError, NotFoundError, ValidationError
from src.application.queries.routes.find_suitable_trucks_for_route import (
    FIND_SUITABLE_TRUCKS_FOR_ROUTE,
    FindSuitableTrucksForRouteQuery,
)
from src.application.queries.routes.view_all_routes import VIEW_ALL_ROUTES, ViewAllRoutesQuery
from src.application.queries.routes.view_route import VIEW_ROUTE, ViewRouteQuery
from src.application.queries.routes.view_routes_in_progress import (
    VIEW_ROUTES_IN_PROGRESS,
    ViewRoutesInProgressQuery,
)
from src.application.results.assign_packages_to_route_result import (
    AssignPackagesToRouteResult,
    PackageAssignmentError,
    PackageAssignmentSuccess,
)
from src.application.results.assign_truck_to_route_result import AssignTruckToRouteResult
from src.application.use_cases.pagination import PageQuery, PageResult
from src.domain.entities.delivery_route import DeliveryRoute, RoutePosition, RoutePositionKind
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from src.ports.input.command_bus import CommandBus
from src.ports.input.query_bus import QueryBus

NOW = datetime(2026, 8, 26, 12, 30)


class RoutesRouterShould(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(routes_router)
        register_exception_handlers(self.app)
        self.command_bus = MagicMock(spec=CommandBus)
        self.query_bus = MagicMock(spec=QueryBus)
        self.app.dependency_overrides[routes_router_module.get_authenticated_command_bus] = lambda: (
            self.command_bus
        )
        self.app.dependency_overrides[routes_router_module.get_authenticated_query_bus] = lambda: self.query_bus
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_routes_returns_paginated_route_responses_without_total(self) -> None:
        self.query_bus.dispatch.return_value = PageResult(
            items=(self._route(route_id=21),),
            total=None,
            limit=1,
            offset=2,
        )

        response = self.client.get("/routes/?limit=1&offset=2")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["total"])
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["limit"], 1)
        self.assertEqual(response.json()["offset"], 2)
        self.assertEqual(response.json()["items"][0]["route_id"], 21)
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_ROUTES,
            query=ViewAllRoutesQuery(
                page=PageQuery(limit=1, offset=2, include_total=False),
            ),
        )

    def test_list_routes_includes_total_when_requested(self) -> None:
        self.query_bus.dispatch.return_value = PageResult(
            items=(self._route(route_id=22),),
            total=12,
            limit=1,
            offset=2,
        )

        response = self.client.get("/routes/?limit=1&offset=2&include_total=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 12)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["limit"], 1)
        self.assertEqual(response.json()["offset"], 2)
        self.assertEqual(response.json()["items"][0]["route_id"], 22)
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_ROUTES,
            query=ViewAllRoutesQuery(
                page=PageQuery(limit=1, offset=2, include_total=True),
            ),
        )

    def test_list_routes_preserves_unpaginated_limit(self) -> None:
        self.query_bus.dispatch.return_value = PageResult(
            items=(self._route(route_id=23),),
            total=None,
            limit=None,
            offset=0,
        )

        response = self.client.get("/routes/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["limit"])
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["items"][0]["route_id"], 23)
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_ROUTES,
            query=ViewAllRoutesQuery(
                page=PageQuery(limit=50, offset=0, include_total=False),
            ),
        )

    def test_list_routes_returns_forbidden_for_permission_error(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_VIEW_ALL")

        response = self.client.get("/routes/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_VIEW_ALL")
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_ROUTES,
            query=ViewAllRoutesQuery(
                page=PageQuery(limit=50, offset=0, include_total=False),
            ),
        )

    def test_list_routes_rejects_invalid_pagination_params(self) -> None:
        response = self.client.get("/routes/?limit=0&offset=-1")

        self.assertEqual(response.status_code, 422)
        self.query_bus.dispatch.assert_not_called()

    def test_list_routes_returns_bad_request_for_pagination_validation_error(self) -> None:
        self.query_bus.dispatch.side_effect = ValidationError("Offset cannot be used without a limit.")

        response = self.client.get("/routes/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Offset cannot be used without a limit.")
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_ROUTES,
            query=ViewAllRoutesQuery(
                page=PageQuery(limit=50, offset=0, include_total=False),
            ),
        )

    def test_create_route_returns_created_route(self) -> None:
        route = self._route(route_id=31)
        self.command_bus.dispatch.return_value = route

        response = self.client.post(
            "/routes/",
            json={"locations": ["SYD", "MEL"], "departure_time": None},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["route_id"], 31)
        self.command_bus.dispatch.assert_called_once_with(
            key=CREATE_ROUTE,
            command=CreateRouteCommand(locations=("SYD", "MEL")),
        )

    def test_create_route_returns_bad_request_for_invalid_route(self) -> None:
        self.command_bus.dispatch.side_effect = DomainValidationError("Invalid location code: BAD.")

        response = self.client.post(
            "/routes/",
            json={"locations": ["BAD", "MEL"], "departure_time": None},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid location code: BAD.")
        self.command_bus.dispatch.assert_called_once_with(
            key=CREATE_ROUTE,
            command=CreateRouteCommand(locations=("BAD", "MEL")),
        )

    def test_create_route_returns_forbidden_for_permission_error(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_CREATE")

        response = self.client.post(
            "/routes/",
            json={"locations": ["SYD", "MEL"], "departure_time": None},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_CREATE")
        self.command_bus.dispatch.assert_called_once_with(
            key=CREATE_ROUTE,
            command=CreateRouteCommand(locations=("SYD", "MEL")),
        )

    def test_list_in_progress_routes_returns_position_responses(self) -> None:
        route = self._route(route_id=41)
        position = RoutePosition(kind=RoutePositionKind.AT_STOP, stop_city=LocationCode("SYD"))
        self.query_bus.dispatch.return_value = [(route, position)]

        with patch.object(routes_router_module, "datetime") as datetime_mock:
            datetime_mock.now.return_value = NOW
            response = self.client.get("/routes/in-progress")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["route"]["route_id"], 41)
        self.assertEqual(response.json()[0]["position_kind"], "AT_STOP")
        self.assertEqual(response.json()[0]["current_location"], "SYD")
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ROUTES_IN_PROGRESS,
            query=ViewRoutesInProgressQuery(now=NOW),
        )

    def test_list_in_progress_routes_returns_forbidden_for_permission_error(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError(
            "Missing permission: ROUTE_VIEW_IN_PROGRESS"
        )

        with patch.object(routes_router_module, "datetime") as datetime_mock:
            datetime_mock.now.return_value = NOW
            response = self.client.get("/routes/in-progress")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_VIEW_IN_PROGRESS")
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ROUTES_IN_PROGRESS,
            query=ViewRoutesInProgressQuery(now=NOW),
        )

    def test_get_route_returns_route_response(self) -> None:
        self.query_bus.dispatch.return_value = self._route(route_id=51)

        response = self.client.get("/routes/51")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["route_id"], 51)
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ROUTE,
            query=ViewRouteQuery(route_id=51),
        )

    def test_get_route_returns_not_found_for_missing_route(self) -> None:
        self.query_bus.dispatch.side_effect = NotFoundError("Route with ID 51 not found")

        response = self.client.get("/routes/51")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Route with ID 51 not found")
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ROUTE,
            query=ViewRouteQuery(route_id=51),
        )

    def test_get_route_returns_forbidden_for_permission_error(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_VIEW")

        response = self.client.get("/routes/51")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_VIEW")
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ROUTE,
            query=ViewRouteQuery(route_id=51),
        )

    def test_delete_route_removes_route(self) -> None:
        response = self.client.delete("/routes/61")

        self.assertEqual(response.status_code, 204)
        self.command_bus.dispatch.assert_called_once_with(
            key=REMOVE_ROUTE,
            command=RemoveRouteCommand(route_id=61),
        )

    def test_delete_route_returns_not_found_for_missing_route(self) -> None:
        self.command_bus.dispatch.side_effect = NotFoundError("Route with ID 61 not found")

        response = self.client.delete("/routes/61")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Route with ID 61 not found")
        self.command_bus.dispatch.assert_called_once_with(
            key=REMOVE_ROUTE,
            command=RemoveRouteCommand(route_id=61),
        )

    def test_delete_route_returns_forbidden_for_permission_error(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_REMOVE")

        response = self.client.delete("/routes/61")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_REMOVE")
        self.command_bus.dispatch.assert_called_once_with(
            key=REMOVE_ROUTE,
            command=RemoveRouteCommand(route_id=61),
        )

    def test_assign_packages_to_route_returns_nested_assignment_response(self) -> None:
        route = self._route(route_id=71)
        self.command_bus.dispatch.return_value = AssignPackagesToRouteResult(
            successes=[
                PackageAssignmentSuccess(
                    package_id=1,
                    route_id=71,
                    eta_text="2026-05-24 10:00",
                    route=route,
                )
            ],
            errors=[PackageAssignmentError(package_id=2, message="Package 2 not found.")],
        )
        response = self.client.patch("/routes/71/packages", json={"package_ids": [1, 2]})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["successes"][0]["package_id"], 1)
        self.assertEqual(payload["successes"][0]["route_id"], 71)
        self.assertEqual(payload["successes"][0]["route"]["route_id"], 71)
        self.assertEqual(payload["successes"][0]["route"]["locations"], ["SYD", "MEL"])
        self.assertEqual(payload["successes"][0]["route"]["package_ids"], [])
        self.assertEqual(payload["errors"][0]["message"], "Package 2 not found.")
        self.command_bus.dispatch.assert_called_once_with(
            key=ASSIGN_PACKAGES_TO_ROUTE,
            command=AssignPackagesToRouteCommand(route_id=71, package_ids=(1, 2)),
        )

    def test_assign_packages_to_route_returns_only_errors(self) -> None:
        self.command_bus.dispatch.return_value = AssignPackagesToRouteResult(
            successes=[],
            errors=[PackageAssignmentError(package_id=2, message="Package 2 not found.")],
        )

        response = self.client.patch("/routes/71/packages", json={"package_ids": [2]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["successes"], [])
        self.assertEqual(response.json()["errors"][0]["message"], "Package 2 not found.")
        self.command_bus.dispatch.assert_called_once_with(
            key=ASSIGN_PACKAGES_TO_ROUTE,
            command=AssignPackagesToRouteCommand(route_id=71, package_ids=(2,)),
        )

    def test_assign_packages_to_route_returns_not_found_for_missing_route(self) -> None:
        self.command_bus.dispatch.side_effect = NotFoundError("Route with ID 71 not found.")

        response = self.client.patch("/routes/71/packages", json={"package_ids": [1]})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Route with ID 71 not found.")
        self.command_bus.dispatch.assert_called_once_with(
            key=ASSIGN_PACKAGES_TO_ROUTE,
            command=AssignPackagesToRouteCommand(route_id=71, package_ids=(1,)),
        )

    def test_assign_packages_to_route_returns_forbidden_for_permission_error(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_ASSIGN_PACKAGE")

        response = self.client.patch("/routes/71/packages", json={"package_ids": [1]})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_ASSIGN_PACKAGE")
        self.command_bus.dispatch.assert_called_once_with(
            key=ASSIGN_PACKAGES_TO_ROUTE,
            command=AssignPackagesToRouteCommand(route_id=71, package_ids=(1,)),
        )

    def test_assign_packages_to_route_rejects_empty_package_list(self) -> None:
        response = self.client.patch("/routes/71/packages", json={"package_ids": []})

        self.assertEqual(response.status_code, 422)
        self.command_bus.dispatch.assert_not_called()

    def test_assign_truck_to_route_returns_assignment_response(self) -> None:
        route = self._route(route_id=81)
        self.command_bus.dispatch.return_value = AssignTruckToRouteResult(
            route_id=81,
            truck_id=7,
            route=route,
        )

        response = self.client.patch("/routes/81/truck", json={"truck_id": 7})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"route_id": 81, "truck_id": 7})
        self._assert_assign_truck_dispatched()

    def test_assign_truck_to_route_returns_conflict_for_unsuitable_truck(self) -> None:
        self.command_bus.dispatch.side_effect = ConflictError("Truck 7 is not suitable for route 81.")

        response = self.client.patch("/routes/81/truck", json={"truck_id": 7})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Truck 7 is not suitable for route 81.")
        self._assert_assign_truck_dispatched()

    def test_assign_truck_to_route_returns_not_found_for_missing_truck_or_route(self) -> None:
        self.command_bus.dispatch.side_effect = NotFoundError("Truck with ID 7 not found")

        response = self.client.patch("/routes/81/truck", json={"truck_id": 7})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Truck with ID 7 not found")
        self._assert_assign_truck_dispatched()

    def test_assign_truck_to_route_returns_generic_error_for_database_failure(self) -> None:
        self.command_bus.dispatch.side_effect = DatabaseError.write_failed(Exception("boom"))

        response = self.client.patch("/routes/81/truck", json={"truck_id": 7})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Database operation failed.")
        self._assert_assign_truck_dispatched()

    def test_assign_truck_to_route_returns_forbidden_for_permission_error(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_ASSIGN_TRUCK")

        response = self.client.patch("/routes/81/truck", json={"truck_id": 7})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_ASSIGN_TRUCK")
        self._assert_assign_truck_dispatched()

    def test_find_suitable_trucks_for_route_returns_truck_responses(self) -> None:
        truck = Truck(vehicle_id=7, name="Scania", capacity=42000, max_range=8000)
        truck.current_location = LocationCode("SYD")
        truck.status = TruckStatus.FREE
        self.query_bus.dispatch.return_value = [truck]

        response = self.client.get("/routes/91/suitable-trucks")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["vehicle_id"], 7)
        self.assertEqual(response.json()[0]["name"], "Scania")
        self.assertEqual(response.json()[0]["current_location"], "SYD")
        self.query_bus.dispatch.assert_called_once_with(
            key=FIND_SUITABLE_TRUCKS_FOR_ROUTE,
            query=FindSuitableTrucksForRouteQuery(route_id=91),
        )

    def test_find_suitable_trucks_for_route_returns_not_found_for_missing_route(self) -> None:
        self.query_bus.dispatch.side_effect = NotFoundError("Route with ID 91 not found")

        response = self.client.get("/routes/91/suitable-trucks")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Route with ID 91 not found")
        self.query_bus.dispatch.assert_called_once_with(
            key=FIND_SUITABLE_TRUCKS_FOR_ROUTE,
            query=FindSuitableTrucksForRouteQuery(route_id=91),
        )

    def test_find_suitable_trucks_for_route_returns_generic_error_for_database_failure(self) -> None:
        self.query_bus.dispatch.side_effect = DatabaseError.read_failed(Exception("boom"))

        response = self.client.get("/routes/91/suitable-trucks")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Database operation failed.")
        self.query_bus.dispatch.assert_called_once_with(
            key=FIND_SUITABLE_TRUCKS_FOR_ROUTE,
            query=FindSuitableTrucksForRouteQuery(route_id=91),
        )

    def test_find_suitable_trucks_for_route_returns_forbidden_for_permission_error(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_FIND_TRUCK_FOR")

        response = self.client.get("/routes/91/suitable-trucks")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_FIND_TRUCK_FOR")
        self.query_bus.dispatch.assert_called_once_with(
            key=FIND_SUITABLE_TRUCKS_FOR_ROUTE,
            query=FindSuitableTrucksForRouteQuery(route_id=91),
        )

    def _route(self, *, route_id: int) -> DeliveryRoute:
        return DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=route_id)

    def _assert_assign_truck_dispatched(self) -> None:
        """Assert assignment dispatch while allowing its runtime timestamp."""
        self.command_bus.dispatch.assert_called_once()
        self.assertIs(self.command_bus.dispatch.call_args.kwargs["key"], ASSIGN_TRUCK_TO_ROUTE)
        command = self.command_bus.dispatch.call_args.kwargs["command"]
        self.assertIsInstance(command, AssignTruckToRouteCommand)
        assert isinstance(command, AssignTruckToRouteCommand)
        self.assertEqual(command.truck_id, 7)
        self.assertEqual(command.route_id, 81)
        self.assertIsNone(command.now.tzinfo)
