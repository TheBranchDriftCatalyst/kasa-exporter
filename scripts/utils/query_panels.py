#!/usr/bin/env python3
"""
Query specific panels from extracted panel data.

This utility helps query and filter panels from the extracted JSON data,
making it easy to find specific panels without loading large dashboard files.

Usage:
    # Find panel by ID
    python query_panels.py --id 101

    # Find panels by title (partial match, case-insensitive)
    python query_panels.py --title "power"

    # Find panels by dashboard
    python query_panels.py --dashboard "1-real-time-monitoring.json"

    # Find panels by type
    python query_panels.py --type "piechart"

    # Find panels with specific query pattern
    python query_panels.py --query-pattern "current_consumption"

    # Combine filters
    python query_panels.py --dashboard "2-tou" --type "stat"

    # Output only specific fields
    python query_panels.py --id 101 --fields id,title,targets
"""

import json
import argparse
from pathlib import Path
from typing import Any


def load_panels_data(panels_file: Path) -> list[dict[str, Any]]:
    """Load extracted panels data from JSON file."""
    with panels_file.open() as f:
        return json.load(f)


def query_panels(
    data: list[dict[str, Any]],
    panel_id: int | None = None,
    title: str | None = None,
    dashboard: str | None = None,
    panel_type: str | None = None,
    query_pattern: str | None = None,
) -> list[dict[str, Any]]:
    """
    Query panels based on filters.

    Args:
        data: List of dashboard dictionaries with panels
        panel_id: Filter by panel ID
        title: Filter by title (partial match, case-insensitive)
        dashboard: Filter by dashboard file name (partial match)
        panel_type: Filter by panel type
        query_pattern: Filter by query pattern in targets

    Returns:
        List of matching panels with dashboard context
    """
    results = []

    for dashboard_data in data:
        # Filter by dashboard if specified
        if dashboard and dashboard.lower() not in dashboard_data["file"].lower():
            continue

        for panel in dashboard_data["panels"]:
            # Filter by panel ID
            if panel_id is not None and panel.get("id") != panel_id:
                continue

            # Filter by title
            if title and title.lower() not in str(panel.get("title", "")).lower():
                continue

            # Filter by type
            if panel_type and panel.get("type") != panel_type:
                continue

            # Filter by query pattern
            if query_pattern:
                targets = panel.get("targets", [])
                if not any(
                    query_pattern.lower() in str(target.get("expr", "")).lower()
                    for target in targets
                ):
                    continue

            # Add dashboard context to result
            result = {
                "dashboard_file": dashboard_data["file"],
                "dashboard_title": dashboard_data["title"],
                "dashboard_uid": dashboard_data["uid"],
                **panel,
            }
            results.append(result)

    return results


def format_panel_output(
    panels: list[dict[str, Any]], fields: list[str] | None = None
) -> str:
    """
    Format panels for output.

    Args:
        panels: List of panel dictionaries
        fields: Optional list of fields to include in output

    Returns:
        Formatted string output
    """
    if not panels:
        return "No panels found matching criteria."

    output = []
    for i, panel in enumerate(panels, 1):
        output.append(f"\n{'='*60}")
        output.append(f"Panel {i} of {len(panels)}")
        output.append(f"{'='*60}")

        # If specific fields requested, show only those
        if fields:
            for field in fields:
                if field in panel:
                    output.append(f"{field}: {json.dumps(panel[field], indent=2)}")
        else:
            # Show all fields in pretty format
            output.append(json.dumps(panel, indent=2))

    return "\n".join(output)


def main():
    """Query panels from extracted data."""
    parser = argparse.ArgumentParser(
        description="Query panels from extracted Grafana dashboard data"
    )
    parser.add_argument(
        "--input",
        "-i",
        default="dashboard_panels.json",
        help="Input JSON file with extracted panels (default: dashboard_panels.json)",
    )
    parser.add_argument(
        "--id", type=int, help="Filter by panel ID"
    )
    parser.add_argument(
        "--title", help="Filter by panel title (partial match, case-insensitive)"
    )
    parser.add_argument(
        "--dashboard",
        "-d",
        help="Filter by dashboard file name (partial match)",
    )
    parser.add_argument(
        "--type", "-t", help="Filter by panel type (e.g., stat, piechart, timeseries)"
    )
    parser.add_argument(
        "--query-pattern",
        "-q",
        help="Filter by query pattern in targets (partial match)",
    )
    parser.add_argument(
        "--fields",
        "-f",
        help="Comma-separated list of fields to display (default: all fields)",
    )
    parser.add_argument(
        "--count",
        "-c",
        action="store_true",
        help="Only show count of matching panels",
    )

    args = parser.parse_args()

    # Load panels data
    panels_file = Path(args.input)
    if not panels_file.exists():
        print(f"❌ Panels data file not found: {panels_file}")
        print("Run extract_panels.py first to generate the data.")
        return 1

    data = load_panels_data(panels_file)

    # Query panels
    results = query_panels(
        data,
        panel_id=args.id,
        title=args.title,
        dashboard=args.dashboard,
        panel_type=args.type,
        query_pattern=args.query_pattern,
    )

    # Output results
    if args.count:
        print(f"Found {len(results)} matching panel(s)")
    else:
        fields = args.fields.split(",") if args.fields else None
        output = format_panel_output(results, fields)
        print(output)

    return 0


if __name__ == "__main__":
    exit(main())
