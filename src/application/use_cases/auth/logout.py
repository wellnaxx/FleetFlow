from src.application.services.auth_service import AuthService


class LogoutUseCase:
    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def execute(self) -> None:
        self._auth.logout()
