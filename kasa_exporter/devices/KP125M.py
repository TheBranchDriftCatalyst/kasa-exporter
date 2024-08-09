from datetime import date, datetime

import structlog

from ..utils.time_of_use_calc import TIME_OF_USE_CONFIG, TimeOfUseCalc
from .prom_device_extractor import (DimensionsType,
                                    PrometheusDeviceExtractor, PromMetricType)

logger = structlog.get_logger()

dimensions: DimensionsType = {
    "device_id": None,
    "alias": None,
    "model": None,
}

calculator = TimeOfUseCalc(TIME_OF_USE_CONFIG)

metrics = {
    "signal_level": {
        "type": PromMetricType.GAUGE,
        "getter": lambda d: d.features["signal_level"].value,
    },
    "state": {
        "type": PromMetricType.ENUM,
        "getter": lambda d: "on" if d.features["state"].value else "off",
        "states": ["on", "off"],
    },
    "rssi": {
        "type": PromMetricType.GAUGE,
        "getter": lambda d: d.features["rssi"].value,
    },
    "ssid": {
        "type": PromMetricType.INFO,
        "getter": lambda d: {"ssid": d.features["ssid"].value},
    },
    "on_since": {
        "type": PromMetricType.GAUGE,
        "getter": lambda d: (
            datetime.now() - d.features["on_since"].value.replace(tzinfo=None)
        ).total_seconds()
        / 3600,
    },
    "auto_off_enabled": {
        "type": PromMetricType.ENUM,
        "getter": lambda d: (
            "enabled" if d.features["auto_off_enabled"].value else "disabled"
        ),
        "states": ["enabled", "disabled"],
    },
    "auto_off_minutes": {
        "type": PromMetricType.GAUGE,
        "getter": lambda d: d.features["auto_off_minutes"].value,
    },
    "auto_off_at": {
        "type": PromMetricType.INFO,
        "getter": lambda d: {"auto_off_at": str(d.features["auto_off_at"].value)},
    },
    "cloud_connection": {
        "type": PromMetricType.ENUM,
        "getter": lambda d: (
            "connected" if d.features["cloud_connection"].value else "disconnected"
        ),
        "states": ["connected", "disconnected"],
    },
    "current_consumption": {
        "type": PromMetricType.GAUGE,
        "getter": lambda d: d.features["current_consumption"].value,
    },
    "consumption_today": {
        "type": PromMetricType.GAUGE,
        "getter": lambda d: d.features["consumption_today"].value,
    },  # Histogram for distribution over the day
    "consumption_this_month": {
        "type": PromMetricType.HISTOGRAM,
        "getter": lambda d: d.features["consumption_this_month"].value,
    },  # Summary for distribution over the month
    "auto_update_enabled": {
        "type": PromMetricType.ENUM,
        "getter": lambda d: (
            "enabled" if d.features["auto_update_enabled"].value else "disabled"
        ),
        "states": ["enabled", "disabled"],
    },
    "update_available": {
        "type": PromMetricType.ENUM,
        "getter": lambda d: (
            "available" if d.features["update_available"].value else "not_available"
        ),
        "states": ["available", "not_available"],
    },
    "current_firmware_version": {
        "type": PromMetricType.INFO,
        "getter": lambda d: {
            "current_firmware_version": d.features["current_firmware_version"].value
        },
    },
    "available_firmware_version": {
        "type": PromMetricType.INFO,
        "getter": lambda d: {
            "available_firmware_version": d.features["available_firmware_version"].value
        },
    },
    "led": {
        "type": PromMetricType.ENUM,
        "getter": lambda d: "on" if d.features["led"].value else "off",
        "states": ["on", "off"],
    },
    "update_attempts": {
        "type": PromMetricType.COUNTER,
        "getter": lambda d: int(d.features.get("update_attempts", 0)),
    },  # Counter for update attempts
    "consumption_cost": {  # this can be moved to a derived label on the current consumption metric
        "type": PromMetricType.GAUGE,
        "getter": lambda device: calculator.calc_rate(
            device.state_information["Current consumption"]
        ),
        "derive_labels": {
            # not the best way to do this but works well enough.  (we still need to know these upfront in register)
            "season": lambda _d: calculator.get_current_season(),
            # "rate": lambda _d: calculator.get_rate_for_time(
            #     date.today(), calculator.get_current_season()
            # ),
            "rate_class": lambda _d: calculator.get_rate_name(
                date.today(), calculator.get_current_season()
            ),
        },
    },
}

Extractor = PrometheusDeviceExtractor(
    metrics=metrics, 
    dimensions=dimensions,
    # is_device: lambda device: device.model == "KP125M"
)
