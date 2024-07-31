from datetime import datetime
import pytz

TIME_OF_USE_CONFIG = {
    "season": {
        "summer": ["06-01", "09-30"],  # Example time range for the year
        "winter": ["12-01", "02-28"],  # Example time range for the year
        # Add other seasons as needed
    },
    "summer": {
        "rate": {
            "off_peak": 0.11,
            "mid_peak": 0.19,
            "on_peak": 0.28,
        },
        # Time ranges for the day
        "off_peak": [("00:00", "13:00"), ("19:00", "00:00")],
        "mid_peak": [("13:00", "15:00")],
        "on_peak": [("15:00", "19:00")],
    },
    "winter": {
        "rate": {
            "off_peak": 0.10,
            "mid_peak": 0.17,
            "on_peak": 0.25,
        },
        "off_peak": [("00:00", "06:00"), ("20:00", "23:59")],
        "mid_peak": [("06:00", "14:00"), ("18:00", "20:00")],
        "on_peak": [("14:00", "18:00")],
    },
}


class TimeOfUseCalc:
    def __init__(self, config: dict):
        self.config = config

    def get_current_season(self) -> str:
        """Determine the current season based on the date."""
        today = datetime.now().strftime("%m-%d")
        for season, date_range in self.config["season"].items():
            start, end = date_range
            # Handle the case where the season spans across the year-end
            if start <= today <= end or (start > end and (today >= start or today <= end)):
                return season
        # Default season if not in any range
        return "summer"  # or whatever default season you prefer

    def get_rate_for_time(self, current_time: datetime, season: str) -> float:
        """Determine the rate based on the current time and time ranges."""
        current_time_str = current_time.strftime("%H:%M")
        for period, ranges in self.config[season].items():
            if period == "rate":
                continue
            for start, end in ranges:
                if start <= current_time_str <= end:
                    return self.config[season]["rate"][period]
        return self.config[season]["rate"][
            "off_peak"
        ]  # Default rate if not in any range

    def calculate_rate_for_current_usage(self, current_consumption: float) -> float:
        """Calculate the instantaneous cost of the current consumption."""
        self.current_season = self.get_current_season()
        current_time = datetime.now(pytz.timezone("UTC")).astimezone(
            pytz.timezone("America/Denver")
        )  # Adjust timezone as needed
        rate = self.get_rate_for_time(current_time, self.current_season)
        return (current_consumption / 1000) * rate
