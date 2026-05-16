"""Shared command base class and command-state flag contract."""

from abc import ABC, abstractmethod
from collections.abc import Iterable


class BaseCommand[T](ABC):
    """Abstract base for all CLI commands.

    Concrete commands expose one application use case at the CLI boundary.

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
        use_case: T,
    ) -> None:
        """Initialize a command with raw CLI params and its use case.

        Args:
            params: Raw string parameters parsed from the CLI.
            use_case: Application use case executed by the command.
        """
        self._params = tuple(params)
        self._use_case = use_case

    @property
    def params(self) -> tuple[str, ...]:
        """Return the raw command parameters."""
        return self._params

    @property
    def use_case(self) -> T:
        """Return the application use case bound to the command."""
        return self._use_case

    @abstractmethod
    def execute(self) -> str:
        """Execute the command and return CLI output."""
        raise NotImplementedError  # pragma: no cover
