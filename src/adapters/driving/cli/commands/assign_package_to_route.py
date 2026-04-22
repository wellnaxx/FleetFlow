from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_count
from src.application.services.authorization_service import requires
from src.application.use_cases.routes.assign_packages_to_route import AssignPackagesToRouteUseCase
from src.domain.enums.auth import Permission


class AssignPackageToRoute(UseCaseCommand[AssignPackagesToRouteUseCase]):
    """Attach a package to a route subject to capacity/range constraints.

    Args:
        route_id: Target route id.
        package_id: Package to assign.
    Raises:
        ValueError: If not found or constraints fail.
    """

    mutates_state = True

    @requires(Permission.ROUTE_ASSIGN_PACKAGE)
    def execute(self) -> str:
        validate_params_count(self._params, 2)

        route_id = try_parse_int(self._params[0])
        package_ids = [try_parse_int(pid) for pid in self._params[1:]]

        result = self._use_case.execute(route_id, package_ids)

        success_lines = [
            f"Assigned package {s.package_id} to route {s.route_id}. ETA: {s.eta_text}"
            for s in result.successes
        ]

        error_lines = [e.message for e in result.errors]

        parts: list[str] = []
        if success_lines:
            parts.append("\n".join(success_lines))
        if error_lines:
            parts.append("Failed:\n- " + "\n- ".join(error_lines))

        return "\n\n".join(parts)
