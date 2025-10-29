import asyncio
import logging
from datetime import UTC, datetime, timedelta

import structlog
from kasa import Discover
from prometheus_client import CollectorRegistry, Counter, Gauge

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
            self.last_checkin[addr] = datetime.now(tz=UTC)
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
        retry_count = 0
        max_retries = 5
        base_delay = 1

        while True:
            try:
                now = datetime.now(tz=UTC)

                # Create a snapshot to avoid race conditions during iteration
                last_checkin_snapshot = dict(self.last_checkin.items())

                to_prune = [
                    addr
                    for addr, last_seen in last_checkin_snapshot.items()
                    if now - last_seen > timedelta(minutes=1)
                ]

                for addr in to_prune:
                    logger.info(f"Pruning device {addr} due to missed check-in")
                    self.devices.pop(addr, None)
                    self.last_checkin.pop(addr, None)
                    self.pruned_devices.inc()  # Increment pruned devices counter

                self.total_devices.set(len(self.devices))  # Update total devices gauge

                # Reset retry count on success
                retry_count = 0
                await asyncio.sleep(10)

            except Exception as e:
                retry_count += 1
                delay = min(base_delay * (2**retry_count), 60)
                logger.error(
                    f"Unexpected error in update_registry (attempt {retry_count}/{max_retries}): "
                    f"{e!s}, retrying in {delay}s"
                )
                if retry_count >= max_retries:
                    logger.critical("Max retries reached in update_registry, resetting retry count")
                    retry_count = 0
                await asyncio.sleep(delay)
