from datetime import datetime
import logging
import asyncio
import os
from kasa import Credentials
from prometheus_client import CollectorRegistry
import structlog
from ..devices.KP125M import Extractor as KP125MDeviceExtractor

# Configure structured logging with timestamp
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    processors=[
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()

class DeviceExporter:
    def __init__(self, device_registry, collector_registry: CollectorRegistry):
        self.device_registry = device_registry
        self.collector_registry = collector_registry
        self.credentials = Credentials(
            os.getenv("KASA_USERNAME"),
            os.getenv("KASA_PASSWORD"),
        )
        # Initialize metrics for device extractors
        for extractor in [KP125MDeviceExtractor]:
            extractor.initialize_metrics(registry=self.collector_registry)

    async def scrape_devices(self):
        interface = {}

        while True:
            await self.device_registry.discover_devices(self.credentials, interface)
            for addr, device in self.device_registry.devices.items():
                try:
                    await device.update()
                    self.device_registry.last_checkin[addr] = datetime.now()
                    logger.info(
                        "Discovered and scraping device",
                        alias=device.alias,
                        model=device.model,
                        address=addr,
                    )
                    KP125MDeviceExtractor.update_metrics(device)
                except Exception as e:
                    logger.error(f"Error updating device {addr}: {str(e)}")
                finally:
                    await device.disconnect()

            await asyncio.sleep(10)
