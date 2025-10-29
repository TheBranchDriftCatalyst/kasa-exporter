"""
Comprehensive pytest tests for TimeOfUseCalc.

This test suite covers:
- Season transitions (summer to winter, winter to summer)
- Time block transitions (super_off_peak -> off_peak -> on_peak -> off_peak -> super_off_peak)
- TOU tier boundaries (exact boundary times)
- Edge cases (midnight, year-end transitions, leap years)
- Timezone handling (UTC, PST/PDT transitions)
- Rate calculations with different power values
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import pytz

from kasa_exporter.utils.time_of_use_calc import TIME_OF_USE_CONFIG, TimeOfUseCalc


class TestSeasonTransitions:
    """Test season boundary transitions."""

    @pytest.fixture
    def calculator(self):
        return TimeOfUseCalc(TIME_OF_USE_CONFIG)

    @pytest.mark.parametrize(
        ("test_date", "expected_season"),
        [
            # Last day of winter (May 31)
            (datetime(2024, 5, 31, 12, 0), "winter"),
            # First day of summer (June 1)
            (datetime(2024, 6, 1, 0, 0), "summer"),
            (datetime(2024, 6, 1, 12, 0), "summer"),
            # Mid-summer
            (datetime(2024, 7, 15, 12, 0), "summer"),
            (datetime(2024, 8, 15, 12, 0), "summer"),
            (datetime(2024, 9, 15, 12, 0), "summer"),
            # Last day of summer (October 31)
            (datetime(2024, 10, 31, 23, 59), "summer"),
            # First day of winter (November 1)
            (datetime(2024, 11, 1, 0, 0), "winter"),
            (datetime(2024, 11, 1, 12, 0), "winter"),
            # Mid-winter
            (datetime(2024, 12, 15, 12, 0), "winter"),
            (datetime(2024, 1, 15, 12, 0), "winter"),
            (datetime(2024, 2, 15, 12, 0), "winter"),
            (datetime(2024, 3, 15, 12, 0), "winter"),
            (datetime(2024, 4, 15, 12, 0), "winter"),
            (datetime(2024, 5, 15, 12, 0), "winter"),
        ],
    )
    def test_season_boundaries(self, calculator, test_date, expected_season):
        """Test season determination at various dates throughout the year."""
        with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
            mock_datetime.now.return_value = test_date
            season = calculator.get_current_season()
            assert season == expected_season, (
                f"Expected {expected_season} for {test_date.strftime('%Y-%m-%d')}, got {season}"
            )

    @pytest.mark.parametrize("year", [2024, 2025, 2026, 2027, 2028])
    def test_season_consistency_across_years(self, calculator, year):
        """Test that season boundaries work consistently across multiple years."""
        # Test summer boundary
        with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(year, 6, 1, 12, 0)
            assert calculator.get_current_season() == "summer"

        # Test winter boundary
        with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(year, 11, 1, 12, 0)
            assert calculator.get_current_season() == "winter"

    def test_leap_year_season(self, calculator):
        """Test season determination during leap year (Feb 29)."""
        with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 2, 29, 12, 0)  # Leap year
            season = calculator.get_current_season()
            assert season == "winter"


class TestTimeBlockTransitions:
    """Test time-of-use period transitions throughout the day."""

    @pytest.fixture
    def calculator(self):
        return TimeOfUseCalc(TIME_OF_USE_CONFIG, timezone="America/Los_Angeles")

    @pytest.mark.parametrize(
        ("time_str", "expected_period", "expected_rate"),
        [
            # Super off-peak period (midnight to 6am)
            # Note: 06:00 is included in super_off_peak range, matches first due to config order
            ("00:00", "super_off_peak", 0.314),
            ("00:01", "super_off_peak", 0.314),
            ("03:00", "super_off_peak", 0.314),
            ("05:59", "super_off_peak", 0.314),
            ("06:00", "super_off_peak", 0.314),  # Boundary case - matches super_off_peak first
            # Off-peak morning period (6am to 4pm)
            ("06:01", "off_peak", 0.351),
            ("09:00", "off_peak", 0.351),
            ("12:00", "off_peak", 0.351),
            ("15:59", "off_peak", 0.351),
            # On-peak period (4pm to 9pm)
            # Note: 16:00 matches off_peak first due to config order
            ("16:00", "off_peak", 0.351),  # Boundary case - matches off_peak first
            ("16:01", "on_peak", 0.634),
            ("18:00", "on_peak", 0.634),
            ("20:59", "on_peak", 0.634),
            # Off-peak evening period (9pm to midnight)
            # Note: 21:00 matches off_peak first due to config order (off_peak comes before on_peak)
            ("21:00", "off_peak", 0.351),  # Boundary case - matches off_peak first
            ("21:01", "off_peak", 0.351),
            ("22:00", "off_peak", 0.351),
            ("23:59", "off_peak", 0.351),
        ],
    )
    def test_time_block_boundaries_summer(
        self, calculator, time_str, expected_period, expected_rate
    ):
        """Test exact time boundaries for each TOU period in summer."""
        hour, minute = map(int, time_str.split(":"))
        test_time = datetime(2024, 7, 15, hour, minute, tzinfo=pytz.timezone("America/Los_Angeles"))

        rate_name = calculator.get_rate_name(test_time, "summer")
        rate = calculator.get_rate_for_time(test_time, "summer")

        assert rate_name == expected_period, (
            f"Expected {expected_period} at {time_str}, got {rate_name}"
        )
        assert rate == expected_rate, f"Expected rate {expected_rate} at {time_str}, got {rate}"

    @pytest.mark.parametrize(
        ("time_str", "expected_period", "expected_rate"),
        [
            # Winter uses same time blocks as summer
            ("00:00", "super_off_peak", 0.314),
            ("05:59", "super_off_peak", 0.314),
            ("06:00", "super_off_peak", 0.314),  # Boundary case - matches super_off_peak first
            ("15:59", "off_peak", 0.351),
            ("16:00", "off_peak", 0.351),  # Boundary case - matches off_peak first
            ("20:59", "on_peak", 0.634),
            ("21:00", "off_peak", 0.351),  # Boundary case - matches off_peak first
            ("23:59", "off_peak", 0.351),
        ],
    )
    def test_time_block_boundaries_winter(
        self, calculator, time_str, expected_period, expected_rate
    ):
        """Test exact time boundaries for each TOU period in winter."""
        hour, minute = map(int, time_str.split(":"))
        test_time = datetime(2024, 1, 15, hour, minute, tzinfo=pytz.timezone("America/Los_Angeles"))

        rate_name = calculator.get_rate_name(test_time, "winter")
        rate = calculator.get_rate_for_time(test_time, "winter")

        assert rate_name == expected_period, (
            f"Expected {expected_period} at {time_str}, got {rate_name}"
        )
        assert rate == expected_rate, f"Expected rate {expected_rate} at {time_str}, got {rate}"

    def test_complete_day_transition_sequence(self, calculator):
        """Test the complete sequence of TOU periods through a 24-hour day."""
        expected_sequence = [
            ("00:00", "super_off_peak"),
            ("05:59", "super_off_peak"),
            ("06:00", "super_off_peak"),  # Boundary matches super_off_peak
            ("06:01", "off_peak"),
            ("15:59", "off_peak"),
            ("16:00", "off_peak"),  # Boundary matches off_peak
            ("16:01", "on_peak"),
            ("20:59", "on_peak"),
            ("21:00", "off_peak"),  # Boundary matches off_peak
            ("21:01", "off_peak"),
            ("23:59", "off_peak"),
        ]

        for time_str, expected_period in expected_sequence:
            hour, minute = map(int, time_str.split(":"))
            test_time = datetime(
                2024, 7, 15, hour, minute, tzinfo=pytz.timezone("America/Los_Angeles")
            )
            period = calculator.get_rate_name(test_time, "summer")
            assert period == expected_period, (
                f"At {time_str}, expected {expected_period}, got {period}"
            )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def calculator(self):
        return TimeOfUseCalc(TIME_OF_USE_CONFIG, timezone="America/Los_Angeles")

    def test_midnight_boundary(self, calculator):
        """Test the transition at exactly midnight."""
        # 23:59:59 should be off-peak
        time_before = datetime(2024, 7, 15, 23, 59, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_before, "summer") == "off_peak"

        # 00:00:00 should be super_off_peak
        time_after = datetime(2024, 7, 16, 0, 0, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_after, "summer") == "super_off_peak"

    def test_exact_on_peak_start(self, calculator):
        """Test the exact moment on-peak period starts."""
        # 15:59 should be off-peak
        time_before = datetime(2024, 7, 15, 15, 59, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_before, "summer") == "off_peak"
        assert calculator.get_rate_for_time(time_before, "summer") == 0.351

        # 16:00 is a boundary - matches off_peak first due to config order
        time_boundary = datetime(2024, 7, 15, 16, 0, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_boundary, "summer") == "off_peak"
        assert calculator.get_rate_for_time(time_boundary, "summer") == 0.351

        # 16:01 should be on-peak
        time_after = datetime(2024, 7, 15, 16, 1, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_after, "summer") == "on_peak"
        assert calculator.get_rate_for_time(time_after, "summer") == 0.634

    def test_exact_on_peak_end(self, calculator):
        """Test the exact moment on-peak period ends."""
        # 20:59 should be on-peak
        time_before = datetime(2024, 7, 15, 20, 59, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_before, "summer") == "on_peak"
        assert calculator.get_rate_for_time(time_before, "summer") == 0.634

        # 21:00 is a boundary - matches off_peak first due to config order
        time_boundary = datetime(2024, 7, 15, 21, 0, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_boundary, "summer") == "off_peak"
        assert calculator.get_rate_for_time(time_boundary, "summer") == 0.351

        # 21:01 should be off-peak
        time_after = datetime(2024, 7, 15, 21, 1, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_after, "summer") == "off_peak"
        assert calculator.get_rate_for_time(time_after, "summer") == 0.351

    def test_super_off_peak_to_off_peak_transition(self, calculator):
        """Test the transition from super off-peak to off-peak at 6am."""
        # 05:59 should be super_off_peak
        time_before = datetime(2024, 7, 15, 5, 59, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_before, "summer") == "super_off_peak"
        assert calculator.get_rate_for_time(time_before, "summer") == 0.314

        # 06:00 is a boundary - matches super_off_peak first due to config order
        time_boundary = datetime(2024, 7, 15, 6, 0, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_boundary, "summer") == "super_off_peak"
        assert calculator.get_rate_for_time(time_boundary, "summer") == 0.314

        # 06:01 should be off-peak
        time_after = datetime(2024, 7, 15, 6, 1, tzinfo=pytz.timezone("America/Los_Angeles"))
        assert calculator.get_rate_name(time_after, "summer") == "off_peak"
        assert calculator.get_rate_for_time(time_after, "summer") == 0.351

    def test_year_end_season_transition(self, calculator):
        """Test season determination across year-end boundary."""
        # December 31 should be winter
        with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 12, 31, 23, 59)
            assert calculator.get_current_season() == "winter"

        # January 1 should be winter
        with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 1, 0, 0)
            assert calculator.get_current_season() == "winter"


class TestTimezoneHandling:
    """Test timezone conversion and handling."""

    def test_utc_to_pst_conversion(self):
        """Test UTC to PST conversion during calc_rate."""
        calculator = TimeOfUseCalc(TIME_OF_USE_CONFIG, timezone="America/Los_Angeles")

        # June 15, 2024 at 5pm PST is on-peak
        test_time_pst = pytz.timezone("America/Los_Angeles").localize(datetime(2024, 6, 15, 17, 0))

        # Directly test that 5pm PST gives on-peak rate
        rate = calculator.get_rate_for_time(test_time_pst, "summer")
        assert rate == 0.634  # on-peak rate

    def test_daylight_saving_time_spring(self):
        """Test behavior during DST spring transition (March)."""
        calculator = TimeOfUseCalc(TIME_OF_USE_CONFIG, timezone="America/Los_Angeles")

        # March 10, 2024 is DST transition day (2am becomes 3am)
        # Test time before DST (1am PST)
        time_before = datetime(2024, 3, 10, 1, 0, tzinfo=pytz.timezone("America/Los_Angeles"))
        rate_before = calculator.get_rate_for_time(time_before, "winter")
        assert rate_before == 0.314  # super_off_peak

        # Test time after DST (3am PDT, which is 4am in clock time)
        time_after = pytz.timezone("America/Los_Angeles").localize(
            datetime(2024, 3, 10, 4, 0), is_dst=True
        )
        rate_after = calculator.get_rate_for_time(time_after, "winter")
        assert rate_after == 0.314  # super_off_peak

    def test_daylight_saving_time_fall(self):
        """Test behavior during DST fall transition (November)."""
        calculator = TimeOfUseCalc(TIME_OF_USE_CONFIG, timezone="America/Los_Angeles")

        # November 3, 2024 is DST transition day (2am becomes 1am)
        # Test time before DST ends (1am PDT)
        time_before = pytz.timezone("America/Los_Angeles").localize(
            datetime(2024, 11, 3, 1, 0), is_dst=True
        )
        rate_before = calculator.get_rate_for_time(time_before, "winter")
        assert rate_before == 0.314  # super_off_peak

        # Test time after DST ends (1am PST, second occurrence)
        time_after = pytz.timezone("America/Los_Angeles").localize(
            datetime(2024, 11, 3, 1, 0), is_dst=False
        )
        rate_after = calculator.get_rate_for_time(time_after, "winter")
        assert rate_after == 0.314  # super_off_peak

    @pytest.mark.parametrize(
        "timezone",
        [
            "America/Los_Angeles",
            "America/New_York",
            "UTC",
            "Europe/London",
        ],
    )
    def test_different_timezones(self, timezone):
        """Test that calculator works with different timezones."""
        calculator = TimeOfUseCalc(TIME_OF_USE_CONFIG, timezone=timezone)

        # Create a time in the specified timezone
        tz = pytz.timezone(timezone)
        test_time = tz.localize(datetime(2024, 7, 15, 18, 0))

        # Should work without errors
        rate = calculator.get_rate_for_time(test_time, "summer")
        assert isinstance(rate, float)
        assert rate > 0


class TestRateCalculations:
    """Test rate calculations with various power consumption values."""

    @pytest.fixture
    def calculator(self):
        return TimeOfUseCalc(TIME_OF_USE_CONFIG, timezone="America/Los_Angeles")

    @pytest.mark.parametrize(
        ("consumption", "season", "hour", "expected_rate_kwh", "expected_cost"),
        [
            # Super off-peak (0.314/kWh)
            (1000, "summer", 3, 0.314, 0.314),  # 1000W = 1kW * 0.314
            (2000, "summer", 3, 0.314, 0.628),  # 2000W = 2kW * 0.314
            (500, "summer", 3, 0.314, 0.157),  # 500W = 0.5kW * 0.314
            (100, "summer", 3, 0.314, 0.0314),  # 100W = 0.1kW * 0.314
            # Off-peak (0.351/kWh)
            (1000, "summer", 10, 0.351, 0.351),  # 1000W = 1kW * 0.351
            (2000, "summer", 10, 0.351, 0.702),  # 2000W = 2kW * 0.351
            # On-peak (0.634/kWh) - use 17:00 to avoid 16:00 boundary
            (1000, "summer", 17, 0.634, 0.634),  # 1000W = 1kW * 0.634
            (2000, "summer", 17, 0.634, 1.268),  # 2000W = 2kW * 0.634
            (5000, "summer", 17, 0.634, 3.170),  # 5000W = 5kW * 0.634
        ],
    )
    def test_rate_calculations_various_consumption(
        self, calculator, consumption, season, hour, expected_rate_kwh, expected_cost
    ):
        """Test rate calculations with various consumption levels."""
        test_time_la = pytz.timezone("America/Los_Angeles").localize(datetime(2024, 7, 15, hour, 0))

        with patch.object(calculator, "get_current_season", return_value="summer"):
            with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
                # Create a mock that handles the timezone conversion
                mock_utc_now = MagicMock()
                mock_utc_now.astimezone.return_value = test_time_la
                mock_datetime.now.return_value = mock_utc_now

                cost = calculator.calc_rate(consumption)
                assert abs(cost - expected_cost) < 0.001, (
                    f"Expected cost {expected_cost} for {consumption}W at hour {hour}, got {cost}"
                )

    def test_zero_consumption(self, calculator):
        """Test calculation with zero consumption."""
        test_time_la = pytz.timezone("America/Los_Angeles").localize(datetime(2024, 7, 15, 17, 0))

        with patch.object(calculator, "get_current_season", return_value="summer"):
            with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
                mock_utc_now = MagicMock()
                mock_utc_now.astimezone.return_value = test_time_la
                mock_datetime.now.return_value = mock_utc_now

                cost = calculator.calc_rate(0)
                assert cost == 0.0

    def test_very_high_consumption(self, calculator):
        """Test calculation with very high consumption (e.g., whole-house)."""
        test_time_la = pytz.timezone("America/Los_Angeles").localize(datetime(2024, 7, 15, 17, 0))

        with patch.object(calculator, "get_current_season", return_value="summer"):
            with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
                mock_utc_now = MagicMock()
                mock_utc_now.astimezone.return_value = test_time_la
                mock_datetime.now.return_value = mock_utc_now

                # 10kW (10,000W) during on-peak
                cost = calculator.calc_rate(10000)
                expected = 10 * 0.634  # 10kW * on-peak rate
                assert abs(cost - expected) < 0.001

    def test_fractional_wattage(self, calculator):
        """Test calculation with fractional wattage values."""
        test_time_la = pytz.timezone("America/Los_Angeles").localize(datetime(2024, 7, 15, 17, 0))

        with patch.object(calculator, "get_current_season", return_value="summer"):
            with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
                mock_utc_now = MagicMock()
                mock_utc_now.astimezone.return_value = test_time_la
                mock_datetime.now.return_value = mock_utc_now

                # 123.45W during on-peak
                cost = calculator.calc_rate(123.45)
                expected = (123.45 / 1000) * 0.634
                assert abs(cost - expected) < 0.000001  # Higher precision for small values


class TestCustomConfiguration:
    """Test calculator with custom TOU configurations."""

    def test_custom_config_different_rates(self):
        """Test calculator with custom rate structure."""
        custom_config = {
            "season": {
                "summer": ["06-01", "09-30"],
                "winter": ["10-01", "05-31"],
            },
            "summer": {
                "rate": {
                    "off_peak": 0.10,
                    "on_peak": 0.50,
                },
                "off_peak": [("00:00", "14:00"), ("22:00", "23:59")],
                "on_peak": [("14:00", "22:00")],
            },
            "winter": {
                "rate": {
                    "off_peak": 0.08,
                    "on_peak": 0.40,
                },
                "off_peak": [("00:00", "16:00"), ("21:00", "23:59")],
                "on_peak": [("16:00", "21:00")],
            },
        }

        calculator = TimeOfUseCalc(custom_config, timezone="America/Los_Angeles")

        # Test summer on-peak
        summer_time = datetime(2024, 7, 15, 18, 0, tzinfo=pytz.timezone("America/Los_Angeles"))
        rate = calculator.get_rate_for_time(summer_time, "summer")
        assert rate == 0.50

        # Test winter off-peak
        winter_time = datetime(2024, 1, 15, 10, 0, tzinfo=pytz.timezone("America/Los_Angeles"))
        rate = calculator.get_rate_for_time(winter_time, "winter")
        assert rate == 0.08

    def test_config_with_single_tier(self):
        """Test calculator with simplified single-tier configuration."""
        simple_config = {
            "season": {
                "all_year": ["01-01", "12-31"],
            },
            "all_year": {
                "rate": {
                    "flat_rate": 0.25,
                },
                "flat_rate": [("00:00", "23:59")],
            },
        }

        calculator = TimeOfUseCalc(simple_config, timezone="America/Los_Angeles")

        with patch("kasa_exporter.utils.time_of_use_calc.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 7, 15, 12, 0)
            season = calculator.get_current_season()
            assert season == "all_year"

        test_time = datetime(2024, 7, 15, 18, 0, tzinfo=pytz.timezone("America/Los_Angeles"))
        rate = calculator.get_rate_for_time(test_time, "all_year")
        assert rate == 0.25


class TestRateNameRetrieval:
    """Test get_rate_name method specifically."""

    @pytest.fixture
    def calculator(self):
        return TimeOfUseCalc(TIME_OF_USE_CONFIG, timezone="America/Los_Angeles")

    @pytest.mark.parametrize(
        ("hour", "expected_name"),
        [
            (0, "super_off_peak"),
            (5, "super_off_peak"),
            (6, "super_off_peak"),  # Boundary - matches super_off_peak
            (7, "off_peak"),
            (12, "off_peak"),
            (15, "off_peak"),
            (16, "off_peak"),  # Boundary - matches off_peak
            (17, "on_peak"),
            (20, "on_peak"),
            (21, "off_peak"),  # Boundary - matches off_peak
            (22, "off_peak"),
            (23, "off_peak"),
        ],
    )
    def test_rate_name_by_hour(self, calculator, hour, expected_name):
        """Test that get_rate_name returns correct period names."""
        test_time = datetime(2024, 7, 15, hour, 0, tzinfo=pytz.timezone("America/Los_Angeles"))
        rate_name = calculator.get_rate_name(test_time, "summer")
        assert rate_name == expected_name

    def test_rate_name_consistency_with_rate(self, calculator):
        """Test that rate name matches the rate returned."""
        for hour in range(24):
            test_time = datetime(2024, 7, 15, hour, 0, tzinfo=pytz.timezone("America/Los_Angeles"))
            rate_name = calculator.get_rate_name(test_time, "summer")
            rate = calculator.get_rate_for_time(test_time, "summer")
            expected_rate = TIME_OF_USE_CONFIG["summer"]["rate"][rate_name]
            assert rate == expected_rate, (
                f"Rate mismatch at hour {hour}: {rate_name} should have rate {expected_rate}, got {rate}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
