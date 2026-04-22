from abc import ABC, abstractmethod
from collections.abc import Iterable

from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService
from src.core.application_data import ApplicationData


class BaseCommand(ABC):
    """Abstract base for all commands: holds params and app context."""

    def __init__(self, params: Iterable[str], app_data: ApplicationData, auth: AuthService) -> None:
        self._params = tuple(params)
        self._app_data = app_data
        self._auth = auth

    @property
    def params(self) -> tuple[str, ...]:
        return self._params

    @property
    def app_data(self) -> ApplicationData:
        return self._app_data

    @property
    def auth(self) -> AuthService:
        return self._auth

    @property
    def authz(self) -> AuthorizationService:
        return self._app_data.authz

    @abstractmethod
    def execute(self) -> str:
        raise NotImplementedError  # pragma: no cover


class UseCaseCommand[T](BaseCommand, ABC):
    """Base commands that depend on a single use case"""

    def __init__(
        self, params: Iterable[str], app_data: ApplicationData, auth: AuthService, use_case: T
    ) -> None:
        super().__init__(params, app_data, auth)
        self._use_case = use_case

    @property
    def use_case(self) -> T:
        return self._use_case
