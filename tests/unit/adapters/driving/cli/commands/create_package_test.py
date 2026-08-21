"""Tests for the command-bus-backed create-package CLI adapter."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.create_package import CreatePackage
from src.application.commands.packages.create_package import CREATE_PACKAGE, CreatePackageCommand
from src.ports.input.command_bus import CommandBus


class CreatePackageShould(unittest.TestCase):
    """Verify CLI parsing, dispatch, error propagation, and rendering."""

    def setUp(self) -> None:
        """Create an isolated command bus for each test."""
        self.command_bus = MagicMock(spec=CommandBus)

    def make_command(self, params: list[str]) -> CreatePackage:
        """Build the adapter with raw parameters and the mocked bus."""
        return CreatePackage(params, self.command_bus)

    def test_mutates_and_autosaves_state(self) -> None:
        self.assertTrue(CreatePackage.mutates_state)
        self.assertTrue(CreatePackage.autosaves_state)

    def test_dispatches_minimal_command_and_renders_result(self) -> None:
        package = SimpleNamespace(package_id=123, customer=SimpleNamespace(customer_id=55))
        self.command_bus.dispatch.return_value = package
        command = self.make_command(["A1", "B2", "12.5", "Alice"])

        result = command.execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=CREATE_PACKAGE,
            command=CreatePackageCommand(
                start="A1",
                end="B2",
                weight=12.5,
                name="Alice",
                email="",
                phone="",
            ),
        )
        self.assertEqual(
            result,
            "Package 123 was created for customer Alice (ID: 55) successfully.",
        )

    def test_dispatches_all_optional_contact_fields(self) -> None:
        package = SimpleNamespace(package_id=999, customer=SimpleNamespace(customer_id=1))
        self.command_bus.dispatch.return_value = package
        command = self.make_command(["S1", "E9", "7", "Bob", "bob@ex.com", "0412345678"])

        result = command.execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=CREATE_PACKAGE,
            command=CreatePackageCommand(
                start="S1",
                end="E9",
                weight=7.0,
                name="Bob",
                email="bob@ex.com",
                phone="0412345678",
            ),
        )
        self.assertEqual(
            result,
            "Package 999 was created for customer Bob (ID: 1) successfully.",
        )

    def test_propagates_permission_error_from_command_bus(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: PACKAGE_CREATE")
        command = self.make_command(["A1", "B2", "12.5", "Alice"])

        with self.assertRaisesRegex(PermissionError, "PACKAGE_CREATE"):
            command.execute()

        self.command_bus.dispatch.assert_called_once()

    @patch("src.adapters.driving.cli.commands.create_package.try_parse_float")
    def test_weight_parse_failure_prevents_dispatch(self, parse_float: MagicMock) -> None:
        parse_float.side_effect = ValueError("not a number")
        command = self.make_command(["A1", "B2", "x", "Alice"])

        with self.assertRaisesRegex(ValueError, "not a number"):
            command.execute()

        parse_float.assert_called_once_with("x", "weight")
        self.command_bus.dispatch.assert_not_called()

    def test_propagates_command_bus_failure(self) -> None:
        self.command_bus.dispatch.side_effect = RuntimeError("db error")
        command = self.make_command(["A1", "B2", "2.5", "Alice"])

        with self.assertRaisesRegex(RuntimeError, "db error"):
            command.execute()

        self.command_bus.dispatch.assert_called_once()

    @patch("src.adapters.driving.cli.commands.create_package.validate_params_count")
    def test_validates_supported_parameter_count(self, validate: MagicMock) -> None:
        package = SimpleNamespace(package_id=1, customer=SimpleNamespace(customer_id=2))
        self.command_bus.dispatch.return_value = package
        params = ["S", "E", "1", "Name"]
        command = self.make_command(params)

        command.execute()

        validate.assert_called_once_with(tuple(params), 4, 6)


if __name__ == "__main__":
    unittest.main()
