import unittest
from unittest.mock import ANY, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.routers.api import routes_router as routes_router_module
from src.adapters.driving.http.routers.api.routes_router import routes_router
from src.application.exceptions.application_errors import ConflictError, NotFoundError, ValidationError
from src.application.results.assign_packages_to_route_result import (
    AssignPackagesToRouteResult,
    PackageAssignmentError,
    PackageAssignmentSuccess,
)
from src.application.use_cases.pagination import PageQuery, PageResult
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteResult
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode


class RoutesRouterShould(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(routes_router)
        register_exception_handlers(self.app)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_routes_returns_paginated_route_responses_without_total(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = PageResult(
            items=(self._route(route_id=21),),
            total=None,
            limit=1,
            offset=2,
        )
        self.app.dependency_overrides[routes_router_module.get_view_all_routes_use_case] = lambda: use_case

        response = self.client.get("/routes/?limit=1&offset=2")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["total"])
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["limit"], 1)
        self.assertEqual(response.json()["offset"], 2)
        self.assertEqual(response.json()["items"][0]["route_id"], 21)
        use_case.execute.assert_called_once_with(PageQuery(limit=1, offset=2, include_total=False))

    def test_list_routes_includes_total_when_requested(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = PageResult(
            items=(self._route(route_id=22),),
            total=12,
            limit=1,
            offset=2,
        )
        self.app.dependency_overrides[routes_router_module.get_view_all_routes_use_case] = lambda: use_case

        response = self.client.get("/routes/?limit=1&offset=2&include_total=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 12)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["limit"], 1)
        self.assertEqual(response.json()["offset"], 2)
        self.assertEqual(response.json()["items"][0]["route_id"], 22)
        use_case.execute.assert_called_once_with(PageQuery(limit=1, offset=2, include_total=True))

    def test_list_routes_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_VIEW_ALL")
        self.app.dependency_overrides[routes_router_module.get_view_all_routes_use_case] = lambda: use_case

        response = self.client.get("/routes/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_VIEW_ALL")
        use_case.execute.assert_called_once_with(PageQuery(limit=50, offset=0, include_total=False))

    def test_list_routes_rejects_invalid_pagination_params(self) -> None:
        use_case = MagicMock()
        self.app.dependency_overrides[routes_router_module.get_view_all_routes_use_case] = lambda: use_case

        response = self.client.get("/routes/?limit=0&offset=-1")

        self.assertEqual(response.status_code, 422)
        use_case.execute.assert_not_called()

    def test_list_routes_returns_bad_request_for_pagination_validation_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = ValidationError("Offset cannot be used without a limit.")
        self.app.dependency_overrides[routes_router_module.get_view_all_routes_use_case] = lambda: use_case

        response = self.client.get("/routes/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Offset cannot be used without a limit.")

    def test_create_route_returns_created_route(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = self._route(route_id=31)
        self.app.dependency_overrides[routes_router_module.get_create_route_use_case] = lambda: use_case

        response = self.client.post(
            "/routes/",
            json={"locations": ["SYD", "MEL"], "departure_time": None},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["route_id"], 31)
        use_case.execute.assert_called_once_with(locations=["SYD", "MEL"], departure_time=None)

    def test_create_route_returns_bad_request_for_invalid_route(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = DomainValidationError("Invalid location code: BAD.")
        self.app.dependency_overrides[routes_router_module.get_create_route_use_case] = lambda: use_case

        response = self.client.post(
            "/routes/",
            json={"locations": ["BAD", "MEL"], "departure_time": None},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid location code: BAD.")

    def test_create_route_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_CREATE")
        self.app.dependency_overrides[routes_router_module.get_create_route_use_case] = lambda: use_case

        response = self.client.post(
            "/routes/",
            json={"locations": ["SYD", "MEL"], "departure_time": None},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_CREATE")

    def test_list_in_progress_routes_returns_position_responses(self) -> None:
        use_case = MagicMock()
        route = self._route(route_id=41)
        position = routes_router_module.RoutePosition(kind="AT_STOP", stop_city=LocationCode("SYD"))
        use_case.execute.return_value = [(route, position)]
        self.app.dependency_overrides[routes_router_module.get_view_routes_in_progress_use_case] = lambda: (
            use_case
        )

        response = self.client.get("/routes/in-progress")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["route"]["route_id"], 41)
        self.assertEqual(response.json()[0]["position_kind"], "AT_STOP")
        self.assertEqual(response.json()[0]["current_location"], "SYD")
        use_case.execute.assert_called_once_with(now=ANY)

    def test_list_in_progress_routes_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_VIEW_IN_PROGRESS")
        self.app.dependency_overrides[routes_router_module.get_view_routes_in_progress_use_case] = lambda: (
            use_case
        )

        response = self.client.get("/routes/in-progress")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_VIEW_IN_PROGRESS")

    def test_get_route_returns_route_response(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = self._route(route_id=51)
        self.app.dependency_overrides[routes_router_module.get_view_route_use_case] = lambda: use_case

        response = self.client.get("/routes/51")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["route_id"], 51)
        use_case.execute.assert_called_once_with(route_id=51)

    def test_get_route_returns_not_found_for_missing_route(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = NotFoundError("Route with ID 51 not found")
        self.app.dependency_overrides[routes_router_module.get_view_route_use_case] = lambda: use_case

        response = self.client.get("/routes/51")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Route with ID 51 not found")

    def test_get_route_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_VIEW")
        self.app.dependency_overrides[routes_router_module.get_view_route_use_case] = lambda: use_case

        response = self.client.get("/routes/51")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_VIEW")

    def test_delete_route_removes_route(self) -> None:
        use_case = MagicMock()
        self.app.dependency_overrides[routes_router_module.get_remove_route_use_case] = lambda: use_case

        response = self.client.delete("/routes/61")

        self.assertEqual(response.status_code, 204)
        use_case.execute.assert_called_once_with(route_id=61)

    def test_delete_route_returns_not_found_for_missing_route(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = NotFoundError("Route with ID 61 not found")
        self.app.dependency_overrides[routes_router_module.get_remove_route_use_case] = lambda: use_case

        response = self.client.delete("/routes/61")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Route with ID 61 not found")

    def test_delete_route_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_REMOVE")
        self.app.dependency_overrides[routes_router_module.get_remove_route_use_case] = lambda: use_case

        response = self.client.delete("/routes/61")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_REMOVE")

    def test_assign_packages_to_route_returns_nested_assignment_response(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = AssignPackagesToRouteResult(
            successes=[PackageAssignmentSuccess(package_id=1, route_id=71, eta_text="2026-05-24 10:00")],
            errors=[PackageAssignmentError(package_id=2, message="Package 2 not found.")],
        )
        self.app.dependency_overrides[routes_router_module.get_assign_packages_to_route_use_case] = lambda: (
            use_case
        )

        response = self.client.patch("/routes/71/packages", json={"package_ids": [1, 2]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["successes"][0]["package_id"], 1)
        self.assertEqual(response.json()["errors"][0]["message"], "Package 2 not found.")
        use_case.execute.assert_called_once_with(route_id=71, package_ids=[1, 2])

    def test_assign_packages_to_route_returns_not_found_for_missing_route(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = NotFoundError("Route with ID 71 not found.")
        self.app.dependency_overrides[routes_router_module.get_assign_packages_to_route_use_case] = lambda: (
            use_case
        )

        response = self.client.patch("/routes/71/packages", json={"package_ids": [1]})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Route with ID 71 not found.")

    def test_assign_packages_to_route_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_ASSIGN_PACKAGE")
        self.app.dependency_overrides[routes_router_module.get_assign_packages_to_route_use_case] = lambda: (
            use_case
        )

        response = self.client.patch("/routes/71/packages", json={"package_ids": [1]})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_ASSIGN_PACKAGE")

    def test_assign_packages_to_route_rejects_empty_package_list(self) -> None:
        use_case = MagicMock()
        self.app.dependency_overrides[routes_router_module.get_assign_packages_to_route_use_case] = lambda: (
            use_case
        )

        response = self.client.patch("/routes/71/packages", json={"package_ids": []})

        self.assertEqual(response.status_code, 422)
        use_case.execute.assert_not_called()

    def test_assign_truck_to_route_returns_assignment_response(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = AssignTruckToRouteResult(route_id=81, truck_id=7)
        self.app.dependency_overrides[routes_router_module.get_assign_truck_to_route_use_case] = lambda: (
            use_case
        )

        response = self.client.patch("/routes/81/truck", json={"truck_id": 7})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"route_id": 81, "truck_id": 7})
        use_case.execute.assert_called_once_with(truck_id=7, route_id=81, now=ANY)

    def test_assign_truck_to_route_returns_conflict_for_unsuitable_truck(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = ConflictError("Truck 7 is not suitable for route 81.")
        self.app.dependency_overrides[routes_router_module.get_assign_truck_to_route_use_case] = lambda: (
            use_case
        )

        response = self.client.patch("/routes/81/truck", json={"truck_id": 7})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Truck 7 is not suitable for route 81.")

    def test_assign_truck_to_route_returns_not_found_for_missing_truck_or_route(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = NotFoundError("Truck with ID 7 not found")
        self.app.dependency_overrides[routes_router_module.get_assign_truck_to_route_use_case] = lambda: (
            use_case
        )

        response = self.client.patch("/routes/81/truck", json={"truck_id": 7})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Truck with ID 7 not found")

    def test_assign_truck_to_route_returns_generic_error_for_database_failure(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = DatabaseError.write_failed(Exception("boom"))
        self.app.dependency_overrides[routes_router_module.get_assign_truck_to_route_use_case] = lambda: (
            use_case
        )

        response = self.client.patch("/routes/81/truck", json={"truck_id": 7})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Database operation failed.")

    def test_assign_truck_to_route_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_ASSIGN_TRUCK")
        self.app.dependency_overrides[routes_router_module.get_assign_truck_to_route_use_case] = lambda: (
            use_case
        )

        response = self.client.patch("/routes/81/truck", json={"truck_id": 7})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_ASSIGN_TRUCK")

    def test_find_suitable_trucks_for_route_returns_truck_responses(self) -> None:
        use_case = MagicMock()
        truck = Truck(vehicle_id=7, name="Scania", capacity=42000, max_range=8000)
        truck.current_location = LocationCode("SYD")
        truck.status = TruckStatus.FREE
        use_case.execute.return_value = [truck]
        self.app.dependency_overrides[routes_router_module.get_find_suitable_trucks_for_route_use_case] = (
            lambda: use_case
        )

        response = self.client.get("/routes/91/suitable-trucks")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["vehicle_id"], 7)
        self.assertEqual(response.json()[0]["name"], "Scania")
        self.assertEqual(response.json()[0]["current_location"], "SYD")
        use_case.execute.assert_called_once_with(route_id=91)

    def test_find_suitable_trucks_for_route_returns_not_found_for_missing_route(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = NotFoundError("Route with ID 91 not found")
        self.app.dependency_overrides[routes_router_module.get_find_suitable_trucks_for_route_use_case] = (
            lambda: use_case
        )

        response = self.client.get("/routes/91/suitable-trucks")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Route with ID 91 not found")

    def test_find_suitable_trucks_for_route_returns_generic_error_for_database_failure(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = DatabaseError.read_failed(Exception("boom"))
        self.app.dependency_overrides[routes_router_module.get_find_suitable_trucks_for_route_use_case] = (
            lambda: use_case
        )

        response = self.client.get("/routes/91/suitable-trucks")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Database operation failed.")

    def test_find_suitable_trucks_for_route_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_FIND_TRUCK_FOR")
        self.app.dependency_overrides[routes_router_module.get_find_suitable_trucks_for_route_use_case] = (
            lambda: use_case
        )

        response = self.client.get("/routes/91/suitable-trucks")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ROUTE_FIND_TRUCK_FOR")

    def _route(self, *, route_id: int) -> DeliveryRoute:
        return DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=route_id)
