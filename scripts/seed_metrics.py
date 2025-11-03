#!/usr/bin/env python3
"""
Seed Prometheus with a full day's worth of realistic power consumption metrics.

This script generates 24 hours of historical data with realistic usage patterns
and writes directly to Prometheus using the remote write API with proper timestamps.

Usage patterns:
- Night hours (12am-6am): Low baseline usage
- Morning hours (6am-9am): Ramp up as devices activate
- Day hours (9am-5pm): Moderate to high sustained usage
- Evening hours (5pm-10pm): Peak usage (cooking, entertainment, etc.)
- Late evening (10pm-12am): Wind down period
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from scipy.signal.windows import gaussian

# Device definitions based on current metrics
DEVICES = [
    {
        "alias": "Dream Machine",
        "device_id": "803A8E059228352E87967BD82DCBA06122588678",
        "model": "KP125M",
        "baseline_watts": 50,
        "variation": 10,
        "pattern": "constant",
    },
    {
        "alias": "Reality Forge",
        "device_id": "803A23F06D7211C4D09368C654B849762282467E",
        "model": "KP125M",
        "baseline_watts": 5,
        "variation": 5,
        "pattern": "occasional",
    },
    {
        "alias": "6985",
        "device_id": "803AD6935764643857F377445DB8FB0F2258182B",
        "model": "KP125M",
        "baseline_watts": 150,
        "variation": 50,
        "pattern": "workday",
    },
    {
        "alias": "Furbo",
        "device_id": "803A2BC059F51E9BDC5D471D6481E907228286B1",
        "model": "KP125M",
        "baseline_watts": 3,
        "variation": 2,
        "pattern": "constant",
    },
    {
        "alias": "Lab Server",
        "device_id": "803AC99E58A6AC51871091C0D3755E3B2282C74C",
        "model": "KP125M",
        "baseline_watts": 8,
        "variation": 15,
        "pattern": "workday",
    },
    {
        "alias": "Fatboy Synology",
        "device_id": "803A5D96B6516ABA75D62FF0A03CCD6A2282B060",
        "model": "KP125M",
        "baseline_watts": 45,
        "variation": 30,
        "pattern": "variable",
    },
]

# Time-of-Use rate structure (winter season)
TOU_RATES = {
    "super_off_peak": 0.314,
    "off_peak": 0.351,
    "on_peak": 0.634,
}


def get_rate_class(hour: int) -> str:
    """Determine TOU rate class for a given hour."""
    if 0 <= hour < 6 or 22 <= hour < 24:
        return "super_off_peak"
    if 16 <= hour < 21:
        return "on_peak"
    return "off_peak"


def smooth_noise(x, scale=0.1):
    """Generate smooth Perlin-like noise using sine waves."""
    return (
        np.sin(x * scale) * 0.3
        + np.sin(x * scale * 2.3) * 0.15
        + np.sin(x * scale * 4.7) * 0.08
        + np.sin(x * scale * 8.1) * 0.04
    )


def get_daily_curve(hour_fraction: float, pattern: str) -> float:
    """
    Get smooth daily usage curve (0.0 to 1.0 through the day).

    Args:
        hour_fraction: Current position in day (0.0 = midnight, 1.0 = next midnight)
        pattern: Device usage pattern type
    """
    # Convert to radians (full day = 2π)
    t = hour_fraction * 2 * np.pi

    if pattern == "constant":
        # Minimal variation - just gentle breathing
        return 1.0 + np.sin(t) * 0.05 + np.cos(t * 3) * 0.02

    if pattern == "workday":
        # Low at night, ramp up morning, peak midday, taper evening
        # Use combination of sine waves to create realistic work pattern
        night_dip = np.clip(1.0 - np.cos(t), 0, 1) * 0.5  # 0.0-0.5 multiplier overnight
        day_boost = np.sin(t - np.pi / 2) * 0.3  # Boost during day (shifted sine)
        lunch_dip = -np.sin((t - np.pi) * 2) * 0.1  # Small dip at lunch

        base = 0.6 + night_dip + day_boost + lunch_dip
        return np.clip(base, 0.5, 1.5)

    if pattern == "variable":
        # More dynamic - follows household activity patterns
        # Morning spike (6-9am)
        morning_spike = np.exp(-((hour_fraction - 0.3) ** 2) / 0.01) * 0.4
        # Evening spike (5-10pm)
        evening_spike = np.exp(-((hour_fraction - 0.75) ** 2) / 0.015) * 0.6
        # Gentle overnight taper
        night_base = 0.6 + np.cos(t) * 0.2

        return np.clip(night_base + morning_spike + evening_spike, 0.6, 1.8)

    if pattern == "occasional":
        # Random on/off periods with smooth transitions
        # Use low frequency sine to create occasional bursts
        on_probability = (np.sin(t * 0.7) + 1) / 2  # 0 to 1
        return 1.0 if on_probability > 0.7 else 0.3

    return 1.0


def get_usage_multiplier(
    time_index: int, total_points: int, pattern: str, device_seed: int = 0
) -> float:
    """
    Get smooth usage multiplier with realistic variation.

    Args:
        time_index: Current sample index
        total_points: Total samples in the period
        pattern: Device usage pattern type
        device_seed: Seed for per-device variation
    """
    # Calculate position in day (0.0 to 1.0)
    hour_fraction = (time_index / total_points) % 1.0

    # Get base daily curve
    base_curve = get_daily_curve(hour_fraction, pattern)

    # Add smooth noise for micro-variations
    noise = smooth_noise(time_index + device_seed * 1000, scale=0.02)

    # Combine with small random walk for realism
    random_walk = noise * 0.15

    return base_curve * (1.0 + random_walk)


def calculate_cost(watts: float, rate_class: str) -> float:
    """Calculate cost in $/hr for given watts and rate class."""
    kwh = watts / 1000.0
    return kwh * TOU_RATES[rate_class]


def create_timeseries(metric_name: str, labels: dict[str, str], samples: list[tuple]) -> dict:
    """
    Create a time series dict in Prometheus remote write format.

    Args:
        metric_name: Name of the metric
        labels: Dict of label key-value pairs
        samples: List of (timestamp_ms, value) tuples
    """
    # Create labels list
    label_list = [{"name": "__name__", "value": metric_name}]
    for key, value in labels.items():
        label_list.append({"name": key, "value": value})

    # Create samples list
    sample_list = []
    for ts_ms, value in samples:
        sample_list.append({"timestamp": ts_ms, "value": value})

    return {"labels": label_list, "samples": sample_list}


def write_to_prometheus(
    timeseries_list: list[dict], prometheus_url: str = "http://localhost:9090"
) -> str:
    """
    Write timeseries data directly to Prometheus using remote write API.

    This uses a simplified approach: writing metrics in OpenMetrics format
    directly to Prometheus's admin API for loading data.
    """
    # Build OpenMetrics format text with timestamps
    metrics_text = ""

    for ts in timeseries_list:
        # Extract metric name and labels
        metric_name = None
        labels_dict = {}

        for label in ts["labels"]:
            if label["name"] == "__name__":
                metric_name = label["value"]
            else:
                labels_dict[label["name"]] = label["value"]

        # Build label string
        if labels_dict:
            labels_str = ",".join([f'{k}="{v}"' for k, v in labels_dict.items()])
            labels_str = "{" + labels_str + "}"
        else:
            labels_str = ""

        # Add all samples for this timeseries
        for sample in ts["samples"]:
            metrics_text += f"{metric_name}{labels_str} {sample['value']} {sample['timestamp']}\n"

    # Write to a temp file and use promtool to inject it
    # OR use the admin API if available
    # For now, let's return the metrics text for manual injection
    return metrics_text


def seed_day_direct(  # noqa: PLR0915
    hours: int = 24, interval_seconds: int = 10, prometheus_url: str = "http://localhost:9090"
):
    """
    Generate a full day's worth of metrics and write directly to Prometheus.

    Since Prometheus doesn't have a simple "inject historical data" API,
    we'll generate the data in OpenMetrics format and provide instructions
    for loading it.
    """
    # Avoid the last 3 hours as per Prometheus docs (current head block)
    start_time = datetime.now(tz=UTC) - timedelta(hours=hours + 3)
    num_points = int(hours * 3600 / interval_seconds)

    print("🌱 Generating seed data for Prometheus")
    print(f"📅 Start time: {start_time}")
    print(f"⏰ Duration: {hours} hours")
    print(f"📊 Interval: {interval_seconds} seconds")
    print(f"📈 Total data points: {num_points} per device")
    print(f"🎯 Total samples: {num_points * len(DEVICES) * 3} (3 metrics per device)")
    print()

    all_timeseries = []

    # Generate data for each device
    for device_idx, device in enumerate(DEVICES):
        labels = {
            "alias": device["alias"],
            "device_id": device["device_id"],
            "model": device["model"],
            "version": "mock",
        }

        consumption_raw = []
        timestamps = []

        # First pass: Generate raw smooth consumption values
        for i in range(num_points):
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            timestamps.append(timestamp.timestamp())

            # Generate smooth consumption using wave functions
            multiplier = get_usage_multiplier(
                i, num_points, device["pattern"], device_seed=device_idx
            )
            watts = device["baseline_watts"] * multiplier

            # Add minimal gaussian noise (2% of variation instead of 10%)
            watts += np.random.normal(0, device["variation"] * 0.02)
            watts = max(0, watts)

            consumption_raw.append(watts)

        # Second pass: Apply aggressive moving average smoothing
        window_size = 180  # 30 minutes of smoothing (180 samples * 10 seconds)
        # Use Gaussian window for smoother edges
        window = gaussian(window_size, std=window_size / 6)
        window = window / window.sum()  # Normalize

        consumption_smooth = np.convolve(consumption_raw, window, mode="same")

        # Third pass: Create final samples with timestamps
        consumption_samples = []
        cost_samples = []

        for i in range(num_points):
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            hour = timestamp.hour
            rate_class = get_rate_class(hour)

            watts = consumption_smooth[i]
            cost = calculate_cost(watts, rate_class)

            consumption_samples.append((timestamps[i], watts))
            cost_samples.append((timestamps[i], cost))

        # Create timeseries for this device
        all_timeseries.append(create_timeseries("current_consumption", labels, consumption_samples))
        all_timeseries.append(create_timeseries("consumption_cost", labels, cost_samples))

        print(f"✅ Generated {len(consumption_samples)} samples for {device['alias']}")

    # Add energy rate metrics (current values, not historical)
    for device in DEVICES:
        for rate_name, rate_value in TOU_RATES.items():
            labels = {
                "alias": device["alias"],
                "device_id": device["device_id"],
                "model": device["model"],
                "version": "mock",
                "rate_class": rate_name,
                "season": "winter",
            }
            # Just use current timestamp for rate info (in seconds)
            current_ts = datetime.now(tz=UTC).timestamp()
            all_timeseries.append(
                create_timeseries("current_energy_rate", labels, [(current_ts, rate_value)])
            )

    print()
    print("📝 Generating OpenMetrics format...")
    metrics_text = write_to_prometheus(all_timeseries, prometheus_url)

    # Write to file (OpenMetrics format requires # EOF at the end)
    output_file = Path("seed_data.txt")
    with output_file.open("w") as f:
        f.write(metrics_text)
        f.write("# EOF\n")

    print(f"✅ Wrote {len(metrics_text.splitlines())} metric lines to {output_file}")
    print()
    print("📋 To load this data into Prometheus:")
    print("   1. Stop Prometheus:")
    print("      docker compose stop prometheus")
    print()
    print("   2. Create TSDB blocks from the seed data:")
    print(
        f"      docker run --rm -v $(pwd)/{output_file}:/{output_file} -v $(pwd)/.promdb:/prometheus \\"
    )
    print(
        f"        prom/prometheus:latest promtool tsdb create-blocks-from openmetrics /{output_file} /prometheus"
    )
    print()
    print(
        "   3. Start Prometheus (may need --storage.tsdb.allow-overlapping-blocks if there's overlap):"
    )
    print("      docker compose start prometheus")
    print()
    print("   Note: Data is placed 3+ hours in the past to avoid the current head block")


def preview_daily_pattern():
    """Preview the daily consumption pattern for each device."""
    print("📈 Daily Consumption Pattern Preview")
    print("=" * 80)
    print()

    num_samples = 24 * 6  # Every 10 minutes for 24 hours

    for device_idx, device in enumerate(DEVICES):
        print(f"Device: {device['alias']} ({device['pattern']} pattern)")
        print(f"  Baseline: {device['baseline_watts']}W ± {device['variation']}W")

        # Generate 24 hours of smooth data with moving average
        consumption_raw = []
        for i in range(num_samples):
            multiplier = get_usage_multiplier(
                i, num_samples, device["pattern"], device_seed=device_idx
            )
            watts = device["baseline_watts"] * multiplier
            watts += np.random.normal(0, device["variation"] * 0.02)
            watts = max(0, watts)
            consumption_raw.append(watts)

        # Apply aggressive Gaussian smoothing
        window_size = 180
        window = gaussian(window_size, std=window_size / 6)
        window = window / window.sum()

        consumption = np.convolve(consumption_raw, window, mode="same")

        print(f"  Min: {min(consumption):.1f}W")
        print(f"  Max: {max(consumption):.1f}W")
        print(f"  Avg: {np.mean(consumption):.1f}W")
        print(f"  Std Dev: {np.std(consumption):.1f}W")
        print(f"  Daily kWh: {sum(consumption) * 10 / 60 / 1000:.2f}")  # 10-min intervals

        # Show sample points throughout the day
        print("  Sample points throughout day:")
        for hour in [0, 6, 12, 18, 22]:
            idx = hour * 6  # 6 samples per hour
            rate_class = get_rate_class(hour)
            cost = calculate_cost(consumption[idx], rate_class)
            print(f"    {hour:02d}:00 - {consumption[idx]:6.1f}W @ ${cost:.4f}/hr ({rate_class})")

        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed Prometheus with daily power metrics")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview daily patterns without generating data",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to generate (default: 24)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Seconds between samples (default: 10)",
    )
    parser.add_argument(
        "--prometheus",
        type=str,
        default="http://localhost:9090",
        help="Prometheus URL (default: http://localhost:9090)",
    )

    args = parser.parse_args()

    if args.preview:
        preview_daily_pattern()
    else:
        seed_day_direct(args.hours, args.interval, args.prometheus)
