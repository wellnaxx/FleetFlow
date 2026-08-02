"""Structured result returned by package assignment policy evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.enums.package_assignment_rejection_reasons import PackageAssignmentRejectionReason
from src.domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class PackageAssignmentDecision:
    """Immutable acceptance or rejection produced by assignment policy.

    Attributes:
        reason: Machine-readable rejection category, or ``None`` when accepted.
        message: Human-readable rejection explanation, or ``None`` when accepted.
    """

    reason: PackageAssignmentRejectionReason | None = None
    message: str | None = None

    @property
    def accepted(self) -> bool:
        """Return whether assignment is allowed."""
        return self.reason is None

    def __post_init__(self) -> None:
        """Require acceptance and rejection fields to describe one valid state.

        Raises:
            DomainValidationError: If the reason or message has an invalid
                runtime type, an accepted decision has a message, or a rejected
                decision lacks a non-blank message.
        """
        _require_runtime_types(self.reason, self.message)

        if self.reason is None and self.message is not None:
            raise DomainValidationError("An accepted assignment cannot contain a rejection message.")

        if self.reason is not None and (self.message is None or not self.message.strip()):
            raise DomainValidationError("A rejected assignment requires a message.")

    @classmethod
    def accept(cls) -> PackageAssignmentDecision:
        """Return an accepted assignment decision."""
        return cls()

    @classmethod
    def reject(cls, reason: PackageAssignmentRejectionReason, message: str) -> PackageAssignmentDecision:
        """Return a rejected assignment decision.

        Args:
            reason: Machine-readable rejection category.
            message: Human-readable rejection explanation.

        Returns:
            Validated rejected decision.

        Raises:
            DomainValidationError: If ``message`` is empty or blank.
        """
        return cls(reason=reason, message=message)


def _require_runtime_types(reason: object, message: object) -> None:
    """Require assignment decision fields to satisfy their runtime types."""
    if reason is not None and not isinstance(reason, PackageAssignmentRejectionReason):
        raise DomainValidationError("Assignment rejection reason must be a PackageAssignmentRejectionReason.")

    if message is not None and not isinstance(message, str):
        raise DomainValidationError("Assignment decision message must be a string.")
