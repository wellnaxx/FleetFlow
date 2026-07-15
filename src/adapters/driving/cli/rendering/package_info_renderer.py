"""CLI rendering for delivery-package summaries."""

from src.domain.entities.delivery_package import DeliveryPackage


def render_package_info(package: DeliveryPackage) -> str:
    """Return a human-readable description of the package.

    Args:
        package: Delivery package to render.

    Returns:
        Multi-line package summary for CLI display.
    """
    contact_info = (
        f"{package.customer.name} ({package.customer.contact.display_email()}, "
        f"{package.customer.contact.display_phone()})"
    )
    route_str = package.route_id if package.route_id else "Not assigned"
    arrival_str = (
        package.expected_arrival.strftime("%Y-%m-%d %H:%M") if package.expected_arrival else "Not assigned"
    )
    return (
        f"Package {package.package_id}: "
        f"{package.start_location} -> {package.end_location}, {package.weight:.1f}kg\n"
        f"Customer: {contact_info}\n"
        f"Assigned route: {route_str}\n"
        f"Expected arrival: {arrival_str}"
    )
