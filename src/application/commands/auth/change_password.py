"""Command contract for changing the current user's password."""

from dataclasses import dataclass, field
from typing import Final

from src.application.messaging.command import Command, CommandKey


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeOwnPasswordCommand(Command):
    """Request a self-service password change for the current principal.

    The target username is absent because authorization context identifies the
    account being changed.

    Attributes:
        current_password: Existing plain-text password used for verification.
        new_password: Replacement plain-text password. Password fields are
            excluded from representations to avoid accidental disclosure.
    """

    current_password: str = field(repr=False)
    new_password: str = field(repr=False)


CHANGE_OWN_PASSWORD: Final[CommandKey[ChangeOwnPasswordCommand, None]] = CommandKey(
    name="change_own_password",
    command_type=ChangeOwnPasswordCommand,
)
