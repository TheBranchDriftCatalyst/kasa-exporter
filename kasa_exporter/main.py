import asyncio
from contextlib import asynccontextmanager
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

# Note if you want to push to the gateway as well as scrape, you need to clone the registry, pushing
# it increments the registry to its next scrape state
collector_registry = CollectorRegistry()
device_registry = DeviceRegistry(collector_registry)
device_exporter = DeviceExporter(device_registry, collector_registry)
push_gateway = PushGateway(collector_registry)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load the ML model
    asyncio.create_task(device_exporter.scrape_devices())
    asyncio.create_task(push_gateway.push_to_gateway())
    asyncio.create_task(device_registry.update_registry())
    yield
    
app = FastAPI(lifespan=lifespan, title="Kasa Exporter", version="0.1.0")

@app.get("/metrics")
async def get_metrics():
    metrics_data = generate_latest(collector_registry)
    return PlainTextResponse(content=metrics_data, media_type="text/plain")

@app.get("/debug")
async def debug_device():
    devices_info = device_registry.get_devices_info()
    return {"devices": devices_info}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("METRICS_PORT", 8000)))
