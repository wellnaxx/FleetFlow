from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand


class ViewUnassignedPackages(BaseCommand):
    """Return a list of packages not attached to any route."""

    def execute(self) -> str:
        packages = self._app_data.view_unassigned_packages()
        if not packages:
            return "No unassigned packages."
        return "\n\n".join(p.info() for p in packages)
