from src.application.models.user_record import UserRecord
from src.application.services.auth_service import AuthService
from src.domain.enums.auth import Role


class RegisterUserUseCase:
    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def execute(
        self,
        username: str,
        role: Role,
        name: str,
        email: str,
        phone_number: str,
        password: str,
    ) -> UserRecord:
        return self._auth.register_user(
            username=username,
            role=role,
            name=name,
            email=email,
            phone_number=phone_number,
            password=password,
        )
