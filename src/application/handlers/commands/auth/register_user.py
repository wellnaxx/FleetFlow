"""Command handler for administrative user registration."""

from src.application.commands.auth.register_user import RegisterUserCommand
from src.application.models.user_record import UserRecord
from src.application.use_cases.auth.register_user import RegisterUserUseCase


class RegisterUserCommandHandler:
    """Adapt a registration command to the user-registration workflow."""

    def __init__(self, use_case: RegisterUserUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized account-registration workflow to invoke.
        """
        self._use_case = use_case

    def handle(self, command: RegisterUserCommand) -> UserRecord:
        """Register the requested user account.

        Args:
            command: Account identity, profile, role, and initial password.

        Returns:
            Persisted user record produced by the use case.

        Raises:
            Exception: Propagates authorization, registration, validation,
                persistence, and other failures raised by the use case.
        """
        return self._use_case.execute(
            username=command.username,
            role=command.role,
            name=command.name,
            email=command.email,
            phone_number=command.phone_number,
            password=command.password,
        )
