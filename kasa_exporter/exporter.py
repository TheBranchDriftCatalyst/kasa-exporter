import logging
import asyncio
import os
from kasa import Credentials, Discover
# import kasa
# from requests import request
import structlog
from prometheus_client import generate_latest, push_to_gateway, start_http_server, CollectorRegistry
from fastapi import FastAPI
# from kasa_exporter.device_registry import DeviceRegistry
from .devices.KP125M import KP125M

# Configure structured logging with timestamp
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    processors=[
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()

app = FastAPI()

collector_registry = CollectorRegistry()

KP125M_device_extractor = KP125M(collector_registry)

@app.get("/metrics")
async def get_metrics():
    return generate_latest(collector_registry)


async def pushgateway():
    push_to_gateway("localhost:9091", job="kasa_exporter", registry=collector_registry)


async def main():

    # Start up the Prometheus HTTP server
    port = os.getenv("METRICS_PORT", 8000)
    start_http_server(port, registry=collector_registry)

    logger.info(
        f"Starting Kasa Exporter on port {port}",
    )

    # env = {
    #     "kasa_username": os.getenv("KASA_USERNAME"),
    #     "kasa_password": os.getenv("KASA_PASSWORD"),
    #     "pushgateway_url": os.getenv("PUSHGATEWAY_URL"),
    #     "pushgateway_job": os.getenv("PUSHGATEWAY_JOB", 'kasa_exporter'),
    #     "pushgateway_interval": os.getenv("PUSHGATEWAY_INTERVAL", 10),
    # }

    for extractor in [KP125M_device_extractor]:
        extractor.initialize_metrics()

    credentials = Credentials(
        os.getenv("KASA_USERNAME"),
        os.getenv("KASA_PASSWORD"),
    )  

    interface = {
        # "target": "192.168.1.255"
        # "interface": "eth0"
    }

    while True:
        found_devices = await Discover.discover(credentials=credentials, **interface)
        for addr, device in found_devices.items():
            await device.update()
            logger.info(
                "Discovered and scraping device", alias=device.alias, model=device.model, address=addr
            )
            KP125M_device_extractor.update_metrics(device)

        # TODO: add the pushgateway here if it is enabled
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
