import asyncio
import logging
import os

import structlog
from prometheus_client import CollectorRegistry, push_to_gateway

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
        self.pg_disabled = os.getenv("PUSH_GATEWAY_DISABLED", "true").lower() == "true"

    async def push_to_gateway(self):
        retry_count = 0
        max_retries = 5
        base_delay = 1
        consecutive_failures = 0
        max_consecutive_failures = 10

        while True:
            try:
                if not self.pg_disabled:
                    try:
                        # Run synchronous push_to_gateway in executor with timeout
                        await asyncio.wait_for(
                            asyncio.to_thread(
                                push_to_gateway,
                                f"{self.pg_host}:{self.pg_port}",
                                job="kasa_exporter",
                                registry=self.collector_registry,
                            ),
                            timeout=10.0,
                        )
                        logger.info("Pushed metrics to gateway")
                        consecutive_failures = 0  # Reset on success
                    except TimeoutError:
                        consecutive_failures += 1
                        logger.warning(
                            f"Timeout pushing to gateway (consecutive failures: {consecutive_failures})"
                        )
                    except Exception as e:
                        consecutive_failures += 1
                        logger.error(
                            f"Failed to push metrics to gateway: {e!s} "
                            f"(consecutive failures: {consecutive_failures})"
                        )

                    # If too many consecutive failures, temporarily back off
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning(
                            f"Too many consecutive push failures ({consecutive_failures}), "
                            "backing off for 60s"
                        )
                        await asyncio.sleep(60)
                        consecutive_failures = 0  # Reset after backoff
                        continue

                # Reset retry count on successful iteration
                retry_count = 0
                await asyncio.sleep(10)

            except Exception as e:
                retry_count += 1
                delay = min(base_delay * (2**retry_count), 60)
                logger.error(
                    f"Unexpected error in push_to_gateway loop (attempt {retry_count}/{max_retries}): "
                    f"{e!s}, retrying in {delay}s"
                )
                if retry_count >= max_retries:
                    logger.critical("Max retries reached in push_to_gateway, resetting retry count")
                    retry_count = 0
                await asyncio.sleep(delay)
