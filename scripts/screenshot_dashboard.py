#!/usr/bin/env python3
"""
Screenshot Grafana dashboards using Grafana's Image Rendering API.

Usage:
    poetry run python scripts/screenshot_dashboard.py
    # Or with custom dashboard UID:
    poetry run python scripts/screenshot_dashboard.py --dashboard "kasa-power-analytics"
"""
import os
import sys
import re
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import requests
from PIL import Image


# Grafana configuration
GRAFANA_BASE_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")

# Paths
SCREENSHOT_DIR = Path(__file__).parent.parent / "docs" / "screenshots"
DASHBOARDS_DIR = Path(__file__).parent.parent / "etc" / "grafana" / "dashboards"


def discover_dashboards():
    """
    Automatically discover dashboards from provisioning folder.

    Returns:
        List of dashboard dictionaries with name, uid, title
    """
    dashboards = []

    # Find all .json files in dashboards directory
    for json_file in DASHBOARDS_DIR.glob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)

            uid = data.get("uid")
            title = data.get("title")

            if uid and title:
                dashboards.append({
                    "name": json_file.stem,  # Filename without extension
                    "uid": uid,
                    "title": title,
                    "from": "now-15m",
                    "to": "now",
                })
                print(f"   Found dashboard: {title} (uid={uid})")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"   ⚠️  Skipping {json_file.name}: {e}")
            continue

    return dashboards


def autocrop_image(image_path: Path, bg_threshold: int = 25) -> None:
    """
    Automatically crop excess dark background from bottom of image.

    Grafana's dark theme background is RGB(17,18,23) with max=23.
    We use threshold of 25 to distinguish actual content from background.

    Args:
        image_path: Path to the image file
        bg_threshold: Threshold for background detection (default 25 for Grafana dark theme)
    """
    img = Image.open(image_path)

    # Convert to RGB if necessary
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Scan from bottom up to find last row with content
    width, height = img.size

    # Start from bottom and work up, find first row with visible content
    crop_height = height

    for y in range(height - 1, -1, -1):
        # Sample pixels across the width
        pixels = [img.getpixel((x, y)) for x in range(0, width, 20)]  # Sample every 20px

        # Calculate average of max RGB values across samples
        avg_max = sum(max(p) for p in pixels) / len(pixels)

        # If average max value exceeds threshold, we found content
        if avg_max > bg_threshold:
            # Found content row - crop with padding
            crop_height = min(y + 100, height)
            break

    # Only crop if we're removing significant space (more than 200px)
    pixels_to_remove = height - crop_height
    if pixels_to_remove > 200:
        print(f"   → Cropping from {height}px to {crop_height}px (removing {pixels_to_remove}px)")
        cropped = img.crop((0, 0, width, crop_height))
        cropped.save(image_path)
    else:
        print(f"   → No significant empty space to crop (would only remove {pixels_to_remove}px)")


def take_dashboard_screenshot(
    dashboard_uid: str,
    output_path: Path,
    time_from: str = "now-15m",
    time_to: str = "now",
    width: int = 1920,
    height: int = 4000,  # Large height to capture full page
    username: str = GRAFANA_USER,
    password: str = GRAFANA_PASSWORD,
    org_id: int = 1,
    kiosk: bool = True,
):
    """
    Use Grafana's rendering API to capture a dashboard screenshot.

    Args:
        dashboard_uid: Dashboard UID
        output_path: Path to save screenshot
        time_from: Start time for dashboard (e.g., "now-15m")
        time_to: End time for dashboard (e.g., "now")
        width: Screenshot width in pixels
        height: Screenshot height in pixels (None for full page)
        username: Grafana username
        password: Grafana password
        org_id: Grafana organization ID
        kiosk: Hide sidebar and navigation (kiosk mode)
    """
    print(f"📸 Rendering dashboard: {dashboard_uid}")

    # Construct the render URL
    # Format: /render/d/{uid}/{slug}
    render_url = f"{GRAFANA_BASE_URL}/render/d/{dashboard_uid}/{dashboard_uid}"

    params = {
        "orgId": org_id,
        "from": time_from,
        "to": time_to,
        "width": width,
        "timeout": 60,  # Rendering timeout in seconds
    }

    # Always add height parameter
    params["height"] = height

    # Add kiosk mode to hide sidebar/navigation
    if kiosk:
        params["kiosk"] = ""  # Empty value for full kiosk mode (no sidebar, no top nav)

    try:
        print(f"   → Requesting: {render_url}")
        print(f"   → Time range: {time_from} to {time_to}")
        print(f"   → Dimensions: {width}x{height}")

        # Make authenticated request to Grafana's rendering API
        response = requests.get(
            render_url,
            params=params,
            auth=(username, password),
            timeout=120,  # HTTP request timeout
        )

        response.raise_for_status()

        # Save the screenshot
        with open(output_path, "wb") as f:
            f.write(response.content)

        file_size = len(response.content) / 1024  # KB
        print(f"   ✅ Screenshot saved: {output_path} ({file_size:.1f} KB)")

        # Auto-crop excess black space
        autocrop_image(output_path)

        # Get final file size after cropping
        final_size = output_path.stat().st_size / 1024  # KB
        print(f"   ✅ Final size after cropping: {final_size:.1f} KB")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error rendering dashboard: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response status: {e.response.status_code}")
            print(f"   Response body: {e.response.text[:500]}")
        raise


def main():
    """Take screenshots of all discovered dashboards."""
    # Ensure output directory exists
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"🎬 Grafana Dashboard Screenshot Tool")
    print(f"   Output dir: {SCREENSHOT_DIR}")
    print()

    # Check if custom dashboard UID provided via command line
    if len(sys.argv) > 1 and sys.argv[1] == "--dashboard":
        if len(sys.argv) < 3:
            print("Error: --dashboard requires a dashboard UID argument")
            sys.exit(1)

        custom_uid = sys.argv[2]
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = SCREENSHOT_DIR / f"custom-dashboard-{timestamp}.png"

        take_dashboard_screenshot(custom_uid, output_file)
        return

    # Auto-discover dashboards from provisioning folder
    print("🔍 Discovering dashboards...")
    dashboards = discover_dashboards()

    if not dashboards:
        print(f"   ⚠️  No dashboards found in {DASHBOARDS_DIR}")
        sys.exit(1)

    print(f"   Found {len(dashboards)} dashboard(s)")
    print()

    # Screenshot all discovered dashboards
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    for dashboard in dashboards:
        name = dashboard["name"]
        uid = dashboard["uid"]
        title = dashboard["title"]
        time_from = dashboard.get("from", "now-15m")
        time_to = dashboard.get("to", "now")

        # Output filename with timestamp
        output_file = SCREENSHOT_DIR / f"{name}-{timestamp}.png"

        print(f"📊 {title}")
        try:
            take_dashboard_screenshot(
                dashboard_uid=uid,
                output_path=output_file,
                time_from=time_from,
                time_to=time_to,
            )
        except Exception as e:
            print(f"   ❌ Failed to screenshot {name}: {e}")
            continue
        print()

    print(f"✅ Done! Screenshots saved to: {SCREENSHOT_DIR}")


if __name__ == "__main__":
    main()
