#!/usr/bin/env python3
"""
Explode Grafana dashboards into individual panel files for easier editing.

This script splits large dashboard JSON files into:
1. Dashboard metadata file (_dashboard.json)
2. Individual panel files (panel-{id}-{slug}.json)

This enables:
- Editing panels in isolation
- Version control-friendly diffs
- Live reload during development
- Easier collaboration

Usage:
    # Explode all dashboards
    python scripts/utils/explode_dashboards.py

    # Explode specific dashboard
    python scripts/utils/explode_dashboards.py --dashboard 1-real-time-monitoring.json

    # Custom source/destination
    python scripts/utils/explode_dashboards.py --source etc/grafana/dashboards --dest etc/grafana/dashboards/src
"""

import argparse
import json
import re
import sys
from pathlib import Path


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        Slugified text
    """
    # Remove emojis and special chars
    text = re.sub(r"[^\w\s-]", "", text)
    # Replace spaces with hyphens
    text = re.sub(r"[\s_]+", "-", text)
    # Lowercase and remove leading/trailing hyphens
    return text.lower().strip("-")


def explode_dashboard(dashboard_path: Path, output_dir: Path, overwrite: bool = False) -> int:
    """
    Explode a single dashboard into individual panel files.

    Args:
        dashboard_path: Path to dashboard JSON file
        output_dir: Directory to write exploded files to
        overwrite: Whether to overwrite existing files

    Returns:
        Number of panel files created
    """
    # Load dashboard
    with dashboard_path.open() as f:
        dashboard = json.load(f)

    # Create output directory for this dashboard
    dashboard_slug = dashboard_path.stem  # e.g., "1-real-time-monitoring"
    dashboard_output_dir = output_dir / dashboard_slug
    dashboard_output_dir.mkdir(parents=True, exist_ok=True)

    # Extract panels and dashboard metadata separately
    panels = dashboard.pop("panels", [])

    # Save dashboard metadata (everything except panels)
    metadata_file = dashboard_output_dir / "_dashboard.json"
    if metadata_file.exists() and not overwrite:
        print(f"  ⚠️  Skipping {metadata_file.name} (already exists)")
    else:
        with metadata_file.open("w") as f:
            json.dump(dashboard, f, indent=2)
        print(f"  ✅ Created {metadata_file.name}")

    # Save individual panels
    panel_count = 0
    for panel in panels:
        # Skip row panels (they're just layout containers)
        if panel.get("type") == "row":
            continue

        panel_id = panel.get("id", "unknown")
        panel_title = panel.get("title", "untitled")
        panel_slug = slugify(panel_title)

        # Create filename: {id}-{slug}.json
        panel_filename = f"{panel_id}-{panel_slug}.json"
        panel_file = dashboard_output_dir / panel_filename

        if panel_file.exists() and not overwrite:
            print(f"  ⚠️  Skipping {panel_filename} (already exists)")
            continue

        with panel_file.open("w") as f:
            json.dump(panel, f, indent=2)

        print(f"  ✅ Created {panel_filename}")
        panel_count += 1

    return panel_count


def explode_all_dashboards(
    source_dir: Path, output_dir: Path, overwrite: bool = False
) -> dict[str, int]:
    """
    Explode all dashboards in source directory.

    Args:
        source_dir: Directory containing dashboard JSON files
        output_dir: Directory to write exploded files to
        overwrite: Whether to overwrite existing files

    Returns:
        Dictionary mapping dashboard name to panel count
    """
    results = {}

    for dashboard_file in sorted(source_dir.glob("*.json")):
        print(f"\n📦 Exploding {dashboard_file.name}...")
        panel_count = explode_dashboard(dashboard_file, output_dir, overwrite)
        results[dashboard_file.name] = panel_count

    return results


def main():
    """Explode Grafana dashboards into individual panel files."""
    parser = argparse.ArgumentParser(
        description="Explode Grafana dashboards into individual panel files"
    )
    parser.add_argument(
        "--dashboard",
        "-d",
        help="Specific dashboard file to explode (default: all dashboards)",
    )
    parser.add_argument(
        "--source",
        "-s",
        default="etc/grafana/dashboards",
        help="Source directory with dashboard JSON files (default: etc/grafana/dashboards)",
    )
    parser.add_argument(
        "--dest",
        "-o",
        default="etc/grafana/dashboards/src",
        help="Destination directory for exploded files (default: etc/grafana/dashboards/src)",
    )
    parser.add_argument(
        "--overwrite",
        "-f",
        action="store_true",
        help="Overwrite existing files",
    )

    args = parser.parse_args()

    source_dir = Path(args.source)
    output_dir = Path(args.dest)

    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return 1

    print(f"Source: {source_dir}")
    print(f"Destination: {output_dir}")
    print(f"Overwrite: {args.overwrite}")

    # Explode dashboard(s)
    if args.dashboard:
        dashboard_path = source_dir / args.dashboard
        if not dashboard_path.exists():
            print(f"❌ Dashboard file not found: {dashboard_path}")
            return 1

        print(f"\n📦 Exploding {args.dashboard}...")
        panel_count = explode_dashboard(dashboard_path, output_dir, args.overwrite)
        results = {args.dashboard: panel_count}
    else:
        results = explode_all_dashboards(source_dir, output_dir, args.overwrite)

    # Summary
    print("\n" + "=" * 70)
    print("📊 EXPLOSION SUMMARY")
    print("=" * 70)
    total_panels = 0
    for dashboard, count in results.items():
        print(f"{dashboard:50} {count:3} panels")
        total_panels += count

    print("=" * 70)
    print(f"✅ Exploded {len(results)} dashboard(s), {total_panels} total panels")
    print(f"📂 Output: {output_dir}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
