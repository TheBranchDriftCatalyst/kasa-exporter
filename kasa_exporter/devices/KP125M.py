from datetime import datetime
from typing import Any
import structlog

from .prom_device_extractor import PromMetricType, PrometheusDeviceExtractor
from ..utils.time_of_use_calc import TIME_OF_USE_CONFIG, TimeOfUseCalc

logger = structlog.get_logger()

dimensions = {
    "device_id": None,
    "alias": None,
    "model": None,
}

calculator = TimeOfUseCalc(TIME_OF_USE_CONFIG)

# NOTE: right now this is coming from state_infomration, lets change this to device.features
# we have access ot the snesors directly here.
metrics = {
    "Current consumption": {
        "type": PromMetricType.GAUGE,
        # TODO: note that i want to change this a bit and move to the device.features 
        # (which gives us more direct access to the sensors)
        "getter": lambda device: device.state_information["Current consumption"],
        # "derived_labels": lambda device: { }
    },
    "Today's consumption": PromMetricType.GAUGE,
    "This month's consumption": PromMetricType.GAUGE,
    "RSSI": PromMetricType.GAUGE, # This can also be moved onto the signal level as a derived metric
    "Signal Level": PromMetricType.GAUGE,
    "consumption_cost": { # this can be moved to a derived label on the current consumption metric
        "type": PromMetricType.GAUGE,
        "getter": lambda device: calculator.calculate_rate_for_current_usage(
            device.state_information["Current consumption"]
        ),
    },
}


class KP125M(PrometheusDeviceExtractor):
    def __init__(self, registry):
        super().__init__(registry, metrics, dimensions)

    def is_device(self, device) -> bool:
        # Implement your device-specific check logic here
        pass
