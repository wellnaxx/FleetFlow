from src.adapters.driven.persistence.application_data.customer_repository import (
    ApplicationDataCustomerRepository,
)
from src.adapters.driven.persistence.application_data.package_repository import ApplicationDataPackageRepository
from src.adapters.driven.persistence.json.user_store import UserStore
from src.adapters.driving.cli.command_factory import CommandFactory
from src.adapters.driving.cli.engine import Engine
from src.application.services.auth_service import AuthService
from src.application.services.customer_service import CustomerService
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.application.use_cases.packages.view_package import ViewPackageUseCase
from src.composition.container import Container
from src.core.application_data import ApplicationData
from src.domain.enums.auth import Role


def bootstrap_admin(auth: AuthService, store: UserStore) -> None:
    if not store.get("admin"):
        auth.register_user(
            username="admin",
            role=Role.MANAGER,
            name="Admin",
            email="",
            phone_number="",
            password="ChangeMe123!",
        )


def main() -> None:
    app_data = ApplicationData(current_user=None)

    try:
        import json
        import os

        if os.path.exists(app_data.AUTOSAVE_PATH):
            with open(app_data.AUTOSAVE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            app_data._apply_state(data)  # pyright: ignore[reportPrivateUsage]; transitional, still ugly
    except Exception:
        pass

    store = UserStore("users.json")
    auth = AuthService(store)
    bootstrap_admin(auth, store)

    customer_repo = ApplicationDataCustomerRepository(app_data)
    package_repo = ApplicationDataPackageRepository(app_data)
    customer_service = CustomerService(customer_repo)

    container = Container(
        create_package_use_case=CreatePackageUseCase(
            customer_service,
            packages=package_repo,
        ),
        view_package_use_case=ViewPackageUseCase(packages=package_repo),
        view_all_packages_use_case=ViewAllPackagesUseCase(packages=package_repo),
    )

    cmd_factory = CommandFactory(app_data, auth, container)
    Engine(cmd_factory, app_data, auth).start()


if __name__ == "__main__":
    main()
