import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from kasa import Discover
from prometheus_client import CollectorRegistry, Counter, Gauge

logger = structlog.get_logger()


class DeviceRegistry:
    def __init__(self, collector_registry: CollectorRegistry):
        self.devices = {}
        self.last_checkin = {}
        self.seen_devices = set()  # Track devices that have been discovered at least once

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

        # Only increment counter for NEW devices (not previously seen)
        new_devices_count = 0
        for addr in self.devices:
            if addr not in self.seen_devices:
                self.seen_devices.add(addr)
                new_devices_count += 1
            self.last_checkin[addr] = datetime.now(tz=UTC)

        if new_devices_count > 0:
            self.discovered_devices.inc(new_devices_count)

        self.total_devices.set(len(self.devices))
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
                    # Keep addr in seen_devices so if it returns it won't be counted as "newly discovered"
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
