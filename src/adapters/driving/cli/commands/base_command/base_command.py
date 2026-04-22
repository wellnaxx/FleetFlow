from abc import ABC, abstractmethod
from collections.abc import Iterable

from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService


class BaseCommand[T](ABC):
    """Abstract base for all CLI commands.

    Concrete commands expose one application use case plus the shared auth and
    authorization services needed at the command boundary.
    """

    mutates_state: bool = False
    mutates_session: bool = False
    skips_heartbeat: bool = False

    def __init__(
        self,
        params: Iterable[str],
        auth: AuthService,
        authz: AuthorizationService,
        use_case: T,
    ) -> None:
        """Initialize a command with shared CLI dependencies.

        Args:
            params: Raw string parameters parsed from the CLI.
            auth: Authentication service available to the command.
            authz: Authorization service available to the command.
            use_case: Application use case executed by the command.
        """
        self._params = tuple(params)
        self._auth = auth
        self._authz = authz
        self._use_case = use_case

    @property
    def params(self) -> tuple[str, ...]:
        """Return the raw command parameters."""
        return self._params

    @property
    def auth(self) -> AuthService:
        """Return the authentication service for the command."""
        return self._auth

    @property
    def authz(self) -> AuthorizationService:
        """Return the authorization service for the command."""
        return self._authz

    @property
    def use_case(self) -> T:
        """Return the application use case bound to the command."""
        return self._use_case

    @abstractmethod
    def execute(self) -> str:
        """Execute the command and return CLI output."""
        raise NotImplementedError  # pragma: no cover
