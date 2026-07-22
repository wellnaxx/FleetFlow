"""Minimal immutable package data used for route-load calculations."""

from dataclasses import dataclass

from src.domain.value_objects.location_code import LocationCode


@dataclass(frozen=True, slots=True)
class PackageLoad:
    """Describe the portion of a route over which package weight is carried.

    This value object deliberately excludes package identity, customer data,
    lifecycle status, and persistence metadata. It allows route-load policies
    and read projections to share the same calculation without constructing a
    complete delivery-package entity.

    Attributes:
        start_location: Route stop where the package begins contributing load.
        end_location: Later route stop where the package stops contributing load.
        weight: Package weight added to every traversed segment, in kilograms.
    """

    start_location: LocationCode
    end_location: LocationCode
    weight: float
