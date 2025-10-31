import pytest
from prometheus_client import CollectorRegistry, Gauge

from kasa_exporter.devices.prom_device_extractor import (
    PrometheusDeviceExtractor,
    PromMetricType,
)


@pytest.fixture
def registry():
    """Create a fresh CollectorRegistry for each test."""
    return CollectorRegistry()


@pytest.fixture
def metrics():
    """Define standard metrics for testing."""
    return {
        "cpu_usage": PromMetricType.GAUGE,
        "memory_usage": PromMetricType.COUNTER,
        "response_time": PromMetricType.SUMMARY,
        "request_size": PromMetricType.HISTOGRAM,
    }


@pytest.fixture
def device_extractor(registry, metrics):
    """Create a PrometheusDeviceExtractor instance for testing."""
    return PrometheusDeviceExtractor(registry, metrics)


def test_sanitize_metric_name(device_extractor):
    name = "CPU Usage %"
    sanitized_name = device_extractor.sanitize_metric_name(name)
    assert sanitized_name == "cpu_usage_"


def test_register_metric(device_extractor):
    metric_key = "cpu_usage"
    metric_type = PromMetricType.GAUGE

    device_extractor.register_metric(metric_key, metric_type)
    metric_object = device_extractor.metric_objects[metric_key]

    # metric_objects stores a dict with 'metric', 'getter', 'derive_labels'
    assert isinstance(metric_object, dict)
    assert "metric" in metric_object
    assert isinstance(metric_object["metric"], Gauge)
    assert metric_object["metric"]._name == "cpu_usage"


def test_initialize_metrics(device_extractor):
    device_extractor.initialize_metrics()
    assert "cpu_usage" in device_extractor.metric_objects
    assert "memory_usage" in device_extractor.metric_objects
    assert "response_time" in device_extractor.metric_objects
    assert "request_size" in device_extractor.metric_objects


# @pytest.mark.skip(reason="Commented out in original - needs mock setup")
# @patch("kasa_exporter.devices.prom_device_extractor.logger")
# def test_update_metrics(mock_logger, device_extractor):
#     device = MagicMock()
#     device.id = "device_123"
#     device.alias = "test_device"
#     device.ip = "192.168.1.1"
#     device.cpu_usage = 75.5
#     device.memory_usage = 1024
#     device.response_time = 0.123
#     device.request_size = 512

#     device_extractor.update_metrics(device)

#     device_extractor.metric_objects["cpu_usage"].labels.assert_called_with(
#         device_id=device.id, alias=device.alias, ip=device.ip
#     )
#     device_extractor.metric_objects["memory_usage"].labels.assert_called_with(
#         device_id=device.id, alias=device.alias, ip=device.ip
#     )
#     device_extractor.metric_objects["response_time"].labels.assert_called_with(
#         device_id=device.id, alias=device.alias, ip=device.ip
#     )
#     device_extractor.metric_objects["request_size"].labels.assert_called_with(
#         device_id=device.id, alias=device.alias, ip=device.ip
#     )

#     mock_logger.debug.assert_called()
