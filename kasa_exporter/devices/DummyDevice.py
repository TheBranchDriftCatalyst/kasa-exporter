from prometheus_client import CollectorRegistry
import random

from kasa_exporter.devices.prom_device_extractor import PromMetricType, PrometheusDeviceExtractor

# Initialize registry
registry = CollectorRegistry()

# Define metrics and dimensions
metrics = {
    "temperature": {
        "type": PromMetricType.GAUGE,
        "getter": lambda d: random.uniform(20.0, 30.0),
    },
    "errors": {
        "type": PromMetricType.COUNTER,
        "getter": lambda d: random.randint(0, 5),
    },
    "latency": {
        "type": PromMetricType.SUMMARY,
        "getter": lambda d: random.uniform(0.1, 1.0),
    },
    "response_time": {
        "type": PromMetricType.HISTOGRAM,
        "getter": lambda d: random.uniform(0.1, 2.0),
    },
    "version": {
        "type": PromMetricType.INFO,
        "getter": lambda d: {"version": "1.0.0", "buildhost": "localhost"},
    },
    "status": {
        "type": PromMetricType.ENUM,
        "states": ["starting", "running", "stopped"],
        "getter": lambda d: random.choice(["starting", "running", "stopped"]),
    },
}

dimensions = {"device_id": lambda d: "DummyTestDevice", "location": lambda d: "server_room"}

# Initialize the PrometheusDeviceExtractor
Extractor = PrometheusDeviceExtractor(
    registry=registry, metrics=metrics, dimensions=dimensions
)
