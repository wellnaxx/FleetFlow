"""Command contract for replacing runtime state from a snapshot."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.command import Command, CommandKey


@dataclass(frozen=True, slots=True, kw_only=True)
class LoadWorldCommand(Command):
    """Request replacement of runtime world state from a snapshot path.

    Attributes:
        path: Caller-supplied snapshot path. Adapter-specific default selection
            occurs before constructing the command.
    """

    path: str


LOAD_WORLD: Final[CommandKey[LoadWorldCommand, str]] = CommandKey(
    name="load_world",
    command_type=LoadWorldCommand,
)
