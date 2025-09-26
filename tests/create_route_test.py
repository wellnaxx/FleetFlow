import unittest
from unittest.mock import Mock
from src.commands.create_route import CreateRoute


class CreateRouteCommandTest_Should(unittest.TestCase):
    def test_min_params_command(self):
        app_data = Mock()
        auth = Mock()
        with self.assertRaises(ValueError):
            cmd = CreateRoute(['a'] * 1, app_data, auth).execute()
