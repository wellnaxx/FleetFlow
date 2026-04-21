from src.application.services.auth_service import AuthService
from src.domain.entities.users.user import User


class LoginUseCase:
    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def execute(self, username: str, password: str) -> User:
        return self._auth.login(username, password)
