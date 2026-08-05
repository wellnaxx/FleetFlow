"""Command contract for terminating the current authenticated session."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.command import Command, CommandKey


@dataclass(frozen=True, slots=True, kw_only=True)
class LogoutCommand(Command):
    """Request termination of the currently authenticated session.

    Actor identity comes from authorization context rather than command fields,
    preventing caller-supplied identity from diverging from the principal.
    """


LOGOUT: Final[CommandKey[LogoutCommand, None]] = CommandKey(
    name="logout",
    command_type=LogoutCommand,
)
