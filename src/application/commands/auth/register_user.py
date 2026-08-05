"""Command contract for registering a new authenticated user account."""

from dataclasses import dataclass, field
from typing import Final

from src.application.messaging.command import Command, CommandKey
from src.application.models.user_record import UserRecord
from src.domain.enums.auth import Role


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisterUserCommand(Command):
    """Request creation of a user account by an authorized administrator.

    Attributes:
        username: Unique login name requested for the account.
        role: Authorization role assigned to the account.
        name: Human-readable display name.
        email: Optional email address.
        phone_number: Optional phone number.
        password: Initial plain-text password. Excluded from representations
            to reduce accidental credential disclosure.
    """

    username: str
    role: Role
    name: str
    password: str = field(repr=False)
    email: str = ""
    phone_number: str = ""


REGISTER_USER: Final[CommandKey[RegisterUserCommand, UserRecord]] = CommandKey(
    name="register_user",
    command_type=RegisterUserCommand,
)
