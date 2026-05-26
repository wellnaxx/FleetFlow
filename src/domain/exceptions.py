"""Domain exception types for validation and business-rule failures."""

from src.application.exceptions.application_errors import ApplicationError


class DomainError(ApplicationError):
    """Base class for expected domain/business-rule failures."""


class EntityNotFoundError(DomainError):
    """Requested domain entity was not found."""


class DomainValidationError(DomainError):
    """Input or domain data failed validation."""


class BusinessRuleViolationError(DomainError):
    """A domain operation violates a business rule."""


class DomainConflictError(DomainError):
    """Operation conflicts with current domain state."""
