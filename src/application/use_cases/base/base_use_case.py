from abc import ABC, abstractmethod
from typing import Any


class BaseUseCase[T](ABC):
    """Base for all use cases."""

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> T:
        """Execute the use case."""
        ...
