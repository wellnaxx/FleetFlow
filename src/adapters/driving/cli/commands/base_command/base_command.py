from abc import ABC, abstractmethod
from collections.abc import Iterable

from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService


class BaseCommand[T](ABC):
    """Abstract base for all CLI commands."""

    mutates_state = False
    mutates_session = False

    def __init__(
        self,
        params: Iterable[str],
        auth: AuthService,
        authz: AuthorizationService,
        use_case: T,
    ) -> None:
        self._params = tuple(params)
        self._auth = auth
        self._authz = authz
        self._use_case = use_case

    @property
    def params(self) -> tuple[str, ...]:
        return self._params

    @property
    def auth(self) -> AuthService:
        return self._auth

    @property
    def authz(self) -> AuthorizationService:
        return self._authz

    @property
    def use_case(self) -> T:
        return self._use_case

    @abstractmethod
    def execute(self) -> str:
        raise NotImplementedError  # pragma: no cover
