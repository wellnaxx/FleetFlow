from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.application.use_cases.packages.view_package import ViewPackageUseCase


class Container:
    def __init__(
        self,
        create_package_use_case: CreatePackageUseCase,
        view_package_use_case: ViewPackageUseCase,
        view_all_packages_use_case: ViewAllPackagesUseCase,
    ) -> None:
        self.create_package_use_case = create_package_use_case
        self.view_package_use_case = view_package_use_case
        self.view_all_packages_use_case = view_all_packages_use_case
