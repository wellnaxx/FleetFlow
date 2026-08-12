"""Command handler for self-service password changes."""

from src.application.commands.auth.change_password import ChangeOwnPasswordCommand
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
        self._use_case.execute(
            current_password=command.current_password,
            new_password=command.new_password,
        )
