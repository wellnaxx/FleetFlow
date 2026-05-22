from typing import Annotated

from fastapi import Depends

from src.adapters.driving.http.dependencies.auth import AuthenticatedPrincipal, get_current_user
from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.application.use_cases.packages.view_package import ViewPackageUseCase
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from src.composition.container import Container
from src.composition.runtime import get_auth_service, get_container


def get_login_use_case() -> LoginUseCase:
    return get_container().auth_cases.login


def get_register_user_use_case(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RegisterUserUseCase:
    return RegisterUserUseCase(auth=auth_service, authz=principal.authz)


def get_change_password_use_case(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ChangePasswordUseCase:
    return ChangePasswordUseCase(auth=auth_service, authz=principal.authz)


def get_view_all_customers_use_case(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> ViewAllCustomersUseCase:
    return ViewAllCustomersUseCase(container.customer_repo, authz=principal.authz)


def get_create_package_use_case(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> CreatePackageUseCase:
    return CreatePackageUseCase(container.customer_service, container.package_repo, authz=principal.authz)


def get_view_package_use_case(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> ViewPackageUseCase:
    return ViewPackageUseCase(container.package_repo, authz=principal.authz)


def get_view_all_packages_use_case(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> ViewAllPackagesUseCase:
    return ViewAllPackagesUseCase(container.package_repo, authz=principal.authz)


def get_view_unassigned_packages_use_case(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> ViewUnassignedPackagesUseCase:
    return ViewUnassignedPackagesUseCase(container.package_repo, authz=principal.authz)


def get_remove_package_use_case(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> RemovePackageUseCase:
    return RemovePackageUseCase(container.package_repo, authz=principal.authz)