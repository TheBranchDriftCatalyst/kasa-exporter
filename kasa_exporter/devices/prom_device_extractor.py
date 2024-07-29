from enum import Enum
from prometheus_client import (
    Gauge,
    Counter,
    Summary,
    Histogram,
    CollectorRegistry,
)
import re
import structlog
from typing import Callable, Dict, Any, Optional

logger = structlog.get_logger()


class PromMetricType(Enum):
    GAUGE = "gauge"
    COUNTER = "counter"
    SUMMARY = "summary"
    HISTOGRAM = "histogram"


PROM_METRIC_TYPES = {
    PromMetricType.GAUGE: Gauge,
    PromMetricType.COUNTER: Counter,
    PromMetricType.SUMMARY: Summary,
    PromMetricType.HISTOGRAM: Histogram,
}


class PrometheusDeviceExtractor:
    @staticmethod
    def sanitize_metric_name(name: str) -> str:
        """Sanitize the metric name to be Prometheus compatible."""
        return re.sub(r"[^a-zA-Z0-9_]", "", name.lower().replace(" ", "_"))

    def __init__(
        self,
        registry: CollectorRegistry,
        metrics: Optional[Dict[str, PromMetricType]] = None,
        dimensions: Optional[
            Dict[str, Optional[Callable[[Any], Any]]]
        ] = None,  # Updated type
    ) -> None:
        self.registry = registry
        self.metrics = metrics or {}
        self.dimensions = dimensions or {}
        self.metric_objects = {}

    def register_metric(self, metric_key: str, metric_type: PromMetricType) -> None:
        if metric_type in PROM_METRIC_TYPES:
            sanitized_name = self.sanitize_metric_name(metric_key)
            metric_class = PROM_METRIC_TYPES[metric_type]
            self.metric_objects[metric_key] = metric_class(
                f"{sanitized_name}",
                f"{metric_key}",
                self.dimensions.keys(),
                registry=self.registry,
            )
            logger.info(
                f"Registered {metric_type.name.lower()} metric for {metric_key}"
            )
        else:
            logger.error(f"Metric type '{metric_type}' not supported.")
            raise ValueError(f"Metric type '{metric_type}' not supported.")

    def initialize_metrics(self) -> None:
        for metric_key, metric_type in self.metrics.items():
            self.register_metric(metric_key, metric_type)

    def get_device_labels(self, device: Any) -> Dict[str, Any]:
        labels = {}
        for dimension_key, dimension_getter in self.dimensions.items():
            if dimension_getter is None:
                labels[dimension_key] = getattr(device, dimension_key, None)
            else:
                try:
                    labels[dimension_key] = dimension_getter(device)
                except Exception as e:
                    logger.error(f"Error retrieving dimension '{dimension_key}': {e}")
                    labels[dimension_key] = None
        return labels

    def update_metrics(self, device: Any) -> None:
        for metric_key, metric_object in self.metric_objects.items():
            metric_value = device.state_information[metric_key]
            device_labels = self.get_device_labels(device)
            if metric_value is not None:
                metric_object.labels(**device_labels).set(metric_value)
                logger.debug(
                    f"Updated metric '{metric_key}'",
                    value=metric_value,
                    device_labels=device_labels,
                )
