from enum import Enum
from prometheus_client import (
    Gauge,
    Counter,
    Summary,
    Histogram,
    CollectorRegistry,
    Info,
    Enum as PromEnum,
)
import re
from pydantic import BaseModel, InstanceOf
import structlog
from typing import Callable, Dict, Any, Optional, Union

logger = structlog.get_logger()

# Define the PromMetricType
PromMetricTypeType = Union[
    InstanceOf[Counter],
    InstanceOf[Gauge],
    InstanceOf[Histogram],
    InstanceOf[Summary],
    InstanceOf[PromEnum],
    InstanceOf[Info],
]

# Define the type for metrics
MetricsType = Optional[
    Dict[
        str,  # device metric name (also prom metric name)
        Union[
            PromMetricTypeType,
            Dict[str, Union[PromMetricTypeType, Callable[[Any], Any]]],
        ],
    ]
]

# Define the type for dimensions
DimensionsType = Optional[Dict[str, Optional[Callable[[Any], Any]]]]


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
        self.metric_objects = {}

    def initialize_metrics(self, registry=None) -> None:
        self.registry = registry
        for metric_key, metric_info in self.metrics.items():
            self.register_metric(metric_key, metric_info)

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

    def register_metric(
        self, metric_key: str, metric_info: Union[PromMetricTypeType, Dict[str, Any]]
    ) -> None:
        if isinstance(metric_info, dict):
            metric_type = metric_info.get("type")
            getter = metric_info.get("getter")
            derive_labels = metric_info.get("derive_labels", {})
            states = (
                metric_info.get("states")
                if metric_type == PromMetricType.ENUM
                else None
            )
        else:
            metric_type = metric_info
            getter = None
            derive_labels = {}
            states = None

        if metric_type in PROM_METRIC_TYPES:
            sanitized_name = self.sanitize_metric_name(metric_key)
            metric_class = PROM_METRIC_TYPES[metric_type]
            label_names = list(self.dimensions.keys()) + list(derive_labels.keys())

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

            logger.info(
                f"Registered {metric_type.name.lower()} metric for {metric_key}"
            )
        else:
            logger.error(f"Metric type '{metric_type}' not supported.")
            raise ValueError(f"Metric type '{metric_type}' not supported.")

    def update_metrics(self, device: Any) -> None:
        for metric_key, metric_info in self.metric_objects.items():
            getter = metric_info["getter"]
            derive_labels = metric_info["derive_labels"]

            metric_value = (
                getter(device) if getter else device.state_information.get(metric_key)
            )
            device_labels = self.get_device_labels(device)
            derived_labels = {
                label: func(device) for label, func in derive_labels.items()
            }

            all_labels = {**device_labels, **derived_labels}
            if metric_value is not None:
                metric_object = metric_info["metric"]
                if isinstance(metric_object, Gauge):
                    metric_object.labels(**all_labels).set(metric_value)
                elif isinstance(metric_object, Counter):
                    metric_object.labels(**all_labels).inc(metric_value)
                elif isinstance(metric_object, Summary):
                    metric_object.labels(**all_labels).observe(metric_value)
                elif isinstance(metric_object, Histogram):
                    metric_object.labels(**all_labels).observe(metric_value)
                elif isinstance(metric_object, Info):
                    metric_object.labels(**all_labels).info(metric_value)
                elif isinstance(metric_object, PromEnum):
                    metric_object.labels(**all_labels).state(metric_value)
                logger.debug(
                    f"Updated metric '{metric_key}'",
                    value=metric_value,
                    device_labels=device_labels,
                    derived_labels=derived_labels,
                    has_getter=bool(getter),
                )
