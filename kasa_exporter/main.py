import asyncio
import logging
import os
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import CollectorRegistry, generate_latest
import structlog

from kasa_exporter.routines.device_registry import DeviceRegistry
from kasa_exporter.routines.exporter import DeviceExporter
from kasa_exporter.routines.pushgateway import PushGateway

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

device_registry = DeviceRegistry(collector_registry)
device_exporter = DeviceExporter(device_registry, collector_registry)
push_gateway = PushGateway(collector_registry)
# The backtick character (`) in Python is used to represent a multi-line string literal. It allows you
# to create a string that spans multiple lines without using explicit newline characters (\n). This
# can be useful for defining long strings or blocks of text in a more readable format within your
# code.

@app.get("/metrics")
async def get_metrics():
    metrics_data = generate_latest(collector_registry)
    return PlainTextResponse(content=metrics_data, media_type="text/plain")


@app.get("/debug")
async def debug_device():
    devices_info = device_registry.get_devices_info()
    return {"devices": devices_info}


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(device_exporter.scrape_devices())
    asyncio.create_task(push_gateway.push_to_gateway())
    asyncio.create_task(device_registry.update_registry())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("METRICS_PORT", 8000)))
