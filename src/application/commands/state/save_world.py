"""Command contract for exporting the current world state."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.command import Command, CommandKey


@dataclass(frozen=True, slots=True, kw_only=True)
class SaveWorldCommand(Command):
    """Request saving the current world state to a snapshot path.

    Attributes:
        path: Caller-supplied snapshot path. Adapter-specific default selection
            occurs before constructing the command.
    """

    path: str


SAVE_WORLD: Final[CommandKey[SaveWorldCommand, str]] = CommandKey(
    name="save_world",
    command_type=SaveWorldCommand,
)
