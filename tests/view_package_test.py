import unittest
from unittest.mock import Mock, patch

from src.commands.view_package import ViewPackage


class TestViewPackage_Should(unittest.TestCase):

    def setUp(self):
        self.mock_app_data = Mock()
        self.command = ViewPackage(params=[], app_data=self.mock_app_data, auth=None)

    def test_successful_execution(self):
        mock_package = Mock()
        mock_package.info.return_value = "Package 123 details"

        self.command._params = ["123"]
        self.mock_app_data.view_package.return_value = mock_package

        result = self.command.execute()
        self.assertEqual(result, "Package 123 details")
        self.mock_app_data.view_package.assert_called_once_with(123)

    def test_package_not_found(self):
        self.command._params = ["999"]
        self.mock_app_data.view_package.return_value = None

        with self.assertRaises(ValueError) as context:
            self.command.execute()

        self.assertTrue("Package with ID 999 not found" in str(context.exception))
        self.mock_app_data.view_package.assert_called_once_with(999)

    def test_invalid_parameter_count(self):
        with patch('src.commands.view_package.validate_params_exact') as mock_validate:
            mock_validate.side_effect = ValueError("Expected 1 parameter(s).")
            self.command._params = []  # No parameters

            with self.assertRaises(ValueError) as context:
                self.command.execute()

            self.assertTrue("Expected 1 parameter(s)." in str(context.exception))
            mock_validate.assert_called_once_with(self.command._params, 1)

    def test_invalid_parameter_type(self):
        with patch('src.commands.view_package.try_parse_int') as mock_try_parse:
            mock_try_parse.side_effect = ValueError("Parameter 'abc' is not a valid integer.")
            self.command._params = ["abc"]

            with self.assertRaises(ValueError) as context:
                self.command.execute()

            self.assertTrue("Parameter 'abc' is not a valid integer." in str(context.exception))
            mock_try_parse.assert_called_once_with("abc")
