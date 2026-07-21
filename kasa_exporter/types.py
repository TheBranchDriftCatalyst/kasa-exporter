"""Type definitions for kasa_exporter."""

from datetime import datetime
from typing import Any, Protocol

from kasa import Device


class KasaDevice(Protocol):
    """Protocol for Kasa device interface."""

    alias: str
    model: str
    host: str

    async def update(self) -> None:
        """Update device state."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from device."""
        ...


# Type aliases
type DeviceDict = dict[str, Device]
type LastCheckinDict = dict[str, datetime]
type SeenDevicesSet = set[str]
# metric_objects values are heterogeneous ({"metric": <MetricWrapper>, "getter": Callable,
# "derive_labels": dict[str, Callable]}) so we widen to Any to avoid overly-precise unions.
type MetricObjectsDict = dict[str, dict[str, Any]]
