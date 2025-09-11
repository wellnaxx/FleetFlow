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
        return cls._locations.copy()

    @classmethod
    def get_distance(cls, city_a, city_b):
        city_a = city_a.strip().upper()
        city_b = city_b.strip().upper()

        if city_a not in cls._locations:
            raise ValueError(f"Invalid location: {city_a}")
        if city_b not in cls._locations:
            raise ValueError(f"Invalid location: {city_b}")
        if city_a == city_b:
            raise ValueError("Invalid input. First and second location cannot be the same")
        return cls._distances[city_a][city_b]
        
    @classmethod
    def is_valid_location(cls, location):
        return location.strip().upper() in cls._locations
        