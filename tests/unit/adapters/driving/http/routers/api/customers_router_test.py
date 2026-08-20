"""Tests for the customer HTTP router."""

import unittest
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.routers.api import customers_router as customers_router_module
from src.adapters.driving.http.routers.api.customers_router import customers_router
from src.application.exceptions.application_errors import ValidationError
from src.application.queries.customers.view_all_customers import (
    VIEW_ALL_CUSTOMERS,
    ViewAllCustomersQuery,
)
from src.application.use_cases.pagination import PageResult
from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo
from src.ports.input.query_bus import QueryBus


class CustomersRouterShould(unittest.TestCase):
    """Verify pagination mapping, response serialization, and failures."""

    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(customers_router)
        register_exception_handlers(self.app)
        self.query_bus = MagicMock(spec=QueryBus)
        self.app.dependency_overrides[customers_router_module.get_authenticated_query_bus] = lambda: (
            self.query_bus
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_customers_returns_customer_responses(self) -> None:
        self.query_bus.dispatch.return_value = PageResult(
            items=(
                self._customer(
                    customer_id=1,
                    name="Alice Smith",
                    email="alice@example.com",
                    phone_number="0412345678",
                ),
                self._customer(customer_id=2, name="Bob Jones"),
            ),
            total=None,
            limit=50,
            offset=0,
        )

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "items": [
                    {
                        "customer_id": 1,
                        "name": "Alice Smith",
                        "email": "alice@example.com",
                        "phone_number": "0412345678",
                    },
                    {
                        "customer_id": 2,
                        "name": "Bob Jones",
                        "email": "",
                        "phone_number": "",
                    },
                ],
                "total": None,
                "count": 2,
                "limit": 50,
                "offset": 0,
            },
        )
        self._assert_query(limit=50, offset=0, include_total=False)

    def test_list_customers_passes_pagination_and_total_selection(self) -> None:
        self.query_bus.dispatch.return_value = PageResult(
            items=(self._customer(customer_id=3, name="Carol Smith"),),
            total=12,
            limit=1,
            offset=2,
        )

        response = self.client.get("/customers/?limit=1&offset=2&include_total=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 12)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["limit"], 1)
        self.assertEqual(response.json()["offset"], 2)
        self._assert_query(limit=1, offset=2, include_total=True)

    def test_list_customers_preserves_unpaginated_result_metadata(self) -> None:
        self.query_bus.dispatch.return_value = PageResult(
            items=(self._customer(customer_id=4, name="Dana Smith"),),
            total=None,
            limit=None,
            offset=0,
        )

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["limit"])
        self.assertEqual(response.json()["count"], 1)
        self._assert_query(limit=50, offset=0, include_total=False)

    def test_list_customers_returns_empty_page(self) -> None:
        self.query_bus.dispatch.return_value = PageResult(items=(), total=None, limit=50, offset=0)

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"items": [], "total": None, "count": 0, "limit": 50, "offset": 0},
        )
        self._assert_query(limit=50, offset=0, include_total=False)

    def test_list_customers_rejects_invalid_http_pagination(self) -> None:
        response = self.client.get("/customers/?limit=0&offset=-1")

        self.assertEqual(response.status_code, 422)
        self.query_bus.dispatch.assert_not_called()

    def test_list_customers_returns_bad_request_for_query_validation_error(self) -> None:
        self.query_bus.dispatch.side_effect = ValidationError("Offset cannot be used without a limit.")

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Offset cannot be used without a limit.")
        self._assert_query(limit=50, offset=0, include_total=False)

    def test_list_customers_returns_forbidden_for_permission_error(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: CUSTOMER_VIEW")

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: CUSTOMER_VIEW")
        self._assert_query(limit=50, offset=0, include_total=False)

    def _assert_query(self, *, limit: int, offset: int, include_total: bool) -> None:
        """Assert dispatch of one customer query with expected pagination."""
        self.query_bus.dispatch.assert_called_once()
        self.assertIs(self.query_bus.dispatch.call_args.kwargs["key"], VIEW_ALL_CUSTOMERS)
        query = self.query_bus.dispatch.call_args.kwargs["query"]
        self.assertIsInstance(query, ViewAllCustomersQuery)
        self.assertEqual(query.page.limit, limit)
        self.assertEqual(query.page.offset, offset)
        self.assertIs(query.page.include_total, include_total)

    def _customer(
        self,
        *,
        customer_id: int,
        name: str,
        email: str = "",
        phone_number: str = "",
    ) -> Customer:
        """Build a customer entity for response serialization tests."""
        return Customer(
            contact=ContactInfo(name=name, email=email, phone_number=phone_number),
            customer_id=customer_id,
        )


if __name__ == "__main__":
    unittest.main()
