from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.services.authorization_service import AuthorizationService
from src.domain.enums.auth import Role


def principal(user_id: int, username: str, role: Role = Role.MANAGER) -> CurrentUserPrincipal:
    """Return a current-user principal for auth-related tests."""
    return CurrentUserPrincipal(
        user_id=user_id,
        username=username,
        name=username.title(),
        email="",
        phone_number="",
        role=role,
    )


def manager_authz() -> AuthorizationService:
    """Return authorization state that grants every application permission."""
    return AuthorizationService(principal(1, "manager", Role.MANAGER))


def employee_authz() -> AuthorizationService:
    """Return authorization state for a regular employee."""
    return AuthorizationService(principal(2, "employee", Role.EMPLOYEE))
