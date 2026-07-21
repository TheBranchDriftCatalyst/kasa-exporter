#!/usr/bin/env python3
"""
Extract panels from Grafana dashboard JSON files.

This utility extracts panel information from large dashboard JSON files
to make them more manageable for analysis and documentation.

Usage:
    # Extract all panels from all dashboards
    python extract_panels.py

    # Extract from specific dashboard
    python extract_panels.py --dashboard 1-real-time-monitoring.json

    # Output to specific file
    python extract_panels.py --output panels.json

    # Extract only specific fields
    python extract_panels.py --fields id,title,type
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def extract_panel_info(panel: dict, fields: list[str] | None = None) -> dict[str, Any]:
    """
    Extract relevant information from a panel.

    Args:
        panel: Panel dictionary from dashboard JSON
        fields: Optional list of fields to extract. If None, extracts all.

    Returns:
        Dictionary with extracted panel information
    """
    # Default fields to extract
    default_fields = {
        "id": panel.get("id"),
        "title": panel.get("title"),
        "type": panel.get("type"),
        "gridPos": panel.get("gridPos"),
        "targets": panel.get("targets", []),
        "fieldConfig": panel.get("fieldConfig"),
        "options": panel.get("options"),
    }

    # If specific fields requested, filter
    if fields:
        return {k: v for k, v in default_fields.items() if k in fields}

    return default_fields


def extract_panels_from_dashboard(
    dashboard_path: Path, fields: list[str] | None = None
) -> dict[str, Any]:
    """
    Extract all panels from a dashboard file.

    Args:
        dashboard_path: Path to dashboard JSON file
        fields: Optional list of fields to extract per panel

    Returns:
        Dictionary with dashboard metadata and panels
    """
    with dashboard_path.open() as f:
        dashboard = json.load(f)

    panels = []
    for panel in dashboard.get("panels", []):
        # Skip row panels (they're just layout containers)
        if panel.get("type") == "row":
            continue

        panel_info = extract_panel_info(panel, fields)
        panels.append(panel_info)

    return {
        "file": dashboard_path.name,
        "title": dashboard.get("title"),
        "uid": dashboard.get("uid"),
        "description": dashboard.get("description"),
        "panel_count": len(panels),
        "panels": panels,
    }


def extract_all_dashboards(
    dashboards_dir: Path, fields: list[str] | None = None
) -> list[dict[str, Any]]:
    """
    Extract panels from all dashboards in directory.

    Args:
        dashboards_dir: Path to dashboards directory
        fields: Optional list of fields to extract per panel

    Returns:
        List of dashboard dictionaries with extracted panels
    """
    all_dashboards = []

    for dashboard_file in sorted(dashboards_dir.glob("*.json")):
        print(f"Extracting panels from {dashboard_file.name}...")
        dashboard_data = extract_panels_from_dashboard(dashboard_file, fields)
        all_dashboards.append(dashboard_data)
        print(f"  Found {dashboard_data['panel_count']} panels")

    return all_dashboards


def main():
    """Extract panels from Grafana dashboards."""
    parser = argparse.ArgumentParser(description="Extract panels from Grafana dashboard JSON files")
    parser.add_argument(
        "--dashboard",
        "-d",
        help="Specific dashboard file to extract (default: all dashboards)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="dashboard_panels.json",
        help="Output JSON file (default: dashboard_panels.json)",
    )
    parser.add_argument(
        "--fields",
        "-f",
        help="Comma-separated list of fields to extract (default: all fields)",
    )
    parser.add_argument(
        "--dashboards-dir",
        default="etc/grafana/dashboards",
        help="Path to dashboards directory (default: etc/grafana/dashboards)",
    )

    args = parser.parse_args()

    dashboards_dir = Path(args.dashboards_dir)
    if not dashboards_dir.exists():
        print(f"❌ Dashboards directory not found: {dashboards_dir}")
        return 1

    # Parse fields if provided
    fields = args.fields.split(",") if args.fields else None

    # Extract panels
    if args.dashboard:
        dashboard_path = dashboards_dir / args.dashboard
        if not dashboard_path.exists():
            print(f"❌ Dashboard file not found: {dashboard_path}")
            return 1

        print(f"Extracting panels from {args.dashboard}...")
        data = [extract_panels_from_dashboard(dashboard_path, fields)]
    else:
        print("Extracting panels from all dashboards...")
        data = extract_all_dashboards(dashboards_dir, fields)

    # Save to output file
    output_path = Path(args.output)
    with output_path.open("w") as f:
        json.dump(data, f, indent=2)

    total_panels = sum(d["panel_count"] for d in data)
    print("\n" + "=" * 60)
    print(f"✅ Extracted {total_panels} panels from {len(data)} dashboard(s)")
    print(f"📄 Saved to {output_path}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
