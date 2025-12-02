#!/usr/bin/env python3
"""
Generate statistics about dashboard panels.

This utility analyzes extracted panel data to provide insights about
query patterns, panel types, metrics usage, and more.

Usage:
    # Generate full statistics report
    python panel_stats.py

    # Statistics for specific dashboard
    python panel_stats.py --dashboard "1-real-time-monitoring.json"

    # Show only specific statistics
    python panel_stats.py --show panel-types,metrics

    # Export statistics as JSON
    python panel_stats.py --output stats.json
"""

import json
import argparse
from pathlib import Path
from typing import Any
from collections import Counter, defaultdict


def load_panels_data(panels_file: Path) -> list[dict[str, Any]]:
    """Load extracted panels data from JSON file."""
    with panels_file.open() as f:
        return json.load(f)


def extract_metrics_from_expr(expr: str) -> list[str]:
    """
    Extract metric names from PromQL expression.

    This is a simple pattern matcher that extracts metric names.
    More sophisticated parsing could be added later.
    """
    import re

    # Match metric names (alphanumeric with underscores and colons)
    metrics = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_:]*)\b", expr)

    # Filter out PromQL keywords and functions
    promql_keywords = {
        "sum",
        "avg",
        "max",
        "min",
        "count",
        "rate",
        "irate",
        "increase",
        "by",
        "without",
        "on",
        "ignoring",
        "group_left",
        "group_right",
        "bool",
        "and",
        "or",
        "unless",
        "offset",
        "topk",
        "bottomk",
        "quantile",
        "histogram_quantile",
    }

    return [m for m in metrics if m not in promql_keywords and not m.startswith("$")]


def analyze_panels(data: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyze panels and generate statistics.

    Returns:
        Dictionary with various statistics
    """
    stats = {
        "total_dashboards": len(data),
        "total_panels": 0,
        "panels_by_dashboard": {},
        "panel_types": Counter(),
        "metrics_used": Counter(),
        "queries_by_dashboard": defaultdict(int),
        "panels_without_queries": [],
        "unique_metrics": set(),
        "version_filtered_queries": 0,
        "total_queries": 0,
    }

    for dashboard_data in data:
        dashboard_name = dashboard_data["file"]
        panel_count = dashboard_data["panel_count"]
        stats["total_panels"] += panel_count
        stats["panels_by_dashboard"][dashboard_name] = panel_count

        for panel in dashboard_data["panels"]:
            # Count panel types
            panel_type = panel.get("type", "unknown")
            stats["panel_types"][panel_type] += 1

            # Analyze queries
            targets = panel.get("targets", [])
            if not targets:
                stats["panels_without_queries"].append(
                    {
                        "dashboard": dashboard_name,
                        "panel_id": panel.get("id"),
                        "title": panel.get("title"),
                    }
                )
                continue

            for target in targets:
                expr = target.get("expr", "")
                if not expr:
                    continue

                stats["total_queries"] += 1
                stats["queries_by_dashboard"][dashboard_name] += 1

                # Check for version filtering
                if "version" in expr:
                    stats["version_filtered_queries"] += 1

                # Extract metrics
                metrics = extract_metrics_from_expr(expr)
                for metric in metrics:
                    stats["metrics_used"][metric] += 1
                    stats["unique_metrics"].add(metric)

    # Convert set to sorted list for JSON serialization
    stats["unique_metrics"] = sorted(stats["unique_metrics"])

    return stats


def format_stats_report(stats: dict[str, Any]) -> str:
    """
    Format statistics as human-readable report.

    Args:
        stats: Statistics dictionary

    Returns:
        Formatted report string
    """
    lines = []

    lines.append("=" * 70)
    lines.append("DASHBOARD PANEL STATISTICS")
    lines.append("=" * 70)
    lines.append("")

    # Overview
    lines.append("📊 OVERVIEW")
    lines.append("-" * 70)
    lines.append(f"Total Dashboards: {stats['total_dashboards']}")
    lines.append(f"Total Panels: {stats['total_panels']}")
    lines.append(f"Total Queries: {stats['total_queries']}")
    lines.append(f"Unique Metrics: {len(stats['unique_metrics'])}")
    lines.append("")

    # Panels by dashboard
    lines.append("📈 PANELS BY DASHBOARD")
    lines.append("-" * 70)
    for dashboard, count in sorted(stats["panels_by_dashboard"].items()):
        queries = stats["queries_by_dashboard"][dashboard]
        lines.append(f"{dashboard:45} {count:3} panels, {queries:3} queries")
    lines.append("")

    # Panel types
    lines.append("🎨 PANEL TYPES")
    lines.append("-" * 70)
    for panel_type, count in stats["panel_types"].most_common():
        percentage = (count / stats["total_panels"]) * 100
        lines.append(f"{panel_type:20} {count:3} ({percentage:5.1f}%)")
    lines.append("")

    # Top metrics
    lines.append("🔥 TOP 20 METRICS BY USAGE")
    lines.append("-" * 70)
    for metric, count in stats["metrics_used"].most_common(20):
        lines.append(f"{metric:50} {count:3} uses")
    lines.append("")

    # Version filtering
    lines.append("🏷️  VERSION FILTERING")
    lines.append("-" * 70)
    version_percentage = (
        (stats["version_filtered_queries"] / stats["total_queries"]) * 100
        if stats["total_queries"] > 0
        else 0
    )
    lines.append(
        f"Queries with version filter: {stats['version_filtered_queries']} "
        f"({version_percentage:.1f}%)"
    )
    lines.append(
        f"Queries without version filter: "
        f"{stats['total_queries'] - stats['version_filtered_queries']} "
        f"({100 - version_percentage:.1f}%)"
    )
    lines.append("")

    # Panels without queries
    if stats["panels_without_queries"]:
        lines.append("⚠️  PANELS WITHOUT QUERIES")
        lines.append("-" * 70)
        for panel in stats["panels_without_queries"]:
            lines.append(
                f"{panel['dashboard']:30} Panel {panel['panel_id']:3}: "
                f"{panel['title']}"
            )
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def main():
    """Generate panel statistics."""
    parser = argparse.ArgumentParser(
        description="Generate statistics about Grafana dashboard panels"
    )
    parser.add_argument(
        "--input",
        "-i",
        default="dashboard_panels.json",
        help="Input JSON file with extracted panels (default: dashboard_panels.json)",
    )
    parser.add_argument(
        "--dashboard",
        "-d",
        help="Filter statistics to specific dashboard (partial match)",
    )
    parser.add_argument(
        "--output", "-o", help="Export statistics as JSON to specified file"
    )

    args = parser.parse_args()

    # Load panels data
    panels_file = Path(args.input)
    if not panels_file.exists():
        print(f"❌ Panels data file not found: {panels_file}")
        print("Run extract_panels.py first to generate the data.")
        return 1

    data = load_panels_data(panels_file)

    # Filter by dashboard if specified
    if args.dashboard:
        data = [
            d for d in data if args.dashboard.lower() in d["file"].lower()
        ]
        if not data:
            print(f"❌ No dashboards found matching: {args.dashboard}")
            return 1

    # Generate statistics
    stats = analyze_panels(data)

    # Output results
    if args.output:
        output_path = Path(args.output)
        with output_path.open("w") as f:
            json.dump(stats, f, indent=2)
        print(f"✅ Statistics exported to {output_path}")
    else:
        report = format_stats_report(stats)
        print(report)

    return 0


if __name__ == "__main__":
    exit(main())
