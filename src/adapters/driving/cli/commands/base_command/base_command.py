"""Shared command base class and command-state flag contract."""

from abc import ABC, abstractmethod
from collections.abc import Iterable


class BaseCommand[T](ABC):
    """Abstract base for all CLI commands.

    Concrete commands receive one application execution dependency. Current
    adapters receive either a command bus or query bus through a specialized
    subclass.

    Class flags describe command side effects for the CLI engine:
    `mutates_state` means the command changes runtime world state,
    `autosaves_state` means a successful command should trigger default
    world-state autosave, `skips_heartbeat` means pre-command heartbeat should
    not run, and `mutates_session` means auth/session state may change.
    """

    mutates_state: bool = False
    mutates_session: bool = False
    skips_heartbeat: bool = False
    autosaves_state: bool = False

    def __init__(
        self,
        params: Iterable[str],
        dependency: T,
    ) -> None:
        """Initialize a command with raw CLI parameters and its dependency.

        Args:
            params: Raw string parameters parsed from the CLI.
            dependency: Application execution dependency used by the command.
        """
        self._params = tuple(params)
        self._dependency = dependency

    @property
    def params(self) -> tuple[str, ...]:
        """Return the raw command parameters."""
        return self._params

    @property
    def dependency(self) -> T:
        """Return the command's injected application dependency."""
        return self._dependency

    @abstractmethod
    def execute(self) -> str:
        """Execute the command and return CLI output."""
        raise NotImplementedError  # pragma: no cover
