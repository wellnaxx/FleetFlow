import unittest
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driving.http.routers.api import customers_router as customers_router_module
from src.adapters.driving.http.routers.api.customers_router import customers_router
from src.application.exceptions.application_errors import ValidationError
from src.application.use_cases.pagination import PageQuery, PageResult
from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo


class CustomersRouterShould(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(customers_router)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_customers_returns_customer_responses(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = PageResult(
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
        self.app.dependency_overrides[customers_router_module.get_view_all_customers_use_case] = lambda: (
            use_case
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
        use_case.execute.assert_called_once_with(PageQuery(limit=50, offset=0, include_total=False))

    def test_list_customers_passes_pagination_params(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = PageResult(
            items=(self._customer(customer_id=3, name="Carol Smith"),),
            total=None,
            limit=1,
            offset=2,
        )
        self.app.dependency_overrides[customers_router_module.get_view_all_customers_use_case] = lambda: (
            use_case
        )

        response = self.client.get("/customers/?limit=1&offset=2")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["total"])
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["limit"], 1)
        self.assertEqual(response.json()["offset"], 2)
        use_case.execute.assert_called_once_with(PageQuery(limit=1, offset=2, include_total=False))

    def test_list_customers_includes_total_when_requested(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = PageResult(
            items=(self._customer(customer_id=3, name="Carol Smith"),),
            total=12,
            limit=1,
            offset=2,
        )
        self.app.dependency_overrides[customers_router_module.get_view_all_customers_use_case] = lambda: (
            use_case
        )

        response = self.client.get("/customers/?limit=1&offset=2&include_total=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 12)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["limit"], 1)
        self.assertEqual(response.json()["offset"], 2)
        use_case.execute.assert_called_once_with(PageQuery(limit=1, offset=2, include_total=True))

    def test_list_customers_returns_empty_list(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = PageResult(items=(), total=None, limit=50, offset=0)
        self.app.dependency_overrides[customers_router_module.get_view_all_customers_use_case] = lambda: (
            use_case
        )

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"items": [], "total": None, "count": 0, "limit": 50, "offset": 0},
        )
        use_case.execute.assert_called_once_with(PageQuery(limit=50, offset=0, include_total=False))

    def test_list_customers_rejects_invalid_pagination_params(self) -> None:
        use_case = MagicMock()
        self.app.dependency_overrides[customers_router_module.get_view_all_customers_use_case] = lambda: (
            use_case
        )

        response = self.client.get("/customers/?limit=0&offset=-1")

        self.assertEqual(response.status_code, 422)
        use_case.execute.assert_not_called()

    def test_list_customers_returns_bad_request_for_pagination_validation_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = ValidationError("Offset cannot be used without a limit.")
        self.app.dependency_overrides[customers_router_module.get_view_all_customers_use_case] = lambda: (
            use_case
        )

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Offset cannot be used without a limit.")

    def test_list_customers_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: CUSTOMER_VIEW")
        self.app.dependency_overrides[customers_router_module.get_view_all_customers_use_case] = lambda: (
            use_case
        )

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: CUSTOMER_VIEW")
        use_case.execute.assert_called_once_with(PageQuery(limit=50, offset=0, include_total=False))

    def _customer(
        self,
        *,
        customer_id: int,
        name: str,
        email: str = "",
        phone_number: str = "",
    ) -> Customer:
        return Customer(
            contact=ContactInfo(name=name, email=email, phone_number=phone_number),
            customer_id=customer_id,
        )
