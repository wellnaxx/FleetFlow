from src.application.models.user_record import UserRecord
from src.application.services.auth_service import AuthService
from src.domain.enums.auth import Role


class RegisterUserUseCase:
    """Register a new user through the auth service."""

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
        """Register a new user account.

        Args:
            username: Unique login name.
            role: Role assigned to the new user.
            name: Human-readable display name.
            email: Optional email address.
            phone_number: Optional phone number.
            password: Plain-text password to hash before storage.

        Returns:
            The persisted user record.

        Raises:
            ValueError: If validation fails or the repository rejects the user.
        """
        return self._auth.register_user(
            username=username,
            role=role,
            name=name,
            email=email,
            phone_number=phone_number,
            password=password,
        )
