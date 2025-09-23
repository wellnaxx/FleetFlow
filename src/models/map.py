class Map:
    _locations = ["SYD", "MEL", "ADL", "ASP", "BRI", "DAR", "PER"]

    _distances = {
        "SYD": {"MEL": 877, "ADL": 1376, "ASP": 2762, "BRI": 909, "DAR": 3935, "PER": 4016},
        "MEL": {"SYD": 877, "ADL": 725, "ASP": 2255, "BRI": 1765, "DAR": 3752, "PER": 3509},
        "ADL": {"SYD": 1376, "MEL": 725, "ASP": 1530, "BRI": 1927, "DAR": 3027, "PER": 2785},
        "ASP": {"SYD": 2762, "MEL": 2255, "ADL": 1530, "BRI": 2993, "DAR": 1497, "PER": 2481},
        "BRI": {"SYD": 909, "MEL": 1765, "ADL": 1927, "ASP": 2993, "DAR": 3426, "PER": 4311},
        "DAR": {"SYD": 3935, "MEL": 3752, "ADL": 3027, "ASP": 1497, "BRI": 3426, "PER": 4025},
        "PER": {"SYD": 4016, "MEL": 3509, "ADL": 2785, "ASP": 2481, "BRI": 4311, "DAR": 4025},
    }

    @classmethod
    def get_locations(cls):
        return list(cls._locations)

    @classmethod
    def is_valid_location(cls, code: str) -> bool:
        return code in cls._locations

    @classmethod
    def get_distance(cls, a: str, b: str) -> int:
        if a == b:
            return 0
        if b in cls._distances.get(a, {}):
            return cls._distances[a][b]
        if a in cls._distances.get(b, {}):
            return cls._distances[b][a]
        raise ValueError(f"No distance between {a} and {b}")
