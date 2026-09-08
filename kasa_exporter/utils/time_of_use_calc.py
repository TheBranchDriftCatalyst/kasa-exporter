import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytz
import yaml


def load_tou_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load Time of Use configuration from YAML file.

    Args:
        config_path: Path to config file. If None, uses TOU_CONFIG_PATH env var
                    or defaults to etc/time_of_use_config.yaml

    Returns:
        dict: TOU configuration with normalized time ranges (tuples instead of lists)
    """
    if config_path is None:
        config_path = os.getenv("TOU_CONFIG_PATH")
        if config_path is None:
            # Default to etc/time_of_use_config.yaml relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "etc" / "time_of_use_config.yaml"

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"TOU config file not found: {config_path}")

    with config_path.open() as f:
        config = yaml.safe_load(f)

    # Normalize time ranges from lists to tuples (for consistency with old format)
    for season in ["summer", "winter"]:
        if season in config:
            for period in ["super_off_peak", "off_peak", "on_peak"]:
                if period in config[season]:
                    config[season][period] = [
                        tuple(time_range) for time_range in config[season][period]
                    ]

    return config


# Default config (fallback if file loading fails)
DEFAULT_TIME_OF_USE_CONFIG = {
    "season": {
        "summer": ["06-01", "10-31"],
        "winter": ["11-01", "05-31"],
    },
    "summer": {
        "rate": {
            "super_off_peak": 0.314,
            "off_peak": 0.351,
            "on_peak": 0.634,
        },
        "super_off_peak": [("00:00", "06:00")],
        "off_peak": [("06:00", "16:00"), ("21:00", "23:59")],
        "on_peak": [("16:00", "21:00")],
    },
    "winter": {
        "rate": {
            "super_off_peak": 0.314,
            "off_peak": 0.351,
            "on_peak": 0.634,
        },
        "super_off_peak": [("00:00", "06:00")],
        "off_peak": [("06:00", "16:00"), ("21:00", "23:59")],
        "on_peak": [("16:00", "21:00")],
    },
}


class TimeOfUseCalc:
    def __init__(self, config: dict[str, Any] | None = None, timezone: str | None = None):
        """
        Initialize TimeOfUseCalc with config and timezone.

        Args:
            config: TOU configuration dict. If None, loads from YAML file.
            timezone: Timezone string (e.g., "America/Los_Angeles")
        """
        if config is None:
            try:
                config = load_tou_config()
            except (FileNotFoundError, yaml.YAMLError) as e:
                # Fall back to default config if file can't be loaded
                print(f"Warning: Failed to load TOU config, using defaults: {e}")
                config = DEFAULT_TIME_OF_USE_CONFIG

        self.config: dict[str, Any] = config
        # Allow timezone override via environment variable or constructor
        self.timezone = timezone or os.getenv("TZ", "America/Los_Angeles")

    def get_current_season(self) -> str:
        """Determine the current season based on the date."""
        today = datetime.now(tz=pytz.timezone(self.timezone)).strftime("%m-%d")
        for season, date_range in self.config["season"].items():
            start, end = date_range
            # Handle the case where the season spans across the year-end
            if start <= today <= end or (start > end and (today >= start or today <= end)):
                return season
        # Default season if not in any range (shouldn't happen with proper config)
        return "summer"

    def get_rate_name(self, current_time: datetime, season: str) -> str:
        """Determine the rate name based on the current time and time ranges."""
        current_time_str = current_time.strftime("%H:%M")
        for period, ranges in self.config[season].items():
            if period == "rate":
                continue
            for start, end in ranges:
                if start <= current_time_str < end or (end == "23:59" and current_time_str == end):
                    return period
        return "off_peak"

    def get_rate_for_time(self, current_time: datetime, season: str) -> float:
        """Determine the rate based on the current time and time ranges."""
        current_time_str = current_time.strftime("%H:%M")
        for period, ranges in self.config[season].items():
            if period == "rate":
                continue
            for start, end in ranges:
                if start <= current_time_str < end or (end == "23:59" and current_time_str == end):
                    return self.config[season]["rate"][period]
        return self.config[season]["rate"]["off_peak"]  # Default rate if not in any range

    def calc_rate(self, current_consumption: float) -> float:
        """Calculate the instantaneous cost of the current consumption."""
        self.current_season = self.get_current_season()
        current_time = datetime.now(pytz.timezone("UTC")).astimezone(pytz.timezone(self.timezone))
        rate = self.get_rate_for_time(current_time, self.current_season)
        return round((current_consumption / 1000) * rate, 6)

    def seconds_until_rate_change(self, now: datetime | None = None) -> float:
        """Time to the next configured period start in the utility's timezone."""
        zone = pytz.timezone(self.timezone)
        now = (now or datetime.now(tz=pytz.UTC)).astimezone(zone)
        candidates = []
        for offset in range(3):
            date = now.date() + timedelta(days=offset)
            date_text = date.strftime("%m-%d")
            season = next(
                name
                for name, (start, end) in self.config["season"].items()
                if start <= date_text <= end
                or (start > end and (date_text >= start or date_text <= end))
            )
            for name, ranges in self.config[season].items():
                if name == "rate":
                    continue
                for start, _ in ranges:
                    hour, minute = map(int, start.split(":"))
                    boundary = zone.localize(
                        datetime(date.year, date.month, date.day, hour, minute)  # noqa: DTZ001 - localize wall time below
                    )
                    if boundary > now:
                        candidates.append((boundary - now).total_seconds())
        return min(candidates)
