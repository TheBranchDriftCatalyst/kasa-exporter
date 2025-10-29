#!/usr/bin/env python3
"""
Validate Kasa credentials by attempting device discovery.

Usage:
    KASA_USERNAME=user KASA_PASSWORD=pass python validate_credentials.py

Exit codes:
    0 - Credentials valid
    1 - Credentials invalid or error
"""

import asyncio
import os
import sys

from kasa import Credentials, Discover


async def validate():
    """Validate Kasa credentials by attempting device discovery."""
    try:
        username = os.getenv("KASA_USERNAME")
        password = os.getenv("KASA_PASSWORD")

        if not username or not password:
            print("ERROR: Missing credentials", file=sys.stderr)
            return False

        credentials = Credentials(username, password)

        # Attempt device discovery with a short timeout
        devices = await asyncio.wait_for(
            Discover.discover(credentials=credentials),
            timeout=15.0,
        )

        if not devices:
            print("WARNING: No devices found on network", file=sys.stderr)
            print(
                "This could be normal if devices are on a different network segment",
                file=sys.stderr,
            )
            return True  # Credentials validated, just no devices found locally

        print(f"SUCCESS: Found {len(devices)} device(s)", file=sys.stderr)
        for ip, dev in devices.items():
            print(f"  - {dev.alias} ({dev.model}) at {ip}", file=sys.stderr)

        return True

    except TimeoutError:
        print(
            "ERROR: Discovery timed out - check network connectivity",
            file=sys.stderr,
        )
        return False
    except Exception as e:
        error_msg = str(e).lower()
        if (
            "authentication" in error_msg
            or "invalid" in error_msg
            or "credentials" in error_msg
        ):
            print(f"ERROR: Invalid credentials - {e}", file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    result = asyncio.run(validate())
    sys.exit(0 if result else 1)
