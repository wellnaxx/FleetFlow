"""Command handler for administrative password resets."""

from src.application.commands.auth.reset_password import ResetUserPasswordCommand
from src.application.use_cases.auth.reset_password import ResetPasswordUseCase


class ResetUserPasswordCommandHandler:
    """Adapt a password-reset command to the administrator workflow."""

    def __init__(self, use_case: ResetPasswordUseCase) -> None:
        """Initialize the handler with the password-reset use case.

        Args:
            use_case: Workflow that authorizes and performs password resets.
        """
        self._use_case = use_case

    def execute(self, command: ResetUserPasswordCommand) -> None:
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
