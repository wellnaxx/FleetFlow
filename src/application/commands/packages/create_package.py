"""Command contract for creating a package and resolving its customer."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.command import Command, CommandKey
from src.domain.entities.delivery_package import DeliveryPackage


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatePackageCommand(Command):
    """Request creation of a delivery package.

    The command preserves existing validation ownership: adapters parse
    ``weight``, while the use case and domain normalize locations, contact
    information, and package invariants.

    Attributes:
        start: Raw pickup location code.
        end: Raw delivery location code.
        weight: Parsed package weight in kilograms.
        name: Customer display name.
        email: Optional customer email address.
        phone: Optional customer phone number.
    """

    start: str
    end: str
    weight: float
    name: str
    email: str = ""
    phone: str = ""


CREATE_PACKAGE: Final[CommandKey[CreatePackageCommand, DeliveryPackage]] = CommandKey(
    name="create_package",
    command_type=CreatePackageCommand,
)
