"""Type definitions for kasa_exporter."""

from datetime import datetime
from typing import Protocol, TypeAlias

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
DeviceDict: TypeAlias = dict[str, Device]
LastCheckinDict: TypeAlias = dict[str, datetime]
SeenDevicesSet: TypeAlias = set[str]
MetricObjectsDict: TypeAlias = dict[str, MetricWrapperBase | dict[str, MetricWrapperBase]]
