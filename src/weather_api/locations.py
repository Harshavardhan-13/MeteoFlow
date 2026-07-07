from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Location:
    slug: str
    city: str
    state_code: str
    latitude: float
    longitude: float
    timezone: str


LOCATIONS: tuple[Location, ...] = (
    Location("new-york-ny", "New York", "NY", 40.7128, -74.0060, "America/New_York"),
    Location("chicago-il", "Chicago", "IL", 41.8781, -87.6298, "America/Chicago"),
    Location(
        "san-francisco-ca",
        "San Francisco",
        "CA",
        37.7749,
        -122.4194,
        "America/Los_Angeles",
    ),
    Location(
        "las-vegas-nv",
        "Las Vegas",
        "NV",
        36.1699,
        -115.1398,
        "America/Los_Angeles",
    ),
    Location(
        "college-park-md",
        "College Park",
        "MD",
        38.9897,
        -76.9378,
        "America/New_York",
    ),
    Location(
        "washington-dc",
        "Washington",
        "DC",
        38.9072,
        -77.0369,
        "America/New_York",
    ),
)


def get_location(slug: str) -> Location:
    for location in LOCATIONS:
        if location.slug == slug:
            return location
    raise KeyError(f"Unknown location: {slug}")

