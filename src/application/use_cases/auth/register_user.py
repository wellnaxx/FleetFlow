"""Use case for registering a new user."""

from src.application.models.user_record import UserRecord
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission, Role


class RegisterUserUseCase(AuthorizedUseCase[UserRecord]):
    """Register a new user through the auth service."""

    def __init__(self, auth: AuthService, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            auth: Authentication service used to create users.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._auth = auth

    @requires(Permission.ADMIN_USER)
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
