from src.application.services.auth_service import AuthService


class ChangePasswordUseCase:
    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def execute(self, username: str, new_password: str, old_password: str | None = None) -> None:
        if old_password is None:
            self._auth.reset_password(username, new_password)
            return
        self._auth.change_password(username, old_password, new_password)
