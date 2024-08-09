import asyncio
from datetime import datetime, timedelta
import logging
from kasa import Discover
from prometheus_client import Gauge, Counter, CollectorRegistry
import structlog

# Configure structured logging with timestamp
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    processors=[
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()


class DeviceRegistry:
    def __init__(self, collector_registry: CollectorRegistry):
        self.devices = {}
        self.last_checkin = {}

        # Prometheus metrics with the provided registry
        self.total_devices = Gauge(
            "device_registry_total_devices",
            "Total number of devices in the registry",
            registry=collector_registry,
        )
        self.pruned_devices = Counter(
            "device_registry_pruned_devices_total",
            "Total number of devices pruned",
            registry=collector_registry,
        )
        self.discovered_devices = Counter(
            "device_registry_discovered_devices_total",
            "Total number of devices discovered",
            registry=collector_registry,
        )

    async def discover_devices(self, credentials, interface):
        found_devices = await Discover.discover(credentials=credentials, **interface)
        self.devices = dict(found_devices.items())
        self.discovered_devices.inc(len(found_devices))
        self.total_devices.set(len(self.devices))
        for addr in self.devices:
            self.last_checkin[addr] = datetime.now()
        return self.devices

    def get_devices_info(self):
        return [
            {
                "alias": device.alias,
                "model": device.model,
                "address": addr,
                "last_checkin": self.last_checkin[addr],
            }
            for addr, device in self.devices.items()
        ]

    async def update_registry(self):
        while True:
            now = datetime.now()
            to_prune = [
                addr
                for addr, last_seen in self.last_checkin.items()
                if now - last_seen > timedelta(minutes=1)
            ]
            for addr in to_prune:
                logger.info(f"Pruning device {addr} due to missed check-in")
                self.devices.pop(addr, None)
                self.last_checkin.pop(addr, None)
                self.pruned_devices.inc()  # Increment pruned devices counter
            self.total_devices.set(len(self.devices))  # Update total devices gauge
            await asyncio.sleep(10)
