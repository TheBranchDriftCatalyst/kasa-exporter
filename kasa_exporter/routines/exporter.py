import asyncio
import os
from datetime import UTC, datetime

import structlog
from kasa import Credentials
from prometheus_client import CollectorRegistry

from ..devices.KP125M import Extractor as KP125MDeviceExtractor

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

    async def scrape_devices(self):  # noqa: PLR0912, PLR0915
        # Configure interface for mDNS discovery
        interface = {}
        mdns_interface = os.getenv("MDNS_INTERFACE")
        if mdns_interface:
            interface = {"interface": mdns_interface}
            logger.info(f"Using mDNS interface: {mdns_interface}")
        else:
            logger.info("Using auto-detect for mDNS interface")

        retry_count = 0
        max_retries = 5
        base_delay = 1

        while True:
            try:
                # Discover devices with timeout (30 seconds)
                await asyncio.wait_for(
                    self.device_registry.discover_devices(self.credentials, interface), timeout=30.0
                )

                # Create a snapshot of devices to avoid race conditions
                devices_snapshot = list(self.device_registry.devices.items())

                for addr, device in devices_snapshot:
                    try:
                        # Update device with timeout (10 seconds per device)
                        await asyncio.wait_for(device.update(), timeout=10.0)
                        self.device_registry.last_checkin[addr] = datetime.now(tz=UTC)
                        logger.info(
                            "Discovered and scraping device",
                            alias=device.alias,
                            model=device.model,
                            address=addr,
                        )
                        KP125MDeviceExtractor.update_metrics(device)
                    except TimeoutError:
                        logger.warning(f"Timeout updating device {addr}, will retry next cycle")
                    except OSError as e:
                        if e.errno == 65:  # EHOSTUNREACH - No route to host
                            logger.warning(
                                f"Device {addr} ({device.alias}) unreachable (No route to host). "
                                f"Check network connectivity or device may be offline."
                            )
                        else:
                            logger.error(f"OS error updating device {addr}: {e!s}")
                    except Exception as e:
                        logger.error(f"Error updating device {addr}: {e!s}")
                    finally:
                        try:
                            await asyncio.wait_for(device.disconnect(), timeout=5.0)
                        except Exception as e:
                            logger.warning(f"Error disconnecting from {addr}: {e!s}")

                # Reset retry count on successful scrape
                retry_count = 0
                await asyncio.sleep(10)

            except TimeoutError:
                retry_count += 1
                delay = min(base_delay * (2**retry_count), 60)
                logger.error(
                    f"Device discovery timed out (attempt {retry_count}/{max_retries}), "
                    f"retrying in {delay}s"
                )
                if retry_count >= max_retries:
                    logger.critical("Max retries reached, resetting interface and retry count")
                    interface = {}  # Reset interface on repeated failures
                    retry_count = 0
                await asyncio.sleep(delay)

            except Exception as e:
                retry_count += 1
                delay = min(base_delay * (2**retry_count), 60)
                logger.error(
                    f"Unexpected error in scrape_devices (attempt {retry_count}/{max_retries}): "
                    f"{e!s}, retrying in {delay}s"
                )
                if retry_count >= max_retries:
                    logger.critical("Max retries reached, resetting state")
                    interface = {}
                    retry_count = 0
                await asyncio.sleep(delay)
