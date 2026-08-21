import unittest
from datetime import datetime
from unittest.mock import MagicMock, call

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.routers.api import packages_router as packages_router_module
from src.adapters.driving.http.routers.api.packages_router import packages_router
from src.application.commands.packages.create_package import CREATE_PACKAGE, CreatePackageCommand
from src.application.exceptions.application_errors import NotFoundError, ValidationError
from src.application.results.find_suitable_packages_for_route_result import SuitableRouteForPackage
from src.application.results.remove_package_result import RemovePackageResult
from src.application.use_cases.pagination import PageQuery, PageResult
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode
from src.ports.input.command_bus import CommandBus


class PackagesRouterShould(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(packages_router)
        register_exception_handlers(self.app)
        self.event_collector = MagicMock()
        self.app.dependency_overrides[packages_router_module.get_event_collector] = lambda: self.event_collector
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_create_package_returns_created_package(self) -> None:
        command_bus = MagicMock(spec=CommandBus)
        package = self._package()
        command_bus.dispatch.return_value = package
        self.app.dependency_overrides[packages_router_module.get_authenticated_command_bus] = lambda: (
            command_bus
        )

        response = self.client.post(
            "/packages",
            json={
                "start_location": "SYD",
                "end_location": "MEL",
                "weight": 12.5,
                "customer_name": "Alice",
                "customer_email": None,
                "customer_phone_number": None,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["package_id"], 1)
        self.assertIsNone(response.json()["route_id"])
        command_bus.dispatch.assert_called_once_with(
            key=CREATE_PACKAGE,
            command=CreatePackageCommand(
                start="SYD",
                end="MEL",
                weight=12.5,
                name="Alice",
                email="",
                phone="",
            ),
        )
        self.event_collector.drain.assert_not_called()

    def test_create_package_returns_bad_request_for_invalid_input(self) -> None:
        command_bus = MagicMock(spec=CommandBus)
        command_bus.dispatch.side_effect = DomainValidationError("Invalid start location: BAD")
        self.app.dependency_overrides[packages_router_module.get_authenticated_command_bus] = lambda: (
            command_bus
        )

        response = self.client.post(
            "/packages",
            json={
                "start_location": "BAD",
                "end_location": "MEL",
                "weight": 12.5,
                "customer_name": "Alice",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid start location: BAD")
        command_bus.dispatch.assert_called_once()
        self.event_collector.drain.assert_not_called()

    def test_create_package_returns_forbidden_for_permission_error(self) -> None:
        command_bus = MagicMock(spec=CommandBus)
        command_bus.dispatch.side_effect = PermissionError("Missing permission: PACKAGE_CREATE")
        self.app.dependency_overrides[packages_router_module.get_authenticated_command_bus] = lambda: (
            command_bus
        )

        response = self.client.post(
            "/packages",
            json={
                "start_location": "SYD",
                "end_location": "MEL",
                "weight": 12.5,
                "customer_name": "Alice",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: PACKAGE_CREATE")
        command_bus.dispatch.assert_called_once()
        self.event_collector.drain.assert_not_called()

    def test_list_packages_returns_paginated_package_responses(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = PageResult(
            items=(self._package(package_id=2, with_route=True),),
            total=12,
            limit=1,
            offset=2,
        )
        self.app.dependency_overrides[packages_router_module.get_view_all_packages_use_case] = lambda: use_case

        response = self.client.get("/packages?limit=1&offset=2&include_total=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["route_id"], 21)
        self.assertEqual(response.json()["total"], 12)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["limit"], 1)
        self.assertEqual(response.json()["offset"], 2)
        use_case.execute.assert_called_once_with(PageQuery(limit=1, offset=2, include_total=True))
        self.event_collector.drain.assert_called_once_with((use_case,))

    def test_list_packages_preserves_unpaginated_limit(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = PageResult(
            items=(self._package(package_id=2),),
            total=None,
            limit=None,
            offset=0,
        )
        self.app.dependency_overrides[packages_router_module.get_view_all_packages_use_case] = lambda: use_case

        response = self.client.get("/packages")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["limit"])
        self.assertEqual(response.json()["count"], 1)
        use_case.execute.assert_called_once_with(PageQuery(limit=50, offset=0, include_total=False))

    def test_list_packages_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: PACKAGE_VIEW_ALL")
        self.app.dependency_overrides[packages_router_module.get_view_all_packages_use_case] = lambda: use_case

        response = self.client.get("/packages")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: PACKAGE_VIEW_ALL")
        use_case.execute.assert_called_once_with(PageQuery(limit=50, offset=0, include_total=False))
        self.event_collector.drain.assert_called_once_with((use_case,))

    def test_list_unassigned_packages_returns_page_without_total_by_default(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = PageResult(
            items=(self._package(package_id=3),),
            total=None,
            limit=1,
            offset=2,
        )
        self.app.dependency_overrides[packages_router_module.get_view_unassigned_packages_use_case] = lambda: (
            use_case
        )

        response = self.client.get("/packages/unassigned?limit=1&offset=2")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["total"])
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["limit"], 1)
        self.assertEqual(response.json()["offset"], 2)
        use_case.execute.assert_called_once_with(PageQuery(limit=1, offset=2, include_total=False))
        self.event_collector.drain.assert_called_once_with((use_case,))

    def test_list_packages_rejects_invalid_pagination_params(self) -> None:
        use_case = MagicMock()
        self.app.dependency_overrides[packages_router_module.get_view_all_packages_use_case] = lambda: use_case

        response = self.client.get("/packages?limit=0&offset=-1")

        self.assertEqual(response.status_code, 422)
        use_case.execute.assert_not_called()

    def test_list_packages_returns_bad_request_for_pagination_validation_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = ValidationError("Offset cannot be used without a limit.")
        self.app.dependency_overrides[packages_router_module.get_view_all_packages_use_case] = lambda: use_case

        response = self.client.get("/packages")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Offset cannot be used without a limit.")

    def test_get_package_returns_package_response(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = self._package(package_id=4)
        self.app.dependency_overrides[packages_router_module.get_view_package_use_case] = lambda: use_case

        response = self.client.get("/packages/4")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["package_id"], 4)
        use_case.execute.assert_called_once_with(package_id=4)
        self.event_collector.drain.assert_called_once_with((use_case,))

    def test_get_package_returns_not_found_for_missing_package(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = NotFoundError("Package with ID 4 not found")
        self.app.dependency_overrides[packages_router_module.get_view_package_use_case] = lambda: use_case

        response = self.client.get("/packages/4")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Package with ID 4 not found")
        self.event_collector.drain.assert_called_once_with((use_case,))

    def test_find_suitable_routes_for_package_returns_route_options(self) -> None:
        use_case = MagicMock()
        eta = datetime(2026, 5, 24, 10, 30)
        use_case.execute.return_value = [
            SuitableRouteForPackage(
                route_id=21,
                start_location=LocationCode("SYD"),
                end_location=LocationCode("MEL"),
                eta=eta,
                capacity_left=125.5,
                end_city=LocationCode("MEL"),
            )
        ]
        self.app.dependency_overrides[packages_router_module.get_find_suitable_routes_for_package_use_case] = (
            lambda: use_case
        )

        response = self.client.get("/packages/4/suitable-routes")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["route_id"], 21)
        self.assertEqual(response.json()[0]["start_location"], "SYD")
        self.assertEqual(response.json()[0]["end_location"], "MEL")
        self.assertEqual(response.json()[0]["eta"], "2026-05-24T10:30:00")
        self.assertEqual(response.json()[0]["capacity_left"], 125.5)
        self.assertEqual(response.json()[0]["end_city"], "MEL")
        use_case.execute.assert_called_once_with(package_id=4)
        self.event_collector.drain.assert_called_once_with((use_case,))

    def test_find_suitable_routes_for_package_returns_not_found_for_missing_package(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = NotFoundError("Package with ID 4 not found.")
        self.app.dependency_overrides[packages_router_module.get_find_suitable_routes_for_package_use_case] = (
            lambda: use_case
        )

        response = self.client.get("/packages/4/suitable-routes")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Package with ID 4 not found.")
        self.event_collector.drain.assert_called_once_with((use_case,))

    def test_find_suitable_routes_for_package_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: PACKAGE_FIND_ROUTE_FOR")
        self.app.dependency_overrides[packages_router_module.get_find_suitable_routes_for_package_use_case] = (
            lambda: use_case
        )

        response = self.client.get("/packages/4/suitable-routes")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: PACKAGE_FIND_ROUTE_FOR")
        self.event_collector.drain.assert_called_once_with((use_case,))

    def test_delete_package_removes_package(self) -> None:
        use_case = MagicMock()
        event_collector = MagicMock()
        package = self._package(package_id=4, with_route=True)
        route = package.route
        self.assertIsNotNone(route)
        use_case.execute.return_value = RemovePackageResult(
            package=package,
            customer=package.customer,
            route=route,
        )
        self.app.dependency_overrides[packages_router_module.get_remove_package_use_case] = lambda: use_case
        self.app.dependency_overrides[packages_router_module.get_event_collector] = lambda: event_collector

        response = self.client.delete("/packages/4")

        self.assertEqual(response.status_code, 204)
        use_case.execute.assert_called_once_with(package_id=4)
        self.assertEqual(
            event_collector.drain.call_args_list,
            [call((use_case,)), call((package, package.customer, route))],
        )

    def test_delete_package_without_route_drains_package_and_customer_only(self) -> None:
        use_case = MagicMock()
        event_collector = MagicMock()
        package = self._package(package_id=4)
        use_case.execute.return_value = RemovePackageResult(
            package=package,
            customer=package.customer,
            route=None,
        )
        self.app.dependency_overrides[packages_router_module.get_remove_package_use_case] = lambda: use_case
        self.app.dependency_overrides[packages_router_module.get_event_collector] = lambda: event_collector

        response = self.client.delete("/packages/4")

        self.assertEqual(response.status_code, 204)
        use_case.execute.assert_called_once_with(package_id=4)
        self.assertEqual(
            event_collector.drain.call_args_list,
            [call((use_case,)), call((package, package.customer))],
        )

    def test_delete_package_returns_not_found_for_missing_package(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = NotFoundError("Package with ID 4 not found")
        self.app.dependency_overrides[packages_router_module.get_remove_package_use_case] = lambda: use_case

        response = self.client.delete("/packages/4")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Package with ID 4 not found")
        self.event_collector.drain.assert_called_once_with((use_case,))

    def test_delete_package_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: PACKAGE_REMOVE")
        self.app.dependency_overrides[packages_router_module.get_remove_package_use_case] = lambda: use_case

        response = self.client.delete("/packages/4")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: PACKAGE_REMOVE")
        self.event_collector.drain.assert_called_once_with((use_case,))

    def _package(self, *, package_id: int = 1, with_route: bool = False) -> DeliveryPackage:
        package = DeliveryPackage(
            start_location=LocationCode("SYD"),
            end_location=LocationCode("MEL"),
            weight=12.5,
            customer=Customer(
                customer_id=7,
                contact=ContactInfo(
                    name="Alice",
                    email="alice@example.com",
                    phone_number="0412345678",
                ),
            ),
            package_id=package_id,
        )
        if with_route:
            package.route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)
        return package
