import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.package_unit_of_work_repository import (
    PostgresPackageUnitOfWorkRepository,
)
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.item_status import ItemStatus
from src.domain.value_objects.contact_info import ContactInfo

MODULE = "src.adapters.driven.persistence.database.repositories.package_unit_of_work_repository"


class PostgresPackageUnitOfWorkRepository_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = MagicMock()
        self.repo = PostgresPackageUnitOfWorkRepository(self.cursor)
        self.customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))

    @patch(f"{MODULE}.execute_write_tx")
    def test_update_state_writes_package_state_with_shared_cursor(
        self,
        execute_write_tx_mock: MagicMock,
    ) -> None:
        execute_write_tx_mock.return_value = 1
        expected_arrival = datetime(2026, 5, 2, 12, 30)
        package = DeliveryPackage("SYD", "MEL", 12.5, self.customer, 11)
        package.status = ItemStatus.IN_PROGRESS
        package.current_location = "ADL"
        package.expected_arrival = expected_arrival
        package.route = SimpleNamespace(route_id=21)  # type: ignore[assignment]

        self.repo.update_state(package)

        execute_write_tx_mock.assert_called_once_with(
            self.cursor,
            QUERIES.packages.update_state,
            (ItemStatus.IN_PROGRESS.value, "ADL", expected_arrival, 21, 11),
        )

    @patch(f"{MODULE}.execute_write_tx")
    def test_update_state_raises_when_package_row_is_missing(
        self,
        execute_write_tx_mock: MagicMock,
    ) -> None:
        execute_write_tx_mock.return_value = 0
        package = DeliveryPackage("SYD", "MEL", 12.5, self.customer, 11)

        with self.assertRaises(ValueError) as ctx:
            self.repo.update_state(package)

        self.assertIn("Expected to update one package row for id 11, affected 0", str(ctx.exception))
