"""Use case for listing fleet trucks."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.truck import Truck
from src.domain.enums.auth import Permission
from src.ports.output.vehicle_manager import VehicleManagerPort


class ViewAllTrucksUseCase(AuthorizedUseCase[list[Truck]]):
    """List all trucks managed by the vehicle manager."""

    def __init__(self, vehicles: VehicleManagerPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            vehicles: Vehicle manager used to list fleet state.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._vehicles = vehicles

    @requires(Permission.TRUCK_VIEW)
    def execute(self) -> list[Truck]:
        """Return the current fleet listing.

        Returns:
            Trucks currently known to the vehicle manager.
        """
        return self._vehicles.list_fleet()
