"""Tests for the command-bus-backed remove-package CLI adapter."""

import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.remove_package import RemovePackage
from src.application.commands.packages.remove_package import REMOVE_PACKAGE, RemovePackageCommand
from src.ports.input.command_bus import CommandBus


class RemovePackageShould(unittest.TestCase):
    """Verify package-id parsing, dispatch, rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated command bus for each test."""
        self.command_bus = MagicMock(spec=CommandBus)

    def make_command(self, params: list[str]) -> RemovePackage:
        """Build the adapter with raw parameters and the mocked bus."""
        return RemovePackage(params, self.command_bus)

    def test_mutates_and_autosaves_state(self) -> None:
        self.assertTrue(RemovePackage.mutates_state)
        self.assertTrue(RemovePackage.autosaves_state)

    def test_dispatches_remove_command_and_renders_confirmation(self) -> None:
        command = self.make_command(["42"])

        result = command.execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=REMOVE_PACKAGE,
            command=RemovePackageCommand(package_id=42),
        )
        self.assertEqual(result, "Package 42 removed.")

    def test_propagates_permission_error_from_command_bus(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: PACKAGE_REMOVE")
        command = self.make_command(["42"])

        with self.assertRaisesRegex(PermissionError, "PACKAGE_REMOVE"):
            command.execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=REMOVE_PACKAGE,
            command=RemovePackageCommand(package_id=42),
        )

    @patch("src.adapters.driving.cli.commands.remove_package.try_parse_int")
    @patch("src.adapters.driving.cli.commands.remove_package.validate_params_exact")
    def test_parameter_count_failure_prevents_parsing_and_dispatch(
        self,
        validate: MagicMock,
        parse_int: MagicMock,
    ) -> None:
        validate.side_effect = ValueError("Expected 1 parameter(s).")
        command = self.make_command([])

        with self.assertRaisesRegex(ValueError, "Expected 1 parameter"):
            command.execute()

        validate.assert_called_once_with((), 1)
        parse_int.assert_not_called()
        self.command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.remove_package.try_parse_int")
    def test_invalid_integer_prevents_dispatch(self, parse_int: MagicMock) -> None:
        parse_int.side_effect = ValueError("Parameter 'str' is not a valid integer.")
        command = self.make_command(["str"])

        with self.assertRaisesRegex(ValueError, "not a valid integer"):
            command.execute()

        parse_int.assert_called_once_with("str", "package_id")
        self.command_bus.dispatch.assert_not_called()

    def test_propagates_command_bus_failure(self) -> None:
        self.command_bus.dispatch.side_effect = RuntimeError("write failed")
        command = self.make_command(["42"])

        with self.assertRaisesRegex(RuntimeError, "write failed"):
            command.execute()

        self.command_bus.dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
