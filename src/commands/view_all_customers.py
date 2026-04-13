from src.commands.base_command.base_command import BaseCommand


class ViewAllCustomers(BaseCommand):
    def execute(self) -> str:
        customers = self._app_data.view_all_customers()
        return (
            "\n\n".join(f"Customer {c.customer_id}: {c.name} ({c.email}, {c.phone_number})" for c in customers)
            if customers
            else "No customers."
        )
