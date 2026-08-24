"""Query-bus-backed CLI command for finding suitable trucks for a route."""

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.queries.routes.find_suitable_trucks_for_route import (
    FIND_SUITABLE_TRUCKS_FOR_ROUTE,
    FindSuitableTrucksForRouteQuery,
)


class FindSuitableTrucksForRoute(QueryBusCommand):
    """Render available truck candidates for a route."""

    def execute(self) -> str:
        """List suitable trucks for the requested route.

        Returns:
            CLI table text, or a no-match message.

        Raises:
            PermissionError: If the caller lacks truck-search permission.
            ValueError: If the route id is invalid or missing.
            NotFoundError: If the route does not exist.
            DatabaseError: If route or vehicle retrieval fails.
        """
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0], "route_id")
        trucks = self.query_bus.dispatch(
            key=FIND_SUITABLE_TRUCKS_FOR_ROUTE,
            query=FindSuitableTrucksForRouteQuery(route_id=route_id),
        )
        if not trucks:
            return "No suitable trucks found."
        lines = ["ID | Name   | Capacity | Max Range | Current Location"]
        lines.extend(
            f"{t.vehicle_id} | {t.name} | {t.capacity} kg | {t.max_range} km | {t.current_location}"
            for t in trucks
        )
        return "\n".join(lines)
