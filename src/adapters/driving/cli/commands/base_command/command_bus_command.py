"""Shared base for CLI commands that dispatch application commands."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.ports.input.command_bus import CommandBus


class CommandBusCommand(BaseCommand[CommandBus]):
    """Expose an injected dispatch-only command bus to a CLI command.

    The inherited constructor accepts raw CLI parameters followed by the
    command bus. This keeps bus injection explicit without requiring every
    command-backed CLI command to repeat the same constructor.
    """

    @property
    def command_bus(self) -> CommandBus:
        """Return the command bus injected by the command factory."""
        return self.dependency
