from datetime import datetime
from unittest.mock import patch

import pytest
import pytz

from kasa_exporter.utils.time_of_use_calc import TimeOfUseCalc


@pytest.fixture
def test_config():
    """Test configuration with different rates than production."""
    return {
        "season": {
            "summer": ["05-0", "10-01"],  # Example time range for the year
            "winter": ["10-02", "05-01"],  # Example time range for the year
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


@pytest.fixture
def calculator(test_config):
    """Create TimeOfUseCalc instance with test config."""
    return TimeOfUseCalc(test_config)


@patch("kasa_exporter.utils.time_of_use_calc.datetime")
def test_get_current_season_summer(mock_datetime, calculator):
    mock_datetime.now.return_value = datetime(2024, 6, 15)  # June 15
    season = calculator.get_current_season()
    assert season == "summer"


@patch("kasa_exporter.utils.time_of_use_calc.datetime")
def test_get_current_season_winter(mock_datetime, calculator):
    mock_datetime.now.return_value = datetime(2024, 12, 20)  # December 20
    season = calculator.get_current_season()
    assert season == "winter"


def test_get_rate_for_time_summer_off_peak(calculator):
    current_time = datetime(2024, 6, 15, 5, 0, tzinfo=pytz.UTC)  # June 15, 5:00 AM UTC
    rate = calculator.get_rate_for_time(current_time, "summer")
    assert rate == 0.11


def test_get_rate_for_time_summer_mid_peak(calculator):
    current_time = datetime(2024, 7, 10, 14, 0, tzinfo=pytz.UTC)  # July 10, 2:00 PM UTC
    rate = calculator.get_rate_for_time(current_time, "summer")
    assert rate == 0.19


def test_get_rate_for_time_summer_on_peak(calculator):
    current_time = datetime(2024, 8, 1, 16, 0, tzinfo=pytz.UTC)  # August 1, 4:00 PM UTC
    rate = calculator.get_rate_for_time(current_time, "summer")
    assert rate == 0.28


def test_get_rate_for_time_winter_off_peak(calculator):
    current_time = datetime(2024, 12, 20, 5, 0, tzinfo=pytz.UTC)  # December 20, 5:00 AM UTC
    rate = calculator.get_rate_for_time(current_time, "winter")
    assert rate == 0.1


def test_get_rate_for_time_winter_mid_peak(calculator):
    current_time = datetime(2024, 1, 10, 13, 0, tzinfo=pytz.UTC)  # January 10, 1:00 PM UTC
    rate = calculator.get_rate_for_time(current_time, "winter")
    assert rate == 0.17


def test_get_rate_for_time_winter_on_peak(calculator):
    current_time = datetime(2024, 1, 15, 15, 0, tzinfo=pytz.UTC)  # January 15, 3:00 PM UTC
    rate = calculator.get_rate_for_time(current_time, "winter")
    assert rate == 0.25


@patch("kasa_exporter.utils.time_of_use_calc.datetime")
def test_calc_rate(mock_datetime, calculator):
    mock_datetime.now.return_value = datetime(2024, 6, 15, 5, 0)  # June 15, 5:00 AM UTC
    mock_datetime.now.return_value = mock_datetime.now.return_value.replace(tzinfo=pytz.UTC)
    cost = calculator.calc_rate(2000)  # 2000 watts
    assert abs(cost - 0.22) < 1e-6  # pytest style comparison instead of assertAlmostEqual
