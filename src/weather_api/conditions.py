from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Condition:
    label: str
    symbol: str


CONDITIONS: dict[int, Condition] = {
    0: Condition("Clear sky", "☀️"),
    1: Condition("Mainly clear", "🌤️"),
    2: Condition("Partly cloudy", "⛅"),
    3: Condition("Overcast", "☁️"),
    45: Condition("Fog", "🌫️"),
    48: Condition("Rime fog", "🌫️"),
    51: Condition("Light drizzle", "🌦️"),
    53: Condition("Moderate drizzle", "🌦️"),
    55: Condition("Dense drizzle", "🌧️"),
    56: Condition("Light freezing drizzle", "🌧️"),
    57: Condition("Dense freezing drizzle", "🌧️"),
    61: Condition("Slight rain", "🌦️"),
    63: Condition("Moderate rain", "🌧️"),
    65: Condition("Heavy rain", "🌧️"),
    66: Condition("Light freezing rain", "🌧️"),
    67: Condition("Heavy freezing rain", "🌧️"),
    71: Condition("Slight snowfall", "❄️"),
    73: Condition("Moderate snowfall", "❄️"),
    75: Condition("Heavy snowfall", "❄️"),
    77: Condition("Snow grains", "❄️"),
    80: Condition("Slight rain showers", "🌦️"),
    81: Condition("Moderate rain showers", "🌧️"),
    82: Condition("Violent rain showers", "🌧️"),
    85: Condition("Slight snow showers", "❄️"),
    86: Condition("Heavy snow showers", "❄️"),
    95: Condition("Thunderstorm", "⛈️"),
    96: Condition("Thunderstorm with slight hail", "⛈️"),
    99: Condition("Thunderstorm with heavy hail", "⛈️"),
}


def condition_for(code: int, is_day: bool) -> Condition:
    if code == 0 and not is_day:
        return Condition("Clear night", "🌙")
    return CONDITIONS.get(code, Condition("Unknown", "❔"))

