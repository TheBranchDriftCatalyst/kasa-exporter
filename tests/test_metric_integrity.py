from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytz
from prometheus_client import CollectorRegistry

from kasa_exporter.devices.prom_device_extractor import PrometheusDeviceExtractor, PromMetricType
from kasa_exporter.routines.device_registry import DeviceRegistry
from kasa_exporter.utils.time_of_use_calc import TimeOfUseCalc


def test_label_transition_removes_previous_tariff_and_device_removal_clears_values():
    registry = CollectorRegistry()
    extractor = PrometheusDeviceExtractor(
        metrics={
            "tariff": {
                "type": PromMetricType.GAUGE,
                "getter": lambda d: d.value,
                "derive_labels": {"period": lambda d: d.period},
            }
        },
        dimensions={"device_id": None},
    )
    extractor.initialize_metrics(registry)
    device = SimpleNamespace(device_id="one", period="off_peak", value=0.351)
    extractor.update_metrics(device)
    device.period, device.value = "on_peak", 0.634
    extractor.update_metrics(device)
    samples = next(iter(registry.collect())).samples
    assert len(samples) == 1
    assert samples[0].labels["period"] == "on_peak"
    assert samples[0].value == 0.634
    extractor.remove_device(device)
    assert next(iter(registry.collect())).samples == []


def test_observed_cumulative_counter_is_not_added_again_every_poll():
    registry = CollectorRegistry()
    extractor = PrometheusDeviceExtractor(
        metrics={
            "attempts": {
                "type": PromMetricType.COUNTER,
                "getter": lambda d: d.value,
            }
        },
        dimensions={"device_id": None},
    )
    extractor.initialize_metrics(registry)
    device = SimpleNamespace(device_id="one", value=3)
    for value in [3, 3, 4, 1]:
        device.value = value
        extractor.update_metrics(device)
    sample = next(s for s in next(iter(registry.collect())).samples if s.name == "attempts_total")
    assert sample.value == 5  # initial3 + delta1 + reset1


def test_discovery_alone_is_not_fresh_and_old_success_expires():
    registry = DeviceRegistry(CollectorRegistry())
    registry.devices["host"] = SimpleNamespace()
    assert registry.fresh_device_count() == 0
    registry.last_scrape_success["host"] = datetime.now(tz=UTC)
    assert registry.fresh_device_count() == 1
    registry.last_scrape_success["host"] -= timedelta(seconds=61)
    assert registry.fresh_device_count() == 0


def test_next_tariff_boundary_and_dst_duration():
    calculator = TimeOfUseCalc(timezone="America/Los_Angeles")
    zone = pytz.timezone(calculator.timezone)
    assert calculator.seconds_until_rate_change(zone.localize(datetime(2026, 9, 8, 15, 59))) == 60
    assert calculator.seconds_until_rate_change(zone.localize(datetime(2026, 9, 8, 16))) == 5 * 3600
    assert calculator.seconds_until_rate_change(zone.localize(datetime(2026, 3, 8, 0))) == 5 * 3600
    assert calculator.seconds_until_rate_change(zone.localize(datetime(2026, 11, 1, 0))) == 7 * 3600
