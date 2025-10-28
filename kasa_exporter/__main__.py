import asyncio
import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
from prometheus_client import CollectorRegistry, generate_latest

from kasa_exporter.routines.device_registry import DeviceRegistry
from kasa_exporter.routines.exporter import DeviceExporter
from kasa_exporter.routines.pushgateway import PushGateway

# Get log level from environment variable (default to INFO)
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    processors=[
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()

# Startup banner with configuration
logger.info("=" * 70)
logger.info("🏠 KASA EXPORTER STARTING UP")
logger.info("=" * 70)
logger.info("Configuration:")
logger.info(f"  📊 Metrics Port: {os.getenv('METRICS_PORT', '8000')}")
logger.info(f"  📝 Log Level: {log_level_name}")
logger.info(f"  👤 Kasa Username: {os.getenv('KASA_USERNAME', 'NOT SET')}")
logger.info(f"  🔑 Kasa Password: {'*' * len(os.getenv('KASA_PASSWORD', '')) if os.getenv('KASA_PASSWORD') else 'NOT SET'}")
logger.info(f"  🌐 mDNS Interface: {os.getenv('MDNS_INTERFACE', 'auto-detect')}")
logger.info(f"  🚀 Push Gateway Host: {os.getenv('PUSH_GATEWAY_HOST', 'localhost')}")
logger.info(f"  🚀 Push Gateway Port: {os.getenv('PUSH_GATEWAY_PORT', '9091')}")
logger.info(f"  🚀 Push Gateway Enabled: {os.getenv('PUSH_GATEWAY_DISABLED', 'true').lower() != 'true'}")
logger.info("=" * 70)

# Note if you want to push to the gateway as well as scrape, you need to clone the registry, pushing
# it increments the registry to its next scrape state
collector_registry = CollectorRegistry()
device_registry = DeviceRegistry(collector_registry)
device_exporter = DeviceExporter(device_registry, collector_registry)
push_gateway = PushGateway(collector_registry)


# Global task tracking for health checks
background_tasks = []


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global background_tasks
    # Start background tasks and store references for cleanup
    background_tasks = [
        asyncio.create_task(device_exporter.scrape_devices(), name="device_scraper"),
        asyncio.create_task(push_gateway.push_to_gateway(), name="push_gateway"),
        asyncio.create_task(device_registry.update_registry(), name="registry_updater"),
    ]

    try:
        yield
    finally:
        # Cancel all tasks and wait for them to finish
        logger.info("Shutting down background tasks")
        for task in background_tasks:
            task.cancel()

        # Wait for cancellation to complete, ignoring CancelledError
        await asyncio.gather(*background_tasks, return_exceptions=True)
        logger.info("All background tasks stopped")


app = FastAPI(lifespan=lifespan, title="Kasa Exporter", version="0.1.0")


@app.get("/metrics")
async def get_metrics():
    metrics_data = generate_latest(collector_registry)
    return PlainTextResponse(content=metrics_data, media_type="text/plain")


@app.get("/debug")
async def debug_device():
    devices_info = device_registry.get_devices_info()
    return {"devices": devices_info}


@app.get("/health")
async def health_check():
    """Health check endpoint to verify all background tasks are running"""
    global background_tasks

    task_statuses = []
    all_healthy = True

    for task in background_tasks:
        is_done = task.done()
        is_cancelled = task.cancelled()

        # Task is unhealthy if it's done but not cancelled (means it crashed)
        is_healthy = not is_done or is_cancelled

        status = {
            "name": task.get_name(),
            "running": not is_done,
            "cancelled": is_cancelled,
            "healthy": is_healthy,
        }

        # If task is done and not cancelled, it crashed - get exception
        if is_done and not is_cancelled:
            try:
                task.exception()
                status["error"] = str(task.exception())
            except Exception:
                pass

        task_statuses.append(status)
        all_healthy = all_healthy and is_healthy

    response = {
        "status": "healthy" if all_healthy else "unhealthy",
        "tasks": task_statuses,
        "device_count": len(device_registry.devices),
    }

    # Return 503 if unhealthy for proper health check integration
    if not all_healthy:
        from fastapi import Response

        return Response(content=str(response), status_code=503, media_type="application/json")

    return response


@app.get("/ready")
async def readiness_check():
    """Readiness check to verify the app has discovered at least one device"""
    device_count = len(device_registry.devices)
    is_ready = device_count > 0

    response = {"ready": is_ready, "device_count": device_count}

    if not is_ready:
        from fastapi import Response

        return Response(content=str(response), status_code=503, media_type="application/json")

    return response


@app.get("/", response_class=HTMLResponse)
async def homepage():
    devices_info = device_registry.get_devices_info()
    total_devices = len(devices_info)

    # Build device cards HTML
    device_cards = ""
    for dev in devices_info:
        device_cards += f"""
        <div class="device-card">
            <h3>{dev["alias"]}</h3>
            <p class="model">{dev["model"]}</p>
            <p class="address">{dev["address"]}</p>
            <p class="status online">● Online</p>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kasa Exporter Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 2rem;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            h1 {{
                color: white;
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }}
            .subtitle {{
                color: rgba(255,255,255,0.9);
                margin-bottom: 2rem;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }}
            .stat-card {{
                background: white;
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .stat-number {{
                font-size: 2.5rem;
                font-weight: bold;
                color: #667eea;
            }}
            .stat-label {{
                color: #666;
                margin-top: 0.5rem;
            }}
            .devices-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 1rem;
            }}
            .device-card {{
                background: white;
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }}
            .device-card:hover {{
                transform: translateY(-4px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.15);
            }}
            .device-card h3 {{
                color: #333;
                margin-bottom: 0.5rem;
            }}
            .model {{
                color: #667eea;
                font-size: 0.9rem;
                margin-bottom: 0.5rem;
            }}
            .address {{
                color: #999;
                font-size: 0.85rem;
                font-family: monospace;
                margin-bottom: 0.5rem;
            }}
            .status {{
                font-weight: bold;
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                display: inline-block;
            }}
            .status.online {{
                color: #10b981;
            }}
            .links {{
                margin-top: 2rem;
                display: flex;
                gap: 1rem;
            }}
            .link-button {{
                background: white;
                color: #667eea;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 500;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: all 0.2s;
            }}
            .link-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }}
        </style>
        <script>
            // Auto-refresh every 10 seconds
            setTimeout(() => location.reload(), 10000);
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🏠 Kasa Exporter Dashboard</h1>
            <p class="subtitle">Real-time monitoring for your smart home devices</p>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{total_devices}</div>
                    <div class="stat-label">Total Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_devices}</div>
                    <div class="stat-label">Online Now</div>
                </div>
            </div>

            <h2 style="color: white; margin-bottom: 1rem;">Connected Devices</h2>
            <div class="devices-grid">
                {device_cards}
            </div>

            <div class="links">
                <a href="/metrics" class="link-button">📊 Prometheus Metrics</a>
                <a href="/debug" class="link-button">🔧 Debug Info</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("METRICS_PORT", 8000)))
