import unittest
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driving.http.routers.api import customers_router as customers_router_module
from src.adapters.driving.http.routers.api.customers_router import customers_router
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
        use_case.execute.return_value = [
            self._customer(
                customer_id=1,
                name="Alice Smith",
                email="alice@example.com",
                phone_number="0412345678",
            ),
            self._customer(customer_id=2, name="Bob Jones"),
        ]
        self.app.dependency_overrides[customers_router_module.get_view_all_customers_use_case] = (
            lambda: use_case
        )

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
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
        )
        use_case.execute.assert_called_once_with()

    def test_list_customers_returns_empty_list(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = []
        self.app.dependency_overrides[customers_router_module.get_view_all_customers_use_case] = (
            lambda: use_case
        )

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        use_case.execute.assert_called_once_with()

    def test_list_customers_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: CUSTOMER_VIEW")
        self.app.dependency_overrides[customers_router_module.get_view_all_customers_use_case] = (
            lambda: use_case
        )

        response = self.client.get("/customers/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: CUSTOMER_VIEW")
        use_case.execute.assert_called_once_with()

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
