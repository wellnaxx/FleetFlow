from abc import ABC, abstractmethod
from collections.abc import Iterable

from src.core.application_data import ApplicationData
from src.core.auth_service import AuthService


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

    @abstractmethod
    def execute(self) -> str:
        raise NotImplementedError  # pragma: no cover
