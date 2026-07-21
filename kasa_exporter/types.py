"""Type definitions for kasa_exporter."""

from datetime import datetime
from typing import Protocol

from kasa import Device
from prometheus_client.metrics import MetricWrapperBase


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
type MetricObjectsDict = dict[str, MetricWrapperBase | dict[str, MetricWrapperBase]]
