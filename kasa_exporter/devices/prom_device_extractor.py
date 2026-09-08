import re
from collections.abc import Callable
from enum import Enum
from typing import Any

import structlog
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
)
from prometheus_client import (
    Enum as PromEnum,
)
from pydantic import InstanceOf

from ..types import MetricObjectsDict
from ..utils.build_info import VERSION

logger = structlog.get_logger()

# Define the PromMetricType
PromMetricTypeType = (
    InstanceOf[Counter]
    | InstanceOf[Gauge]
    | InstanceOf[Histogram]
    | InstanceOf[Summary]
    | InstanceOf[PromEnum]
    | InstanceOf[Info]
)

# Define the type for metrics
MetricsType = (
    dict[
        str,  # device metric name (also prom metric name)
        PromMetricTypeType | dict[str, PromMetricTypeType | Callable[[Any], Any]],
    ]
    | None
)

# Define the type for dimensions
DimensionsType = dict[str, Callable[[Any], Any] | None] | None


class PromMetricType(Enum):
    GAUGE = "gauge"  # has set and #inc and #dec methods
    COUNTER = "counter"  # only has #inc
    SUMMARY = "summary"
    HISTOGRAM = "histogram"
    INFO = "info"
    ENUM = "enum"


# Define the Prometheus metric types mapping
PROM_METRIC_TYPES = {
    PromMetricType.GAUGE: Gauge,
    PromMetricType.COUNTER: Counter,
    PromMetricType.SUMMARY: Summary,
    PromMetricType.HISTOGRAM: Histogram,
    PromMetricType.INFO: Info,
    PromMetricType.ENUM: PromEnum,
}


class PrometheusDeviceExtractor:
    registry: InstanceOf[CollectorRegistry]
    metrics: MetricsType = None
    dimensions: DimensionsType = None

    @staticmethod
    def sanitize_metric_name(name: str) -> str:
        """Sanitize the metric name to be Prometheus compatible."""
        return re.sub(r"[^a-zA-Z0-9_]", "", name.lower().replace(" ", "_"))

    def __init__(self, registry=None, metrics=None, dimensions=None) -> None:
        self.registry = registry
        self.metrics = metrics or {}
        self.dimensions = dimensions or {}
        self.metric_objects: MetricObjectsDict = {}
        self.device_samples: dict[str, dict[str, tuple]] = {}
        self.counter_values: dict[tuple, float] = {}

    def initialize_metrics(self, registry=None) -> None:
        self.registry = registry
        self.device_samples.clear()
        self.counter_values.clear()
        for metric_key, metric_info in self.metrics.items():
            self.register_metric(metric_key, metric_info)

    def get_device_labels(self, device: Any) -> dict[str, Any]:
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

        # Inject global version label to all metrics
        labels["version"] = VERSION

        return labels

    def register_metric(
        self, metric_key: str, metric_info: PromMetricTypeType | dict[str, Any]
    ) -> None:
        if isinstance(metric_info, dict):
            metric_type = metric_info.get("type")
            getter = metric_info.get("getter")
            derive_labels = metric_info.get("derive_labels", {})
            states = metric_info.get("states") if metric_type == PromMetricType.ENUM else None
        else:
            metric_type = metric_info
            getter = None
            derive_labels = {}
            states = None

        if metric_type in PROM_METRIC_TYPES:
            sanitized_name = self.sanitize_metric_name(metric_key)
            metric_class = PROM_METRIC_TYPES[metric_type]
            # Include dimensions, derived labels, and global version label
            label_names = list(self.dimensions.keys()) + list(derive_labels.keys()) + ["version"]

            if metric_type == PromMetricType.ENUM:
                self.metric_objects[metric_key] = {
                    "metric": metric_class(
                        f"{sanitized_name}",
                        f"{metric_key}",
                        states=states,
                        labelnames=label_names,
                        registry=self.registry,
                    ),
                    "getter": getter,
                    "derive_labels": derive_labels,
                }
            else:
                self.metric_objects[metric_key] = {
                    "metric": metric_class(
                        f"{sanitized_name}",
                        f"{metric_key}",
                        labelnames=label_names,
                        registry=self.registry,
                    ),
                    "getter": getter,
                    "derive_labels": derive_labels,
                }

            logger.info(f"Registered {metric_type.name.lower()} metric for {metric_key}")
        else:
            logger.error(f"Metric type '{metric_type}' not supported.")
            raise ValueError(f"Metric type '{metric_type}' not supported.")

    def update_metrics(self, device: Any) -> None:  # noqa: PLR0912
        samples = self.device_samples.setdefault(str(device.device_id), {})
        for metric_key, metric_info in self.metric_objects.items():
            try:
                getter = metric_info["getter"]
                derive_labels = metric_info["derive_labels"]

                metric_value = (
                    getter(device) if getter else device.state_information.get(metric_key)
                )
                device_labels = self.get_device_labels(device)

                # Compute derived labels with error handling
                derived_labels = {}
                for label, func in derive_labels.items():
                    try:
                        derived_labels[label] = func(device)
                    except Exception as e:
                        logger.error(
                            f"Error computing derived label '{label}' for metric '{metric_key}' on device {getattr(device, 'alias', 'unknown')}",
                            error=str(e),
                        )
                        derived_labels[label] = None

                all_labels = {**device_labels, **derived_labels}

                # Warn about None values in labels (helpful for debugging label issues)
                none_labels = [k for k, v in all_labels.items() if v is None]
                if none_labels:
                    logger.warning(
                        f"Metric '{metric_key}' has None labels on device {getattr(device, 'alias', 'unknown')}",
                        none_labels=none_labels,
                        all_labels=all_labels,
                    )

                if metric_value is not None:
                    metric_object = metric_info["metric"]
                    label_values = tuple(all_labels[name] for name in metric_object._labelnames)
                    previous = samples.get(metric_key)
                    if previous is not None and previous != label_values:
                        metric_object.remove(*previous)
                    samples[metric_key] = label_values
                    if isinstance(metric_object, Gauge):
                        metric_object.labels(**all_labels).set(metric_value)
                    elif isinstance(metric_object, Counter):
                        key = (metric_key, label_values)
                        last_value = self.counter_values.get(key, 0)
                        delta = (
                            metric_value - last_value
                            if metric_value >= last_value
                            else metric_value
                        )
                        metric_object.labels(**all_labels).inc(delta)
                        self.counter_values[key] = metric_value
                    elif isinstance(metric_object, (Summary, Histogram)):
                        metric_object.labels(**all_labels).observe(metric_value)
                    elif isinstance(metric_object, Info):
                        metric_object.labels(**all_labels).info(metric_value)
                    elif isinstance(metric_object, PromEnum):
                        metric_object.labels(**all_labels).state(metric_value)

                    logger.debug(
                        f"Updated metric '{metric_key}'",
                        value=metric_value,
                        device_alias=getattr(device, "alias", "unknown"),
                        labels=all_labels,
                    )
                elif metric_key in samples:
                    metric_info["metric"].remove(*samples.pop(metric_key))
            except KeyError:
                # Device models expose different optional features. Never retain a
                # previous reading when a feature is no longer available.
                if metric_key in samples:
                    metric_info["metric"].remove(*samples.pop(metric_key))
            except Exception as e:
                if metric_key in samples:
                    metric_info["metric"].remove(*samples.pop(metric_key))
                logger.error(
                    f"Error processing metric '{metric_key}' for device {getattr(device, 'alias', 'unknown')}",
                    metric_key=metric_key,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Continue to next metric instead of crashing
                continue

    def remove_device(self, device: Any) -> None:
        """Stop publishing stale readings for an unreachable or removed device."""
        for key, values in self.device_samples.pop(str(device.device_id), {}).items():
            self.metric_objects[key]["metric"].remove(*values)
            self.counter_values.pop((key, values), None)
