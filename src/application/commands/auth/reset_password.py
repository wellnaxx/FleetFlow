"""Command contract for an administrator resetting another user's password."""

from dataclasses import dataclass, field
from typing import Final

from src.application.messaging.command import Command, CommandKey


@dataclass(frozen=True, slots=True, kw_only=True)
class ResetUserPasswordCommand(Command):
    """Request an administrative password reset for a target account.

    Attributes:
        username: Login name of the account whose password should be reset.
        new_password: Replacement plain-text password. Excluded from object
            representations to reduce accidental credential disclosure.
    """

    username: str
    new_password: str = field(repr=False)


RESET_USER_PASSWORD: Final[CommandKey[ResetUserPasswordCommand, None]] = CommandKey(
    name="reset_user_password",
    command_type=ResetUserPasswordCommand,
)
