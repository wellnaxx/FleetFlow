"""Command contract for removing a package from active state."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.command import Command, CommandKey
from src.application.results.remove_package_result import RemovePackageResult


@dataclass(frozen=True, slots=True, kw_only=True)
class RemovePackageCommand(Command):
    """Request removal of one package and its active route link.

    Attributes:
        package_id: Stable identifier of the package to remove.
    """

    package_id: int


REMOVE_PACKAGE: Final[CommandKey[RemovePackageCommand, RemovePackageResult]] = CommandKey(
    name="remove_package",
    command_type=RemovePackageCommand,
)
