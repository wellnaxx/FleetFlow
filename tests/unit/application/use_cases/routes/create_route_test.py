import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from tests.unit.application.use_cases.authz_helpers import manager_authz


class CreateRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.use_case = CreateRouteUseCase(self.mock_routes, manager_authz())

    def test_creates_route_when_inputs_are_valid(self) -> None:
        departure = datetime(2025, 10, 12, 6, 0)
        fake_route = MagicMock()
        self.mock_routes.create.return_value = fake_route

        locations = [LocationCode("SYD"), LocationCode("MEL"), LocationCode("ADL")]
        result = self.use_case.execute(locations, departure)

        self.assertIs(result, fake_route)
        self.mock_routes.create.assert_called_once_with(locations=locations, departure_time=departure)

    def test_raises_when_fewer_than_two_locations(self) -> None:
        self.mock_routes.create.side_effect = DomainValidationError(
            "A route must have at least two locations."
        )

        with self.assertRaises(DomainValidationError) as ctx:
            self.use_case.execute([LocationCode("SYD")], None)

        self.assertIn("at least two locations", str(ctx.exception))
        self.mock_routes.create.assert_called_once_with(
            locations=[LocationCode("SYD")],
            departure_time=None,
        )

    def test_raises_when_any_location_is_invalid(self) -> None:
        self.mock_routes.create.side_effect = DomainValidationError("Invalid location code: BAD.")

        with self.assertRaises(DomainValidationError) as ctx:
            self.use_case.execute([LocationCode("SYD"), LocationCode("BAD"), LocationCode("MEL")], None)

        self.assertIn("Invalid location code: BAD", str(ctx.exception))
        self.mock_routes.create.assert_called_once_with(
        locations=[LocationCode("SYD"), LocationCode("BAD"), LocationCode("MEL")],
        departure_time=None,
    )


    def test_delegates_locations_to_repository_for_validation_and_creation(self) -> None:
        fake_route = MagicMock()
        self.mock_routes.create.return_value = fake_route

        locations = [LocationCode("A"), LocationCode("B"), LocationCode("C")]
        result = self.use_case.execute(locations, None)

        self.assertIs(result, fake_route)
        self.mock_routes.create.assert_called_once_with(locations=locations, departure_time=None)
