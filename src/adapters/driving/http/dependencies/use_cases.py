from typing import Annotated

from fastapi import Depends

from src.adapters.driving.http.dependencies.auth import AuthenticatedPrincipal, get_current_user
from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.composition.runtime import get_auth_service, get_container


def get_login_use_case() -> LoginUseCase:
    return get_container().auth_cases.login


def get_register_user_use_case(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RegisterUserUseCase:
    return RegisterUserUseCase(auth=auth_service, authz=principal.authz)


def get_view_all_customers_use_case() -> ViewAllCustomersUseCase:
    return get_container().customer_cases.view_all
