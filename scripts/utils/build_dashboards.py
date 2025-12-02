#!/usr/bin/env python3
"""
Build Grafana dashboards from individual panel files.

This script combines exploded panel files back into complete dashboard JSON files
for Grafana provisioning.

Directory structure expected:
    src/
    ├── 1-real-time-monitoring/
    │   ├── _dashboard.json          # Dashboard metadata
    │   ├── 101-total-power-draw.json
    │   └── ...
    └── ...

Output:
    1-real-time-monitoring.json      # Complete dashboard ready for Grafana

Usage:
    # Build all dashboards
    python scripts/utils/build_dashboards.py

    # Build specific dashboard
    python scripts/utils/build_dashboards.py --dashboard 1-real-time-monitoring

    # Custom source/destination
    python scripts/utils/build_dashboards.py --source etc/grafana/dashboards/src --dest etc/grafana/dashboards

    # Watch mode (auto-rebuild on changes)
    python scripts/utils/build_dashboards.py --watch
"""

import json
import argparse
from pathlib import Path
from typing import Any


def load_panel_file(panel_file: Path) -> dict[str, Any]:
    """Load a panel JSON file."""
    with panel_file.open() as f:
        return json.load(f)


def load_common_config(src_dir: Path) -> dict[str, Any]:
    """
    Load common dashboard configuration.

    Args:
        src_dir: Source directory containing _common.json

    Returns:
        Common config dictionary, or empty dict if not found
    """
    common_file = src_dir / "_common.json"
    if not common_file.exists():
        return {}

    with common_file.open() as f:
        config = json.load(f)

    # Remove metadata fields
    config.pop("$schema", None)
    config.pop("_comment", None)

    return config


def build_panel_dashboard(
    panel: dict[str, Any],
    panel_name: str,
    common_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Build a single-panel dashboard for debugging.

    Args:
        panel: Panel definition
        panel_name: Name for the dashboard
        common_config: Optional common configuration to inject

    Returns:
        Complete dashboard with single panel
    """
    dashboard = {
        "title": panel_name,
        "uid": f"panel-{panel.get('id', 'unknown')}",
        "panels": [panel],
        "version": 1,
        "id": None,
        "time": {"from": "now-6h", "to": "now"},
        "refresh": "10s"
    }

    # Inject common config if provided
    if common_config:
        dashboard = {**common_config, **dashboard}

    return dashboard


def build_dashboard(
    dashboard_src_dir: Path,
    output_file: Path,
    common_config: dict[str, Any] | None = None,
    build_individual_panels: bool = False,
    panels_output_dir: Path | None = None
) -> tuple[int, bool]:
    """
    Build a complete dashboard from exploded panel files.

    Args:
        dashboard_src_dir: Directory containing _dashboard.json and panel files
        output_file: Path to write complete dashboard JSON
        common_config: Optional common configuration to inject
        build_individual_panels: If True, also build individual panel dashboards
        panels_output_dir: Directory to write individual panel dashboards

    Returns:
        Tuple of (panel_count, success)
    """
    # Load dashboard metadata
    metadata_file = dashboard_src_dir / "_dashboard.json"
    if not metadata_file.exists():
        print(f"  ❌ Missing _dashboard.json in {dashboard_src_dir.name}")
        return 0, False

    with metadata_file.open() as f:
        dashboard = json.load(f)

    # Inject common configuration (if provided)
    if common_config:
        # Start with common config, then overlay dashboard-specific config
        # This allows dashboard-specific settings to override common ones
        merged = {**common_config, **dashboard}

        # For nested dicts, do a deeper merge for specific keys
        for key in ["annotations", "templating", "timepicker"]:
            if key in common_config and key in dashboard:
                # Dashboard-specific wins, but we note the injection happened
                pass
            elif key in common_config:
                merged[key] = common_config[key]

        dashboard = merged

    # Load all panel files (skip _dashboard.json and row panels)
    panels = []
    panel_files = sorted(
        [f for f in dashboard_src_dir.glob("*.json") if f.name != "_dashboard.json"]
    )

    for panel_file in panel_files:
        panel = load_panel_file(panel_file)

        # Row panels are layout containers - we can include them if they exist
        # but they don't count toward functional panel count
        panels.append(panel)

        # Build individual panel dashboard if requested
        if build_individual_panels and panels_output_dir and panel.get("type") != "row":
            panel_name = f"{dashboard_src_dir.name}/{panel_file.stem}"
            panel_dashboard = build_panel_dashboard(panel, panel_name, common_config)

            # Create subdirectory for this dashboard's panels
            dashboard_panels_dir = panels_output_dir / dashboard_src_dir.name
            dashboard_panels_dir.mkdir(parents=True, exist_ok=True)

            # Write individual panel dashboard
            panel_output_file = dashboard_panels_dir / f"{panel_file.name}"
            with panel_output_file.open("w") as f:
                json.dump(panel_dashboard, f, indent=2)

    # Sort panels by ID to maintain consistent order
    panels.sort(key=lambda p: p.get("id", 0))

    # Add panels to dashboard
    dashboard["panels"] = panels

    # Write complete dashboard
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w") as f:
        json.dump(dashboard, f, indent=2)

    # Count non-row panels
    panel_count = sum(1 for p in panels if p.get("type") != "row")

    return panel_count, True


def build_all_dashboards(
    source_dir: Path,
    output_dir: Path,
    build_individual_panels: bool = False,
    panels_output_dir: Path | None = None
) -> dict[str, tuple[int, bool]]:
    """
    Build all dashboards from source directory.

    Args:
        source_dir: Directory containing dashboard subdirectories
        output_dir: Directory to write complete dashboard files
        build_individual_panels: If True, also build individual panel dashboards
        panels_output_dir: Directory to write individual panel dashboards

    Returns:
        Dictionary mapping dashboard name to (panel_count, success)
    """
    results = {}

    # Load common configuration (if it exists)
    common_config = load_common_config(source_dir)
    if common_config:
        print(f"📦 Loaded common configuration from _common.json")
        print(f"   Injecting: {', '.join(common_config.keys())}")
        if build_individual_panels:
            print(f"🔍 Building individual panel dashboards for debugging")

    # Find all dashboard source directories (those with _dashboard.json)
    dashboard_dirs = [
        d for d in source_dir.iterdir()
        if d.is_dir() and (d / "_dashboard.json").exists()
    ]

    for dashboard_dir in sorted(dashboard_dirs):
        dashboard_name = dashboard_dir.name
        output_file = output_dir / f"{dashboard_name}.json"

        print(f"\n🔨 Building {dashboard_name}.json...")

        panel_count, success = build_dashboard(
            dashboard_dir,
            output_file,
            common_config,
            build_individual_panels,
            panels_output_dir
        )
        results[dashboard_name] = (panel_count, success)

        if success:
            print(f"  ✅ Built with {panel_count} panels → {output_file.name}")
            if build_individual_panels:
                print(f"     + {panel_count} individual panel dashboards in {dashboard_name}/")
        else:
            print(f"  ❌ Build failed")

    return results


def main():
    """Build Grafana dashboards from individual panel files."""
    parser = argparse.ArgumentParser(
        description="Build Grafana dashboards from individual panel files"
    )
    parser.add_argument(
        "--dashboard",
        "-d",
        help="Specific dashboard to build (directory name, without .json)",
    )
    parser.add_argument(
        "--source",
        "-s",
        default="etc/grafana/dashboards/src",
        help="Source directory with exploded panel files (default: etc/grafana/dashboards/src)",
    )
    parser.add_argument(
        "--dest",
        "-o",
        default="etc/grafana/dashboards",
        help="Destination directory for built dashboards (default: etc/grafana/dashboards)",
    )
    parser.add_argument(
        "--with-panels",
        action="store_true",
        help="Also build individual panel dashboards (for debugging)",
    )
    parser.add_argument(
        "--panels-dir",
        "-p",
        help="Directory for individual panel dashboards (default: <dest>/_panels)",
    )

    args = parser.parse_args()

    source_dir = Path(args.source)
    output_dir = Path(args.dest)

    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        print(f"💡 Run explode_dashboards.py first to create source files")
        return 1

    # Determine panels output directory
    panels_output_dir = None
    if args.with_panels:
        if args.panels_dir:
            panels_output_dir = Path(args.panels_dir)
        else:
            panels_output_dir = output_dir / "_panels"

    print(f"Source: {source_dir}")
    print(f"Destination: {output_dir}")
    if args.with_panels:
        print(f"Individual panels: {panels_output_dir}")

    # Load common configuration
    common_config = load_common_config(source_dir)
    if common_config:
        print(f"📦 Loaded common configuration from _common.json")
        print(f"   Injecting: {', '.join(common_config.keys())}\n")

    # Build dashboard(s)
    if args.dashboard:
        dashboard_dir = source_dir / args.dashboard
        if not dashboard_dir.exists():
            print(f"❌ Dashboard directory not found: {dashboard_dir}")
            return 1

        if not (dashboard_dir / "_dashboard.json").exists():
            print(f"❌ Missing _dashboard.json in {dashboard_dir}")
            return 1

        output_file = output_dir / f"{args.dashboard}.json"
        print(f"🔨 Building {args.dashboard}.json...")
        panel_count, success = build_dashboard(
            dashboard_dir,
            output_file,
            common_config,
            args.with_panels,
            panels_output_dir
        )

        if success:
            results = {args.dashboard: (panel_count, True)}
        else:
            print(f"❌ Build failed")
            return 1
    else:
        results = build_all_dashboards(
            source_dir,
            output_dir,
            args.with_panels,
            panels_output_dir
        )

    # Summary
    print("\n" + "=" * 70)
    print("📊 BUILD SUMMARY")
    print("=" * 70)

    total_panels = 0
    success_count = 0
    failed_count = 0

    for dashboard, (panel_count, success) in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {dashboard:45} {panel_count:3} panels")
        if success:
            total_panels += panel_count
            success_count += 1
        else:
            failed_count += 1

    print("=" * 70)
    print(
        f"✅ Built {success_count} dashboard(s), "
        f"{total_panels} total panels"
    )
    if failed_count > 0:
        print(f"❌ Failed: {failed_count} dashboard(s)")
    print(f"📂 Output: {output_dir}")
    print("=" * 70)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit(main())
