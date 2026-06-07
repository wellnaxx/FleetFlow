from enum import StrEnum


class PackageDetachmentReason(StrEnum):
    """Reasons for detaching a package from a delivery route."""

    PACKAGE_REMOVED = "PACKAGE_REMOVED"
    ROUTE_REMOVED = "ROUTE_REMOVED"
