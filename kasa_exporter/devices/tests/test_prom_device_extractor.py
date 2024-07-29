import unittest
from unittest.mock import MagicMock, patch
from prometheus_client import CollectorRegistry, Gauge, Counter, Summary, Histogram
from kasa_exporter.devices.prom_device_extractor import (
    PromMetricType,
    PrometheusDeviceExtractor,
)


class TestPrometheusDeviceExtractor(unittest.TestCase):

    def setUp(self):
        self.registry = CollectorRegistry()
        self.metrics = {
            "cpu_usage": PromMetricType.GAUGE,
            "memory_usage": PromMetricType.COUNTER,
            "response_time": PromMetricType.SUMMARY,
            "request_size": PromMetricType.HISTOGRAM,
        }
        self.device_extractor = PrometheusDeviceExtractor(
            self.registry, 
            self.metrics
        )
        

    def tearDown(self):
        # Ensures that the registry is reset after each test
        self.registry = None
        self.device_extractor = None

    def test_sanitize_metric_name(self):
        name = "CPU Usage %"
        sanitized_name = self.device_extractor.sanitize_metric_name(name)
        self.assertEqual(sanitized_name, "cpu_usage_")

    def test_register_metric(self):
        metric_key = "cpu_usage"
        metric_type = PromMetricType.GAUGE

        self.device_extractor.register_metric(metric_key, metric_type)
        metric_object = self.device_extractor.metric_objects[metric_key]

        self.assertIsInstance(metric_object, Gauge)
        self.assertEqual(metric_object._name, "device_cpu_usage")

    def test_initialize_metrics(self):
        self.device_extractor.initialize_metrics()
        self.assertIn("cpu_usage", self.device_extractor.metric_objects)
        self.assertIn("memory_usage", self.device_extractor.metric_objects)
        self.assertIn("response_time", self.device_extractor.metric_objects)
        self.assertIn("request_size", self.device_extractor.metric_objects)

    # @patch("kasa_exporter.devices.prom_device_extractor.logger")
    # def test_update_metrics(self, mock_logger):
    #     device = MagicMock()
    #     device.id = "device_123"
    #     device.alias = "test_device"
    #     device.ip = "192.168.1.1"
    #     device.cpu_usage = 75.5
    #     device.memory_usage = 1024
    #     device.response_time = 0.123
    #     device.request_size = 512

    #     self.device_extractor.update_metrics(device)

    #     self.device_extractor.metric_objects["cpu_usage"].labels.assert_called_with(
    #         device_id=device.id, alias=device.alias, ip=device.ip
    #     )
    #     self.device_extractor.metric_objects["memory_usage"].labels.assert_called_with(
    #         device_id=device.id, alias=device.alias, ip=device.ip
    #     )
    #     self.device_extractor.metric_objects["response_time"].labels.assert_called_with(
    #         device_id=device.id, alias=device.alias, ip=device.ip
    #     )
    #     self.device_extractor.metric_objects["request_size"].labels.assert_called_with(
    #         device_id=device.id, alias=device.alias, ip=device.ip
    #     )

    #     mock_logger.debug.assert_called()


if __name__ == "__main__":
    unittest.main()
