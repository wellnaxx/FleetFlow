from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.services.authorization_service import requires
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.domain.enums.auth import Permission


class ViewAllCustomers(BaseCommand[ViewAllCustomersUseCase]):
    @requires(Permission.CUSTOMER_VIEW)
    def execute(self) -> str:
        customers = self._use_case.execute()
        return (
            "\n\n".join(f"Customer {c.customer_id}: {c.name} ({c.email}, {c.phone_number})" for c in customers)
            if customers
            else "No customers."
        )

