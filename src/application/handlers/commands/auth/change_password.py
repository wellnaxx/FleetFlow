"""Command handlers for self-service and administrative password updates."""

from src.application.commands.auth.change_password import ChangeOwnPasswordCommand
from src.application.commands.auth.reset_password import ResetUserPasswordCommand
from src.application.use_cases.auth.change_password import ChangePasswordUseCase


class ChangeOwnPasswordCommandHandler:
    """Adapt a self-service password command to the current password workflow."""

    def __init__(self, use_case: ChangePasswordUseCase) -> None:
        """Initialize the handler with the existing password use case.

        Args:
            use_case: Workflow that verifies and changes the current user's
                password.
        """
        self._use_case = use_case

    def handle(self, command: ChangeOwnPasswordCommand) -> None:
        """Change the authenticated principal's password.

        Args:
            command: Current and replacement passwords to pass to the workflow.

        Raises:
            Exception: Propagates authorization, authentication, validation,
                persistence, and other failures raised by the use case.
        """
        self._use_case.execute_current_user(
            new_password=command.new_password,
            old_password=command.current_password,
        )


class ResetUserPasswordCommandHandler:
    """Adapt an administrative reset command to the current password workflow."""

    def __init__(self, use_case: ChangePasswordUseCase) -> None:
        """Initialize the handler with the existing password use case.

        Args:
            use_case: Workflow that authorizes and performs password resets.
        """
        self._use_case = use_case

    def handle(self, command: ResetUserPasswordCommand) -> None:
        """Reset the target user's password.

        Args:
            command: Target username and replacement password.

        Raises:
            Exception: Propagates authorization, validation, persistence, and
                other failures raised by the use case.
        """
        self._use_case.execute(
            username=command.username,
            new_password=command.new_password,
        )
