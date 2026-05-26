"""Application-layer exception types."""


class ApplicationError(Exception):
    """Base class for application/use-case failures."""


class AuthenticationError(ApplicationError):
    """Raised when authentication fails."""


class NotFoundError(ApplicationError):
    """Raised when a requested application resource does not exist."""


class ValidationError(ApplicationError):
    """Raised when command/use-case input is invalid."""


class UnsupportedRoleError(ValidationError):
    """Raised when persisted role data names a role the runtime cannot hydrate."""


class ConflictError(ApplicationError):
    """Raised when a requested operation conflicts with current state."""
