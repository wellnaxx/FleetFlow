"""Tests for the customer-listing CLI command."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.view_all_customers import ViewAllCustomers
from src.application.queries.customers.view_all_customers import (
    VIEW_ALL_CUSTOMERS,
    ViewAllCustomersQuery,
)
from src.application.use_cases.pagination import PageResult
from src.ports.input.query_bus import QueryBus


class ViewAllCustomersShould(unittest.TestCase):
    """Verify customer query dispatch and CLI rendering."""

    def make_cmd(
        self,
        params: tuple[str, ...] = (),
    ) -> tuple[ViewAllCustomers, MagicMock]:
        """Build the command with an isolated query bus."""
        query_bus = MagicMock(spec=QueryBus)
        return ViewAllCustomers(params, query_bus), query_bus

    def test_no_customers_returns_friendly_message(self) -> None:
        cmd, query_bus = self.make_cmd()
        query_bus.dispatch.return_value = PageResult(items=(), total=None, limit=None, offset=0)

        result = cmd.execute()

        self.assertEqual(result, "No customers.")
        self._assert_default_query(query_bus)

    def test_formats_multiple_customers_separated_by_blank_lines(self) -> None:
        cmd, query_bus = self.make_cmd()
        first = SimpleNamespace(
            customer_id=1,
            name="Alice",
            email="alice@test.com",
            phone_number="0411111111",
        )
        second = SimpleNamespace(
            customer_id=2,
            name="Bob",
            email="",
            phone_number="",
        )
        query_bus.dispatch.return_value = PageResult(
            items=(first, second),
            total=None,
            limit=None,
            offset=0,
        )

        result = cmd.execute()

        self.assertEqual(
            result,
            "Customer 1: Alice (alice@test.com, 0411111111)\n\nCustomer 2: Bob (, )",
        )
        self._assert_default_query(query_bus)

    def test_propagates_permission_error(self) -> None:
        cmd, query_bus = self.make_cmd()
        expected = PermissionError("Missing permission: CUSTOMER_VIEW")
        query_bus.dispatch.side_effect = expected

        with self.assertRaises(PermissionError) as raised:
            cmd.execute()

        self.assertIs(raised.exception, expected)
        self._assert_default_query(query_bus)

    def test_propagates_repository_error(self) -> None:
        cmd, query_bus = self.make_cmd()
        expected = RuntimeError("db down")
        query_bus.dispatch.side_effect = expected

        with self.assertRaises(RuntimeError) as raised:
            cmd.execute()

        self.assertIs(raised.exception, expected)
        self._assert_default_query(query_bus)

    def test_rejects_arguments_before_dispatch(self) -> None:
        cmd, query_bus = self.make_cmd(("unexpected",))

        with self.assertRaisesRegex(ValueError, "does not accept arguments"):
            cmd.execute()

        query_bus.dispatch.assert_not_called()

    def test_has_no_mutation_flags(self) -> None:
        self.assertFalse(getattr(ViewAllCustomers, "mutates_state", False))
        self.assertFalse(getattr(ViewAllCustomers, "mutates_session", False))

    def _assert_default_query(self, query_bus: MagicMock) -> None:
        """Assert dispatch of the default unpaginated customer query."""
        query_bus.dispatch.assert_called_once()
        self.assertIs(query_bus.dispatch.call_args.kwargs["key"], VIEW_ALL_CUSTOMERS)
        query = query_bus.dispatch.call_args.kwargs["query"]
        self.assertIsInstance(query, ViewAllCustomersQuery)
        self.assertIsNone(query.page.limit)
        self.assertEqual(query.page.offset, 0)
        self.assertFalse(query.page.include_total)


if __name__ == "__main__":
    unittest.main()
