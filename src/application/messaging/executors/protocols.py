"""Structural contracts shared by application message executors."""

from typing import Protocol


class MessageExecutor[M, R](Protocol):
    """Execute one typed message and return its associated result."""

    def execute(self, message: M) -> R:
        """Execute a command or query.

        Args:
            message: Typed application message accepted by this executor.

        Returns:
            Result associated with the message registration.

        Raises:
            Exception: Propagates application, domain, persistence, and other
                execution failures.
        """
        ...
