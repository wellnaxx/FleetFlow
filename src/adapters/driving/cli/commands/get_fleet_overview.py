"""CLI command for rendering the current fleet operations overview."""

from typing import Final

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_count
from src.adapters.driving.cli.rendering.fleet_overview_renderer import render_fleet_overview
from src.application.queries.fleet.get_fleet_overview import (
    GET_FLEET_OVERVIEW,
    GetFleetOverviewQuery,
)
from src.shared.validation import require_positive_int

DEFAULT_ACTIVE_ROUTE_LIMIT: Final[int] = 10


class GetFleetOverview(QueryBusCommand):
    """Parse overview options, execute the use case, and render its projection."""

    def execute(self) -> str:
        """Return the current fleet overview as CLI text.

        The optional positional argument controls the number of active routes
        included in the result. The registered query executor owns scoped
        authorization-event publication.

        Returns:
            Rendered fleet overview.

        Raises:
            ValueError: If more than one argument is supplied or the active
                route limit is not an integer from 1 through 100.
            PermissionError: If the current principal cannot view the fleet
                overview.
            ValidationError: If the application rejects the requested limit or
                generated overview data.
            RuntimeError: If overview persistence or projection fails.
        """
        validate_params_count(self.params, 0, 1)
        active_route_limit = (
            require_positive_int(
                try_parse_int(
                    self.params[0],
                    "active_route_limit",
                ),
                "active_route_limit",
            )
            if self.params
            else DEFAULT_ACTIVE_ROUTE_LIMIT
        )
        if active_route_limit > 100:
            raise ValueError("active_route_limit must be less than or equal to 100.")

        fleet_overview = self.query_bus.dispatch(
            key=GET_FLEET_OVERVIEW,
            query=GetFleetOverviewQuery(active_route_limit=active_route_limit),
        )

        return render_fleet_overview(fleet_overview)
