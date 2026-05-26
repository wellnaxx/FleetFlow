"""Repository-port exception types."""


class RepositoryError(Exception):
    """Base class for output-port repository failures."""


class DuplicateKeyError(RepositoryError):
    """Raised when a repository create operation violates a unique key."""
