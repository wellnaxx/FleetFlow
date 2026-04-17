import unittest
from unittest.mock import Mock

from src.adapters.driving.cli.commands.view_all_customers import ViewAllCustomers


class TestViewAllCustomers_Should(unittest.TestCase):
    def setUp(self):
        self.mock_app_data = Mock()
        self.command = ViewAllCustomers(params={}, app_data=self.mock_app_data, auth=None)  # type: ignore[reportArgumentType]

    def test_no_customers_available(self):
        self.mock_app_data.view_all_customers.return_value = []
        result = self.command.execute()
        self.assertEqual(result, "No customers.")
        self.mock_app_data.view_all_customers.assert_called_once()

    def test_with_multiple_customers(self):
        mock_customer1 = Mock()
        mock_customer1.customer_id = 1
        mock_customer1.name = "John Doe"
        mock_customer1.email = "john.doe@example.com"
        mock_customer1.phone_number = "123-456-7890"

        mock_customer2 = Mock()
        mock_customer2.customer_id = 2
        mock_customer2.name = "Jane Smith"
        mock_customer2.email = "jane.smith@example.com"
        mock_customer2.phone_number = "098-765-4321"

        self.mock_app_data.view_all_customers.return_value = [mock_customer1, mock_customer2]

        expected_output = (
            "Customer 1: John Doe (john.doe@example.com, 123-456-7890)\n\n"
            "Customer 2: Jane Smith (jane.smith@example.com, 098-765-4321)"
        )
        result = self.command.execute()
        self.assertEqual(result, expected_output)
        self.mock_app_data.view_all_customers.assert_called_once()
