import getpass

from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.application.services.authorization import requires
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.domain.enums.auth import Role
from src.domain.enums.auth import Permission


class AuthRegisterUser(UseCaseCommand[RegisterUserUseCase]):
    """
    Usage:
      registeruser                                  # prompts for all fields
      registeruser <username> <role> <name> [email] [phone]  # hybrid mode
    Roles: 'employee' or 'manager'
    """

    @requires(Permission.ADMIN_USER)
    def execute(self) -> str:
        # Gather inputs (use prompts for anything missing)
        p = self._params
        username = (p[0] if len(p) >= 1 else input("Username: ")).strip().lower()
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

        # Prompt for password (with confirmation)
        password = getpass.getpass("Temporary password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise ValueError("Passwords do not match.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")

        rec = self._use_case.execute(
            username=username,
            role=role,
            name=name,
            email=email,
            phone_number=phone,
            password=password,
        )
        return f"Created {rec.role} user '{rec.username}' (id={rec.user_id})."
