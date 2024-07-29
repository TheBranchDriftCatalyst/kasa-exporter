import structlog

from .prom_device_extractor import PromMetricType, PrometheusDeviceExtractor
# from devices.prom_device_extractor import (
#     PromMetricType,
#     PrometheusDeviceExtractor,
# )

logger = structlog.get_logger()

dimensions = {
    "device_id": None,
    "alias": None,
    "model": None,
}

# NOTE: right now this is coming from state_infomration, lets change this to device.features
# we have access ot the snesors directly here.
metrics = {
    "Current consumption": PromMetricType.GAUGE,
    "Today's consumption": PromMetricType.GAUGE,
    "This month's consumption": PromMetricType.GAUGE,
    "RSSI": PromMetricType.GAUGE,
    "Signal Level": PromMetricType.GAUGE,
    # "State": PromMetricType.BOOLEAN,
}


class KP125M(PrometheusDeviceExtractor):
    def __init__(self, registry):
        super().__init__(registry, metrics, dimensions)

    def is_device(self, device) -> bool:
        # Implement your device-specific check logic here
        pass


# # Example usage
# if __name__ == "__main__":
#     registry = CollectorRegistry()
#     kp125m_extractor = KP125M(registry)
#     kp125m_extractor.initialize_metrics()

#     # Simulate a device object for testing
#     class Device:
#         id = "123"
#         alias = "Test Device"
#         ip = "192.168.1.1"
#         current_consumption = 10.5
#         rssi = -70
#         signal_level = 3

#         def get(self, path):
#             # Simulate the nested dictionary retrieval for device_type
#             if path == "_.info.device_type":
#                 return "KP125M"
#             return None

#     device = Device()
#     kp125m_extractor.update_metrics(device)
