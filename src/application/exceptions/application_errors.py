"""Application-layer exception types."""


class ApplicationError(Exception):
    """Base class for application/use-case failures."""


class NotFoundError(ApplicationError):
    """Raised when a requested application resource does not exist."""


class ValidationError(ApplicationError):
    """Raised when command/use-case input is invalid."""


class ConflictError(ApplicationError):
    """Raised when a requested operation conflicts with current state."""
