"""CLI command for registering users."""

import getpass

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_passwords
from src.application.commands.auth.register_user import REGISTER_USER, RegisterUserCommand
from src.domain.enums.auth import Role


class AuthRegisterUser(CommandBusCommand):
    """Register employee or manager users from CLI input.

    Usage:
        registeruser: prompts for all fields.
        registeruser <username> <role> <name> [email] [phone]: hybrid mode.
    """

    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Collect account details and dispatch a registration command.

        Returns:
            CLI confirmation text for the created user.

        Raises:
            PermissionError: If the caller lacks user administration permission.
            ValueError: If the argument count, role, or password confirmation
                is invalid.
            RegistrationInvalidUsernameError: If the username is invalid.
            RegistrationUsernameAlreadyExistsError: If the username already
                exists.
            RegistrationPasswordCriteriaNotMetError: If the initial password
                fails policy validation.
            DatabaseError: If account persistence fails.
        """
        if len(self.params) > 5:
            raise ValueError("Usage: registeruser <username> <role> <name> [email] [phone].")

        p = self.params
        username = p[0] if len(p) >= 1 else input("Username: ")
        role_s = (p[1] if len(p) >= 2 else input("Role [employee/manager]: ")).strip().lower()
        name = (p[2] if len(p) >= 3 else input("Full name: ")).strip()
        email = (p[3] if len(p) >= 4 else input("Email (optional): ")).strip()
        phone = (p[4] if len(p) >= 5 else input("Phone (optional, AU 04xxxxxxxx): ")).strip()

        if role_s.startswith("man"):
            role = Role.MANAGER
        elif role_s.startswith("emp"):
            role = Role.EMPLOYEE
        else:
            raise ValueError("Role must be 'employee' or 'manager'.")

        password = getpass.getpass("Temporary password: ")
        confirm = getpass.getpass("Confirm password: ")
        validate_passwords(password, confirm)

        rec = self.command_bus.dispatch(
            key=REGISTER_USER,
            command=RegisterUserCommand(
                username=username,
                role=role,
                name=name,
                email=email,
                phone_number=phone,
                password=password,
            ),
        )

        return f"Created {rec.role} user '{rec.username}' (id={rec.user_id})."
