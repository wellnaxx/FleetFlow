"""Command contract for authenticating a user session."""

from dataclasses import dataclass, field
from typing import Final

from src.application.messaging.command import Command, CommandKey
from src.application.results.login_result import LoginResult


@dataclass(frozen=True, slots=True, kw_only=True)
class LoginCommand(Command):
    """Request authentication with persisted user credentials.

    Attributes:
        username: Login name supplied by the caller.
        password: Plain-text password to verify. Excluded from representations
            to reduce accidental credential disclosure in logs and failures.
    """

    username: str
    password: str = field(repr=False)


LOGIN: Final[CommandKey[LoginCommand, LoginResult]] = CommandKey(
    name="login",
    command_type=LoginCommand,
)
