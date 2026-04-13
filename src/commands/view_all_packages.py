from src.commands.base_command.base_command import BaseCommand


class ViewAllPackages(BaseCommand):
    def execute(self) -> str:
        packages = self._app_data.view_all_packages()
        return "\n\n".join(package.info() for package in packages) if packages else "No packages."
