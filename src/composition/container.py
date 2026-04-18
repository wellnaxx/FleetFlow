from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.packages.view_package import ViewPackageUseCase


class Container:
    def __init__(
        self, create_package_use_case: CreatePackageUseCase, view_package_use_case: ViewPackageUseCase
    ) -> None:
        self.create_package_use_case = create_package_use_case
        self.view_package_use_case = view_package_use_case
