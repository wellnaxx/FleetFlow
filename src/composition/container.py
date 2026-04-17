from src.application.use_cases.packages.create_package import CreatePackageUseCase


class Container:
    def __init__(self, create_package_use_case: CreatePackageUseCase) -> None:
        self.create_package_use_case = create_package_use_case
