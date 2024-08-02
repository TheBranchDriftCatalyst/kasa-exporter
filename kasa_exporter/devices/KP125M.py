from datetime import date, datetime

import structlog

from ..utils.time_of_use_calc import TIME_OF_USE_CONFIG, TimeOfUseCalc
from .prom_device_extractor import (DimensionsType, MetricsType,
                                    PrometheusDeviceExtractor, PromMetricType)

logger = structlog.get_logger()

dimensions: DimensionsType = {
    "device_id": None,
    "alias": None,
    "model": None,
}

calculator = TimeOfUseCalc(TIME_OF_USE_CONFIG)

metrics: MetricsType = {
    "Current consumption": {
        "type": PromMetricType.GAUGE,
        # TODO: note that i want to change this a bit and move to the device.features
        # (which gives us more direct access to the sensors)
        "getter": lambda device: device.state_information["Current consumption"],
        "derive_labels": {
            #  DOnt do this.... it is naughty creates more metrics....
            # cost does not have a finite cardinality and is... effectively random (the space is fuckin big)
            # "cost": lambda device: calculator.calc_rate(
            #     device.state_information["Current consumption"]
            # ),
            "season": lambda _d: calculator.get_current_season(),
            "rate": lambda _d: calculator.get_rate_for_time(
                date.today(), calculator.get_current_season()
            ),
            "rate_class": lambda _d: calculator.get_rate_name(
                date.today(), calculator.get_current_season()
            ),
        },
    },
    "Today's consumption": PromMetricType.GAUGE,
    "This month's consumption": PromMetricType.GAUGE,
    "RSSI": PromMetricType.GAUGE,  # This can also be moved onto the signal level as a derived metric
    # "Signal Level": PromMetricType.GAUGE,
    "consumption_cost": {  # this can be moved to a derived label on the current consumption metric
        "type": PromMetricType.GAUGE,
        "getter": lambda device: calculator.calc_rate(
            device.state_information["Current consumption"]
        ),
        "derive_labels": {
            "season": lambda _d: calculator.get_current_season(),
            "rate": lambda _d: calculator.get_rate_for_time(
                date.today(), calculator.get_current_season()
            ),
            "rate_class": lambda _d: calculator.get_rate_name(
                date.today(), calculator.get_current_season()
            ),
        },
    },
    # "power_state": {
        # type: PromMetricType.ENUM,
        
    # }
}

KP125MDeviceExtractor = PrometheusDeviceExtractor(
    metrics=metrics, 
    dimensions=dimensions,
    # is_device: lambda device: device.model == "KP125M"
)
