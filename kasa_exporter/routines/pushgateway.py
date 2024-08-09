import asyncio
from datetime import datetime, timedelta
import logging
import os
from prometheus_client import push_to_gateway, CollectorRegistry
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


class PushGateway:
    def __init__(self, collector_registry: CollectorRegistry):
        self.collector_registry = collector_registry
        self.pg_host = os.getenv("PUSH_GATEWAY_HOST", "localhost")
        self.pg_port = int(os.getenv("PUSH_GATEWAY_PORT", 9091))
        self.pg_disabled = bool(os.getenv("PUSH_GATEWAY_DISABLED", True))

    async def push_to_gateway(self):
        while True:
            if not self.pg_disabled:
                try:
                    push_to_gateway(
                        f"{self.pg_host}:{self.pg_port}",
                        job="kasa_exporter",
                        registry=self.collector_registry,
                    )
                    logger.info("Pushed metrics to gateway")
                except Exception as e:
                    logger.error(f"Failed to push metrics to gateway: {str(e)}")
            await asyncio.sleep(10)
