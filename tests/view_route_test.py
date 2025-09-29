import unittest
from unittest.mock import patch, MagicMock

from src.commands.view_route import ViewRoute


class ViewRoute_Should(unittest.TestCase):
    def make_cmd(self, params):
        cmd = ViewRoute.__new__(ViewRoute)
        cmd._params = params
        cmd._app_data = MagicMock()
        return cmd

    @patch('src.commands.view_route.validate_params_exact')
    @patch('src.commands.view_route.try_parse_int')
    def test_success_returns_route_info(self, mock_parse, mock_validate):
        mock_parse.return_value = 12
        cmd = self.make_cmd(["12"])
        route = MagicMock()
        route.info.return_value = "ROUTE-INFO"
        cmd._app_data.view_route.return_value = route

        result = cmd.execute()

        mock_validate.assert_called_once_with(["12"], 1)
        mock_parse.assert_called_once_with("12")
        cmd._app_data.view_route.assert_called_once_with(12)
        route.info.assert_called_once_with()
        self.assertEqual(result, "ROUTE-INFO")

    @patch('src.commands.view_route.validate_params_exact')
    @patch('src.commands.view_route.try_parse_int')
    def test_missing_route_raises(self, mock_parse, mock_validate):
        mock_parse.return_value = 77
        cmd = self.make_cmd(["77"])
        cmd._app_data.view_route.return_value = None

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Route with ID 77 not found", str(ctx.exception))
        cmd._app_data.view_route.assert_called_once_with(77)

    @patch('src.commands.view_route.validate_params_exact')
    @patch('src.commands.view_route.try_parse_int')
    def test_parse_failure_bubbles_and_stops(self, mock_parse, mock_validate):
        mock_parse.side_effect = ValueError("not an int")
        cmd = self.make_cmd(["abc"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("not an int", str(ctx.exception))
        cmd._app_data.view_route.assert_not_called()

    def test_validate_params_exact_called_with_one(self):
        cmd = self.make_cmd(["5"])
        with patch('src.commands.view_route.validate_params_exact') as mock_validate, \
             patch('src.commands.view_route.try_parse_int', return_value=5), \
             patch.object(cmd._app_data, 'view_route', return_value=MagicMock(info=lambda: "ok")):
            _ = cmd.execute()
            mock_validate.assert_called_once_with(["5"], 1)

    def test_no_mutates_flags(self):
        self.assertFalse(getattr(ViewRoute, "mutates_state", False))
        self.assertFalse(getattr(ViewRoute, "mutates_session", False))

    @patch('src.commands.view_route.validate_params_exact')
    @patch('src.commands.view_route.try_parse_int')
    def test_ignores_extra_params_beyond_first(self, mock_parse, mock_validate):
        mock_parse.return_value = 1
        cmd = self.make_cmd(["1", "extra", "ignored"])
        cmd._app_data.view_route.return_value = MagicMock(info=lambda: "ok")

        _ = cmd.execute()

        mock_parse.assert_called_once_with("1")
        cmd._app_data.view_route.assert_called_once_with(1)

