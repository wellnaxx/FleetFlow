from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.application.services.authorization import requires
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.domain.enums.auth import Permission


class ViewAllPackages(UseCaseCommand[ViewAllPackagesUseCase]):
    @requires(Permission.PACKAGE_VIEW_ALL)
    def execute(self) -> str:
        packages = self._use_case.execute()
        return "\n\n".join(package.info() for package in packages) if packages else "No packages."
