"""Static map data used for route validation and distance calculation."""

from typing import ClassVar

from src.domain.value_objects.location_code import LocationCode


class Map:
    """Lookup service for supported city codes and intercity distances."""

    _locations: ClassVar[tuple[LocationCode, ...]] = (
        LocationCode("SYD"),
        LocationCode("MEL"),
        LocationCode("ADL"),
        LocationCode("ASP"),
        LocationCode("BRI"),
        LocationCode("DAR"),
        LocationCode("PER"),
    )

    _distances: ClassVar[dict[LocationCode, dict[LocationCode, int]]] = {
        LocationCode("SYD"): {
            LocationCode("MEL"): 877,
            LocationCode("ADL"): 1376,
            LocationCode("ASP"): 2762,
            LocationCode("BRI"): 909,
            LocationCode("DAR"): 3935,
            LocationCode("PER"): 4016,
        },
        LocationCode("MEL"): {
            LocationCode("SYD"): 877,
            LocationCode("ADL"): 725,
            LocationCode("ASP"): 2255,
            LocationCode("BRI"): 1765,
            LocationCode("DAR"): 3752,
            LocationCode("PER"): 3509,
        },
        LocationCode("ADL"): {
            LocationCode("SYD"): 1376,
            LocationCode("MEL"): 725,
            LocationCode("ASP"): 1530,
            LocationCode("BRI"): 1927,
            LocationCode("DAR"): 3027,
            LocationCode("PER"): 2785,
        },
        LocationCode("ASP"): {
            LocationCode("SYD"): 2762,
            LocationCode("MEL"): 2255,
            LocationCode("ADL"): 1530,
            LocationCode("BRI"): 2993,
            LocationCode("DAR"): 1497,
            LocationCode("PER"): 2481,
        },
        LocationCode("BRI"): {
            LocationCode("SYD"): 909,
            LocationCode("MEL"): 1765,
            LocationCode("ADL"): 1927,
            LocationCode("ASP"): 2993,
            LocationCode("DAR"): 3426,
            LocationCode("PER"): 4311,
        },
        LocationCode("DAR"): {
            LocationCode("SYD"): 3935,
            LocationCode("MEL"): 3752,
            LocationCode("ADL"): 3027,
            LocationCode("ASP"): 1497,
            LocationCode("BRI"): 3426,
            LocationCode("PER"): 4025,
        },
        LocationCode("PER"): {
            LocationCode("SYD"): 4016,
            LocationCode("MEL"): 3509,
            LocationCode("ADL"): 2785,
            LocationCode("ASP"): 2481,
            LocationCode("BRI"): 4311,
            LocationCode("DAR"): 4025,
        },
    }

    @classmethod
    def get_locations(cls) -> list[LocationCode]:
        """Return supported location codes.

        Returns:
            Copy of supported location codes.
        """
        return list(cls._locations)

    @classmethod
    def is_valid_location(cls, code: object) -> bool:
        """Return whether a location code is supported.

        Args:
            code: Location code to validate.

        Returns:
            True when the code is known to the map.
        """
        try:
            normalized = LocationCode(code)
        except (TypeError, ValueError):
            return False

        return normalized in cls._locations

    @classmethod
    def get_distance(cls, a: str | LocationCode, b: str | LocationCode) -> int:
        """Return the distance between two supported location codes.

        Args:
            a: First location code.
            b: Second location code.

        Returns:
            Distance in kilometres.

        Raises:
            ValueError: If no distance is known for the pair.
        """
        a = LocationCode(a)
        b = LocationCode(b)
        if a == b:
            return 0
        if b in cls._distances.get(a, {}):
            return cls._distances[a][b]
        if a in cls._distances.get(b, {}):
            return cls._distances[b][a]
        raise ValueError(f"No distance between {a} and {b}")
