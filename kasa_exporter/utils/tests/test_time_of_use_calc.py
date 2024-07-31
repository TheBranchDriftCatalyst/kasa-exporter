import unittest
from datetime import datetime
from unittest.mock import patch
import pytz

from kasa_exporter.utils.time_of_use_calc import TimeOfUseCalc

TIME_OF_USE_CONFIG = {
    "season": {
        "summer": ["05-0", "10-01"],  # Example time range for the year
        "winter": ["10-02", "05-01"],  # Example time range for the year
        # Add other seasons as needed
    },
    "summer": {
        "rate": {
            "off_peak": 0.11,
            "mid_peak": 0.19,
            "on_peak": 0.28,
        },
        # Time ranges for the day
        "off_peak": [("19:00", "13:00"), ("21:00", "23:59")],
        "mid_peak": [("07:00", "15:00"), ("19:00", "21:00")],
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

class TestTimeOfUseCalc(unittest.TestCase):
    def setUp(self):
        self.calculator = TimeOfUseCalc(TIME_OF_USE_CONFIG)

    @patch("kasa_exporter.utils.time_of_use_calc.datetime")
    def test_get_current_season_summer(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2024, 6, 15)  # June 15
        season = self.calculator.get_current_season()
        self.assertEqual(season, "summer")

    @patch("kasa_exporter.utils.time_of_use_calc.datetime")
    def test_get_current_season_winter(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2024, 12, 20)  # December 20
        season = self.calculator.get_current_season()
        self.assertEqual(season, "winter")

    def test_get_rate_for_time_summer_off_peak(self):
        current_time = datetime(
            2024, 6, 15, 5, 0, tzinfo=pytz.UTC
        )  # June 15, 5:00 AM UTC
        rate = self.calculator.get_rate_for_time(current_time, "summer")
        self.assertEqual(rate, 0.11)

    def test_get_rate_for_time_summer_mid_peak(self):
        current_time = datetime(
            2024, 7, 10, 14, 0, tzinfo=pytz.UTC
        )  # July 10, 2:00 PM UTC
        rate = self.calculator.get_rate_for_time(current_time, "summer")
        self.assertEqual(rate, 0.19)

    def test_get_rate_for_time_summer_on_peak(self):
        current_time = datetime(
            2024, 8, 1, 16, 0, tzinfo=pytz.UTC
        )  # August 1, 4:00 PM UTC
        rate = self.calculator.get_rate_for_time(current_time, "summer")
        self.assertEqual(rate, 0.28)

    def test_get_rate_for_time_winter_off_peak(self):
        current_time = datetime(
            2024, 12, 20, 5, 0, tzinfo=pytz.UTC
        )  # December 20, 5:00 AM UTC
        rate = self.calculator.get_rate_for_time(current_time, "winter")
        self.assertEqual(rate, 0.10)

    def test_get_rate_for_time_winter_mid_peak(self):
        current_time = datetime(
            2024, 1, 10, 13, 0, tzinfo=pytz.UTC
        )  # January 10, 1:00 PM UTC
        rate = self.calculator.get_rate_for_time(current_time, "winter")
        self.assertEqual(rate, 0.17)

    def test_get_rate_for_time_winter_on_peak(self):
        current_time = datetime(
            2024, 1, 15, 15, 0, tzinfo=pytz.UTC
        )  # January 15, 3:00 PM UTC
        rate = self.calculator.get_rate_for_time(current_time, "winter")
        self.assertEqual(rate, 0.25)

    @patch("kasa_exporter.utils.time_of_use_calc.datetime")
    def test_calculate_rate_for_current_usage(self, mock_datetime):
        mock_datetime.now.return_value = datetime(
            2024, 6, 15, 5, 0
        )  # June 15, 5:00 AM UTC
        mock_datetime.now.return_value = mock_datetime.now.return_value.replace(
            tzinfo=pytz.UTC
        )
        cost = self.calculator.calculate_rate_for_current_usage(2000)  # 1000 watts
        self.assertAlmostEqual(cost, 0.22, places=6)


if __name__ == "__main__":
    unittest.main()
