import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from prometheus_client import CollectorRegistry, generate_latest

from kasa_exporter.devices.KP125M import calculator
from kasa_exporter.routines.device_registry import DeviceRegistry
from kasa_exporter.routines.exporter import DeviceExporter
from kasa_exporter.routines.pushgateway import PushGateway
from kasa_exporter.utils.build_info import GIT_HASH, VERSION

# Removed: DEFAULT_TIME_OF_USE_CONFIG import - now using calculator.config

# Get log level from environment variable (default to INFO)
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)

# Use human-friendly console output in dev, JSON in production
log_format = os.getenv("LOG_FORMAT", "console").lower()
if log_format == "json":
    renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
else:
    renderer = structlog.dev.ConsoleRenderer(
        colors=True,
        pad_event=0,  # Don't pad the event message
    )

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        renderer,
    ],
)

logger = structlog.get_logger()

# Startup banner with configuration
logger.info("=" * 70)
logger.info("🏠 KASA EXPORTER STARTING UP")
logger.info("=" * 70)
logger.info("Configuration:")
logger.info(f"  📦 Version: {VERSION}")
logger.info(f"  🔖 Git Hash: {GIT_HASH}")
logger.info(f"  📊 Metrics Port: {os.getenv('METRICS_PORT', '8000')}")
logger.info(f"  📝 Log Level: {log_level_name}")
logger.info(f"  👤 Kasa Username: {os.getenv('KASA_USERNAME', 'NOT SET')}")
logger.info(
    f"  🔑 Kasa Password: {'*' * len(os.getenv('KASA_PASSWORD', '')) if os.getenv('KASA_PASSWORD') else 'NOT SET'}"
)
logger.info(f"  🌐 mDNS Interface: {os.getenv('MDNS_INTERFACE', 'auto-detect')}")
logger.info(f"  🚀 Push Gateway Host: {os.getenv('PUSH_GATEWAY_HOST', 'localhost')}")
logger.info(f"  🚀 Push Gateway Port: {os.getenv('PUSH_GATEWAY_PORT', '9091')}")
logger.info(
    f"  🚀 Push Gateway Enabled: {os.getenv('PUSH_GATEWAY_DISABLED', 'true').lower() != 'true'}"
)
logger.info("=" * 70)

# Note if you want to push to the gateway as well as scrape, you need to clone the registry, pushing
# it increments the registry to its next scrape state
collector_registry = CollectorRegistry()
device_registry = DeviceRegistry(collector_registry)
device_exporter = DeviceExporter(device_registry, collector_registry)
push_gateway = PushGateway(collector_registry)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Start background tasks and store references for cleanup in app.state
    _app.state.background_tasks = [
        asyncio.create_task(device_exporter.scrape_devices(), name="device_scraper"),
        asyncio.create_task(push_gateway.push_to_gateway(), name="push_gateway"),
        asyncio.create_task(device_registry.update_registry(), name="registry_updater"),
    ]

    try:
        yield
    finally:
        # Cancel all tasks and wait for them to finish
        logger.info("Shutting down background tasks")
        for task in _app.state.background_tasks:
            task.cancel()

        # Wait for cancellation to complete, ignoring CancelledError
        await asyncio.gather(*_app.state.background_tasks, return_exceptions=True)
        logger.info("All background tasks stopped")


app = FastAPI(lifespan=lifespan, title="Kasa Exporter", version="0.2.0")


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
    task_statuses = []
    all_healthy = True

    for task in app.state.background_tasks:
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
        return Response(content=str(response), status_code=503, media_type="application/json")

    return response


@app.get("/ready")
async def readiness_check():
    """Readiness check to verify the app has discovered at least one device"""
    device_count = len(device_registry.devices)
    is_ready = device_count > 0

    response = {"ready": is_ready, "device_count": device_count}

    if not is_ready:
        return Response(content=str(response), status_code=503, media_type="application/json")

    return response


@app.get("/", response_class=HTMLResponse)
async def homepage():
    devices_info = device_registry.get_devices_info()
    total_devices = len(devices_info)

    # Get current season and TOU config for both seasons
    current_season = calculator.get_current_season()

    # Prepare TOU config for JavaScript (include both seasons)
    tou_config_json = json.dumps(
        {
            "current_season": current_season,
            "summer": {
                "rates": calculator.config["summer"]["rate"],
                "super_off_peak": calculator.config["summer"]["super_off_peak"],
                "off_peak": calculator.config["summer"]["off_peak"],
                "on_peak": calculator.config["summer"]["on_peak"],
            },
            "winter": {
                "rates": calculator.config["winter"]["rate"],
                "super_off_peak": calculator.config["winter"]["super_off_peak"],
                "off_peak": calculator.config["winter"]["off_peak"],
                "on_peak": calculator.config["winter"]["on_peak"],
            },
        }
    )

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

            /* TOU Calendar Styles */
            .tou-calendar-section {{
                margin: 3rem 0;
            }}
            .tou-calendar-card {{
                background: white;
                padding: 2rem;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .tou-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1.5rem;
            }}
            .tou-title {{
                color: #333;
                font-size: 1.5rem;
                margin: 0;
            }}
            .season-toggle {{
                display: flex;
                gap: 0.5rem;
                background: #f3f4f6;
                padding: 0.25rem;
                border-radius: 8px;
            }}
            .season-btn {{
                background: transparent;
                border: none;
                color: #6b7280;
                padding: 0.5rem 1rem;
                border-radius: 6px;
                font-weight: 500;
                text-transform: capitalize;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .season-btn:hover {{
                background: rgba(102, 126, 234, 0.1);
                color: #667eea;
            }}
            .season-btn.active {{
                background: #667eea;
                color: white;
            }}
            .tou-legend {{
                display: flex;
                gap: 1.5rem;
                margin-bottom: 1.5rem;
                flex-wrap: wrap;
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            .legend-color {{
                width: 24px;
                height: 24px;
                border-radius: 4px;
            }}
            .legend-color.super-off-peak {{
                background: #10b981;
            }}
            .legend-color.off-peak {{
                background: #fbbf24;
            }}
            .legend-color.on-peak {{
                background: #ef4444;
            }}
            .legend-text {{
                font-size: 0.9rem;
                color: #666;
            }}
            .legend-rate {{
                font-weight: bold;
                color: #333;
            }}
            .calendar-container {{
                overflow-x: auto;
            }}
            .calendar {{
                display: grid;
                grid-template-columns: 60px repeat(7, 1fr);
                gap: 2px;
                min-width: 800px;
            }}
            .calendar-header {{
                background: #f3f4f6;
                padding: 0.75rem;
                text-align: center;
                font-weight: 600;
                color: #333;
                border-radius: 4px;
            }}
            .calendar-header.time {{
                text-align: right;
                padding-right: 0.5rem;
                font-size: 0.75rem;
                color: #666;
            }}
            .calendar-cell {{
                background: #f9fafb;
                padding: 0.5rem;
                text-align: center;
                border-radius: 4px;
                position: relative;
                cursor: pointer;
                transition: all 0.2s;
                min-height: 32px;
            }}
            .calendar-cell.super-off-peak {{
                background: #10b981;
                color: white;
            }}
            .calendar-cell.off-peak {{
                background: #fbbf24;
                color: #1f2937;
            }}
            .calendar-cell.on-peak {{
                background: #ef4444;
                color: white;
            }}
            .calendar-cell.current {{
                box-shadow: 0 0 0 3px #667eea;
                transform: scale(1.05);
                z-index: 10;
            }}
            .calendar-cell:hover {{
                transform: scale(1.1);
                z-index: 20;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
            .tooltip {{
                position: absolute;
                background: #1f2937;
                color: white;
                padding: 0.75rem;
                border-radius: 6px;
                font-size: 0.85rem;
                white-space: nowrap;
                pointer-events: none;
                z-index: 1000;
                opacity: 0;
                transition: opacity 0.2s;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%);
                margin-bottom: 8px;
            }}
            .tooltip::after {{
                content: '';
                position: absolute;
                top: 100%;
                left: 50%;
                transform: translateX(-50%);
                border: 6px solid transparent;
                border-top-color: #1f2937;
            }}
            .calendar-cell:hover .tooltip {{
                opacity: 1;
            }}
            @media (max-width: 768px) {{
                .tou-header {{
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 1rem;
                }}
            }}
        </style>
        <script>
            // TOU Config from backend
            const touConfigData = {tou_config_json};
            let currentSeason = touConfigData.current_season;

            // Get season config
            function getSeasonConfig(season) {{
                return touConfigData[season];
            }}

            // Update legend with current season rates
            function updateLegend(season) {{
                const config = getSeasonConfig(season);
                const legend = document.getElementById('tou-legend');
                legend.innerHTML = `
                    <div class="legend-item">
                        <div class="legend-color super-off-peak"></div>
                        <span><strong>Super Off-Peak:</strong> $${{config.rates.super_off_peak.toFixed(3)}}/kWh</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color off-peak"></div>
                        <span><strong>Off-Peak:</strong> $${{config.rates.off_peak.toFixed(3)}}/kWh</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color on-peak"></div>
                        <span><strong>On-Peak:</strong> $${{config.rates.on_peak.toFixed(3)}}/kWh</span>
                    </div>
                `;
            }}

            // Generate TOU Calendar
            function generateCalendar(season) {{
                const config = getSeasonConfig(season);
                const calendar = document.getElementById('tou-calendar');
                const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

                // Add empty header cell for time column
                calendar.innerHTML = '<div class="calendar-header time"></div>';

                // Add day headers
                days.forEach(day => {{
                    calendar.innerHTML += `<div class="calendar-header">${{day}}</div>`;
                }});

                // Add hourly rows (24 hours)
                for (let hour = 0; hour < 24; hour++) {{
                    // Time label
                    const timeLabel = hour === 0 ? '12am' : hour < 12 ? `${{hour}}am` : hour === 12 ? '12pm' : `${{hour - 12}}pm`;
                    calendar.innerHTML += `<div class="calendar-header time">${{timeLabel}}</div>`;

                    // Cells for each day
                    days.forEach((day, dayIndex) => {{
                        const rateClass = getRateClass(hour, config);
                        const rate = config.rates[rateClass];
                        const cssClass = rateClass.replace(/_/g, '-'); // Convert underscores to hyphens for CSS
                        const now = new Date();
                        const currentHour = now.getHours();
                        const currentDay = (now.getDay() + 6) % 7; // Convert Sunday=0 to Monday=0
                        const isCurrent = hour === currentHour && dayIndex === currentDay && season === currentSeason;

                        const cell = `
                            <div class="calendar-cell ${{cssClass}} ${{isCurrent ? 'current' : ''}}">
                                <div class="tooltip">
                                    ${{timeLabel}} - ${{rateClass.replace(/_/g, ' ')}}<br>
                                    <strong>$${{rate.toFixed(3)}}/kWh</strong>
                                </div>
                            </div>
                        `;
                        calendar.innerHTML += cell;
                    }});
                }}
            }}

            // Determine rate class for a given hour
            function getRateClass(hour, config) {{
                const time = `${{hour.toString().padStart(2, '0')}}:00`;

                // Check each rate period
                for (const [start, end] of config.super_off_peak) {{
                    if (isInTimeRange(time, start, end)) return 'super_off_peak';
                }}
                for (const [start, end] of config.on_peak) {{
                    if (isInTimeRange(time, start, end)) return 'on_peak';
                }}
                for (const [start, end] of config.off_peak) {{
                    if (isInTimeRange(time, start, end)) return 'off_peak';
                }}

                return 'off_peak'; // default
            }}

            // Check if time is in range
            function isInTimeRange(time, start, end) {{
                return time >= start && time < end;
            }}

            // Switch season display
            function switchSeason(season) {{
                // Update button states
                document.querySelectorAll('.season-btn').forEach(btn => {{
                    btn.classList.remove('active');
                    if (btn.dataset.season === season) {{
                        btn.classList.add('active');
                    }}
                }});

                // Regenerate calendar and legend for selected season
                updateLegend(season);
                generateCalendar(season);
            }}

            // Initialize on page load
            window.addEventListener('DOMContentLoaded', () => {{
                // Set active button for current season
                document.querySelectorAll('.season-btn').forEach(btn => {{
                    btn.classList.remove('active');
                    if (btn.dataset.season === currentSeason) {{
                        btn.classList.add('active');
                    }}

                    // Add click handler
                    btn.addEventListener('click', () => {{
                        switchSeason(btn.dataset.season);
                    }});
                }});

                // Initial render
                updateLegend(currentSeason);
                generateCalendar(currentSeason);
            }});

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

            <div class="tou-calendar-section">
                <div class="tou-calendar-card">
                    <div class="tou-header">
                        <h2 class="tou-title">⚡ Time of Use Rate Schedule</h2>
                        <div class="season-toggle">
                            <button class="season-btn active" data-season="summer">Summer</button>
                            <button class="season-btn" data-season="winter">Winter</button>
                        </div>
                    </div>

                    <div id="tou-legend" class="tou-legend">
                        <!-- Legend will be populated by JavaScript -->
                    </div>

                    <div id="tou-calendar" class="calendar"></div>
                </div>
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

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("METRICS_PORT", "8000")))
