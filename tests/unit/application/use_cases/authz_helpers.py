from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.users.employee import Employee
from src.domain.entities.users.manager import Manager


def manager_authz() -> AuthorizationService:
    """Return authorization state that grants every application permission."""
    return AuthorizationService(Manager(user_id=1, name="Test Manager"))


def employee_authz() -> AuthorizationService:
    """Return authorization state for a regular employee."""
    return AuthorizationService(Employee(user_id=2, name="Test Employee"))
