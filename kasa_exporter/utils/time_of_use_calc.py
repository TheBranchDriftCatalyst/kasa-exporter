from datetime import datetime
import os
import pytz

TIME_OF_USE_CONFIG = {
    "season": {
        "summer": ["06-01", "10-31"],  # SDG&E Summer: June 1 - October 31
        "winter": ["11-01", "05-31"],  # SDG&E Winter: November 1 - May 31
    },
    "summer": {
        "rate": {
            "super_off_peak": 0.314,  # $0.314/kWh - midnight to 6am every day
            "off_peak": 0.351,        # $0.351/kWh - all other hours except on-peak
            "on_peak": 0.634,         # $0.634/kWh - 4pm to 9pm every day
        },
        # Time ranges for the day (SDG&E TOU-ELEC plan)
        "super_off_peak": [("00:00", "06:00")],
        "off_peak": [("06:00", "16:00"), ("21:00", "23:59")],
        "on_peak": [("16:00", "21:00")],  # 4pm to 9pm
    },
    "winter": {
        "rate": {
            "super_off_peak": 0.314,  # $0.314/kWh - midnight to 6am every day
            "off_peak": 0.351,        # $0.351/kWh - all other hours except on-peak
            "on_peak": 0.634,         # $0.634/kWh - 4pm to 9pm every day
        },
        # Same time ranges year-round for SDG&E TOU-ELEC
        "super_off_peak": [("00:00", "06:00")],
        "off_peak": [("06:00", "16:00"), ("21:00", "23:59")],
        "on_peak": [("16:00", "21:00")],  # 4pm to 9pm
    },
}


class TimeOfUseCalc:
    def __init__(self, config: dict, timezone: str = None):
        self.config = config
        # Allow timezone override via environment variable or constructor
        self.timezone = timezone or os.getenv("TZ", "America/Los_Angeles")

    def get_current_season(self) -> str:
        """Determine the current season based on the date."""
        today = datetime.now().strftime("%m-%d")
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
                if start <= current_time_str <= end:
                    return period
        return "off_peak"
    
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

    def calc_rate(self, current_consumption: float) -> float:
        """Calculate the instantaneous cost of the current consumption."""
        self.current_season = self.get_current_season()
        current_time = datetime.now(pytz.timezone("UTC")).astimezone(
            pytz.timezone(self.timezone)
        )
        rate = self.get_rate_for_time(current_time, self.current_season)
        return round((current_consumption / 1000) * rate, 6)
