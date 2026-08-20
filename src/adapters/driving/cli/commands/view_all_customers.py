"""CLI command for listing customers."""

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.application.queries.customers.view_all_customers import (
    VIEW_ALL_CUSTOMERS,
    ViewAllCustomersQuery,
)


class ViewAllCustomers(QueryBusCommand):
    """Render all customers."""

    def execute(self) -> str:
        """Return customer listing text.

        Returns:
            CLI listing of customers, or an empty-state message.

        Raises:
            ValueError: If command arguments are supplied.
            PermissionError: If the caller lacks customer view permission.
            DatabaseError: If customer retrieval fails.
        """
        if self.params:
            raise ValueError("viewallcustomers does not accept arguments.")

        customers = self.query_bus.dispatch(
            key=VIEW_ALL_CUSTOMERS,
            query=ViewAllCustomersQuery(),
        ).items
        return (
            "\n\n".join(f"Customer {c.customer_id}: {c.name} ({c.email}, {c.phone_number})" for c in customers)
            if customers
            else "No customers."
        )
