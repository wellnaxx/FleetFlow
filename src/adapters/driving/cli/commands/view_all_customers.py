"""CLI command for listing customers."""

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase


class ViewAllCustomers(EventDrainingCommand[ViewAllCustomersUseCase]):
    """Render all customers."""

    def execute(self) -> str:
        """Return customer listing text.

        Returns:
            CLI listing of customers, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks customer view permission.
        """
        customers = self._run_and_drain(self._use_case, self._use_case.execute).items
        return (
            "\n\n".join(f"Customer {c.customer_id}: {c.name} ({c.email}, {c.phone_number})" for c in customers)
            if customers
            else "No customers."
        )
