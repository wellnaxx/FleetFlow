"""Command handler for user authentication."""

from src.application.commands.auth.login import LoginCommand
from src.application.results.login_result import LoginResult
from src.application.use_cases.auth.login import LoginUseCase


class LoginCommandHandler:
    """Adapt a login command to the authentication workflow."""

    def __init__(self, use_case: LoginUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authentication workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, command: LoginCommand) -> LoginResult:
        """Authenticate the supplied credentials.

        Args:
            command: Username and plain-text password to verify.

        Returns:
            Authentication result produced by the use case.

        Raises:
            Exception: Propagates authentication, validation, persistence, and
                other failures raised by the use case.
        """
        return self._use_case.execute(command.username, command.password)
