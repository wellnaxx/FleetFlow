import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from domain.value_objects.location_code import LocationCode
from src.application.use_cases.routes.create_route import CreateRouteUseCase


class CreateRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.use_case = CreateRouteUseCase(self.mock_routes)

    @patch("src.application.use_cases.routes.create_route.DeliveryRoute")
    @patch("src.application.use_cases.routes.create_route.Map.is_valid_location")
    def test_creates_route_when_inputs_are_valid(
        self,
        mock_is_valid: MagicMock,
        mock_route_cls: MagicMock,
    ) -> None:
        mock_is_valid.return_value = True
        self.mock_routes.peek_next_id.return_value = 42

        departure = datetime(2025, 10, 12, 6, 0)
        fake_route = MagicMock()
        mock_route_cls.return_value = fake_route

        result = self.use_case.execute(
            [LocationCode("SYD"), LocationCode("MEL"), LocationCode("ADL")], departure
        )

        self.assertIs(result, fake_route)
        self.assertEqual(
            [call.args[0] for call in mock_is_valid.call_args_list],
            ["SYD", "MEL", "ADL"],
        )
        self.mock_routes.peek_next_id.assert_called_once_with()
        mock_route_cls.assert_called_once_with(
            "SYD",
            "MEL",
            "ADL",
            departure_time=departure,
            route_id=42,
        )
        self.mock_routes.add.assert_called_once_with(fake_route)

    def test_raises_when_fewer_than_two_locations(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute([LocationCode("SYD")], None)

        self.assertIn("at least 2 locations", str(ctx.exception))
        self.mock_routes.next_id.assert_not_called()
        self.mock_routes.add.assert_not_called()

    @patch("src.application.use_cases.routes.create_route.DeliveryRoute")
    @patch("src.application.use_cases.routes.create_route.Map.is_valid_location")
    def test_raises_when_any_location_is_invalid(
        self,
        mock_is_valid: MagicMock,
        mock_route_cls: MagicMock,
    ) -> None:
        def side_effect(location: str) -> bool:
            return location != "BAD"

        mock_is_valid.side_effect = side_effect

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute([LocationCode("SYD"), LocationCode("BAD"), LocationCode("MEL")], None)

        self.assertIn("Invalid location: BAD", str(ctx.exception))
        self.mock_routes.next_id.assert_not_called()
        mock_route_cls.assert_not_called()
        self.mock_routes.add.assert_not_called()

    @patch("src.application.use_cases.routes.create_route.DeliveryRoute")
    @patch("src.application.use_cases.routes.create_route.Map.is_valid_location")
    def test_checks_each_location(
        self,
        mock_is_valid: MagicMock,
        mock_route_cls: MagicMock,
    ) -> None:
        mock_is_valid.return_value = True
        self.mock_routes.peek_next_id.return_value = 7
        mock_route_cls.return_value = MagicMock()

        _ = self.use_case.execute([LocationCode("A"), LocationCode("B"), LocationCode("C")], None)

        self.assertEqual(
            [call.args[0] for call in mock_is_valid.call_args_list],
            ["A", "B", "C"],
        )
        self.mock_routes.peek_next_id.assert_called_once_with()
        self.mock_routes.add.assert_called_once()
