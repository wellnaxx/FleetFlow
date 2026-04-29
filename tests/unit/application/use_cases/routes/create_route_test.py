import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.domain.value_objects.location_code import LocationCode


class CreateRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.use_case = CreateRouteUseCase(self.mock_routes)

    @patch("src.application.use_cases.routes.create_route.Map.is_valid_location")
    def test_creates_route_when_inputs_are_valid(
        self,
        mock_is_valid: MagicMock,
    ) -> None:
        mock_is_valid.return_value = True

        departure = datetime(2025, 10, 12, 6, 0)
        fake_route = MagicMock()
        self.mock_routes.create.return_value = fake_route

        locations = [LocationCode("SYD"), LocationCode("MEL"), LocationCode("ADL")]
        result = self.use_case.execute(locations, departure)

        self.assertIs(result, fake_route)
        self.assertEqual(
            [call.args[0] for call in mock_is_valid.call_args_list],
            ["SYD", "MEL", "ADL"],
        )
        self.mock_routes.create.assert_called_once_with(locations=locations, departure_time=departure)

    def test_raises_when_fewer_than_two_locations(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute([LocationCode("SYD")], None)

        self.assertIn("at least 2 locations", str(ctx.exception))
        self.mock_routes.create.assert_not_called()

    @patch("src.application.use_cases.routes.create_route.Map.is_valid_location")
    def test_raises_when_any_location_is_invalid(
        self,
        mock_is_valid: MagicMock,
    ) -> None:
        def side_effect(location: str) -> bool:
            return location != "BAD"

        mock_is_valid.side_effect = side_effect

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute([LocationCode("SYD"), LocationCode("BAD"), LocationCode("MEL")], None)

        self.assertIn("Invalid location: BAD", str(ctx.exception))
        self.mock_routes.create.assert_not_called()

    @patch("src.application.use_cases.routes.create_route.Map.is_valid_location")
    def test_checks_each_location(
        self,
        mock_is_valid: MagicMock,
    ) -> None:
        mock_is_valid.return_value = True
        fake_route = MagicMock()
        self.mock_routes.create.return_value = fake_route

        locations = [LocationCode("A"), LocationCode("B"), LocationCode("C")]
        result = self.use_case.execute(locations, None)

        self.assertIs(result, fake_route)
        self.assertEqual(
            [call.args[0] for call in mock_is_valid.call_args_list],
            ["A", "B", "C"],
        )
        self.mock_routes.create.assert_called_once_with(locations=locations, departure_time=None)
