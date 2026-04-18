from collections.abc import Iterable

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.services.auth_service import AuthService
from src.application.services.authorization import requires
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.core.application_data import ApplicationData
from src.domain.enums.auth import Permission


class ViewAllCustomers(BaseCommand):
    def __init__(
        self,
        params: Iterable[str],
        app_data: ApplicationData,
        auth: AuthService,
        view_all_customers_use_case: ViewAllCustomersUseCase,
    ) -> None:
        super().__init__(params, app_data, auth)
        self._view_all_customers_use_case = view_all_customers_use_case

    @requires(Permission.CUSTOMER_VIEW)
    def execute(self) -> str:
        customers = self._view_all_customers_use_case.execute()
        return (
            "\n\n".join(f"Customer {c.customer_id}: {c.name} ({c.email}, {c.phone_number})" for c in customers)
            if customers
            else "No customers."
        )
