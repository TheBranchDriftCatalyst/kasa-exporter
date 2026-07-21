#!/usr/bin/env python3
"""
Watch dashboard source files and auto-rebuild on changes.

This script watches the exploded panel source directory and automatically
rebuilds dashboards when panel files are modified, enabling live reload
workflow during development.

Features:
- Watches for file changes in source directory
- Automatically rebuilds affected dashboard
- Debounces rapid changes (waits for quiet period)
- Optional Grafana container restart for true live reload

Requirements:
    pip install watchdog

Usage:
    # Basic watch mode
    python scripts/utils/watch_dashboards.py

    # Watch with Grafana restart (requires docker-compose)
    python scripts/utils/watch_dashboards.py --restart-grafana

    # Custom source/dest
    python scripts/utils/watch_dashboards.py --source etc/grafana/dashboards/src --dest etc/grafana/dashboards
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add scripts/utils to path so we can import build_dashboards
_script_dir = Path(__file__).parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("❌ Error: watchdog package not installed")
    print("Install with: pip install watchdog")
    sys.exit(1)

# Import our build function (must happen after sys.path tweak above)
from build_dashboards import build_dashboard  # noqa: E402


class DashboardChangeHandler(FileSystemEventHandler):
    """Handle file system events for dashboard source files."""

    def __init__(
        self,
        source_dir: Path,
        dest_dir: Path,
        restart_grafana: bool = False,
        debounce_seconds: float = 1.0,
    ):
        """
        Initialize handler.

        Args:
            source_dir: Source directory with exploded panels
            dest_dir: Destination directory for built dashboards
            restart_grafana: Whether to restart Grafana container after build
            debounce_seconds: Seconds to wait after last change before rebuilding
        """
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.restart_grafana = restart_grafana
        self.debounce_seconds = debounce_seconds
        self.pending_builds: dict[str, float] = {}  # dashboard_name -> last_change_time

    def _get_dashboard_name(self, file_path: str) -> str | None:
        """Extract dashboard name from file path."""
        path = Path(file_path)

        # Walk up to find dashboard directory
        for parent in path.parents:
            if parent.parent == self.source_dir:
                return parent.name

        return None

    def _should_rebuild(self, dashboard_name: str) -> bool:
        """Check if enough time has passed since last change for rebuild."""
        if dashboard_name not in self.pending_builds:
            return False

        last_change = self.pending_builds[dashboard_name]
        elapsed = time.time() - last_change

        return elapsed >= self.debounce_seconds

    def _rebuild_dashboard(self, dashboard_name: str):
        """Rebuild a specific dashboard."""
        timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] 🔨 Rebuilding {dashboard_name}...")

        dashboard_dir = self.source_dir / dashboard_name
        output_file = self.dest_dir / f"{dashboard_name}.json"

        try:
            panel_count, success = build_dashboard(dashboard_dir, output_file)

            if success:
                print(f"[{timestamp}] ✅ Built {panel_count} panels → {output_file.name}")

                if self.restart_grafana:
                    self._restart_grafana_container()
            else:
                print(f"[{timestamp}] ❌ Build failed")

        except Exception as e:
            print(f"[{timestamp}] ❌ Error rebuilding dashboard: {e}")

        # Clear pending build
        if dashboard_name in self.pending_builds:
            del self.pending_builds[dashboard_name]

    def _restart_grafana_container(self):
        """Restart Grafana container to reload dashboards."""
        timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
        print(f"[{timestamp}] 🔄 Restarting Grafana container...")

        try:
            # Try docker-compose first
            result = subprocess.run(
                ["docker-compose", "restart", "grafana"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print(f"[{timestamp}] ✅ Grafana restarted")
            else:
                # Try docker compose (v2 syntax)
                result = subprocess.run(
                    ["docker", "compose", "restart", "grafana"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    print(f"[{timestamp}] ✅ Grafana restarted")
                else:
                    print(f"[{timestamp}] ⚠️  Could not restart Grafana: {result.stderr}")

        except subprocess.TimeoutExpired:
            print(f"[{timestamp}] ⚠️  Grafana restart timed out")
        except FileNotFoundError:
            print(f"[{timestamp}] ⚠️  docker-compose not found")

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Only watch .json files
        if not event.src_path.endswith(".json"):
            return

        dashboard_name = self._get_dashboard_name(event.src_path)
        if not dashboard_name:
            return

        timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
        file_name = Path(event.src_path).name
        print(f"[{timestamp}] 📝 Changed: {dashboard_name}/{file_name}")

        # Mark for rebuild (debounced)
        self.pending_builds[dashboard_name] = time.time()

    def on_created(self, event):
        """Handle file creation events."""
        self.on_modified(event)

    def check_pending_builds(self):
        """Check and execute pending builds that have passed debounce period."""
        dashboards_to_rebuild = [name for name in self.pending_builds if self._should_rebuild(name)]

        for dashboard_name in dashboards_to_rebuild:
            self._rebuild_dashboard(dashboard_name)


def main():
    """Watch dashboard source files and auto-rebuild."""
    parser = argparse.ArgumentParser(
        description="Watch dashboard source files and auto-rebuild on changes"
    )
    parser.add_argument(
        "--source",
        "-s",
        default="etc/grafana/dashboards/src",
        help="Source directory with exploded panel files (default: etc/grafana/dashboards/src)",
    )
    parser.add_argument(
        "--dest",
        "-d",
        default="etc/grafana/dashboards",
        help="Destination directory for built dashboards (default: etc/grafana/dashboards)",
    )
    parser.add_argument(
        "--restart-grafana",
        "-r",
        action="store_true",
        help="Restart Grafana container after each build (requires docker-compose)",
    )
    parser.add_argument(
        "--debounce",
        "-b",
        type=float,
        default=1.0,
        help="Debounce period in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    source_dir = Path(args.source)
    dest_dir = Path(args.dest)

    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        print("💡 Run explode_dashboards.py first to create source files")
        return 1

    print("=" * 70)
    print("👀 DASHBOARD WATCHER")
    print("=" * 70)
    print(f"Source: {source_dir}")
    print(f"Destination: {dest_dir}")
    print(f"Restart Grafana: {args.restart_grafana}")
    print(f"Debounce: {args.debounce}s")
    print("=" * 70)
    print("Watching for changes... (Ctrl+C to stop)")
    print("=" * 70)

    # Create event handler and observer
    event_handler = DashboardChangeHandler(
        source_dir=source_dir,
        dest_dir=dest_dir,
        restart_grafana=args.restart_grafana,
        debounce_seconds=args.debounce,
    )

    observer = Observer()
    observer.schedule(event_handler, str(source_dir), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(0.5)
            # Check for pending builds (debounced)
            event_handler.check_pending_builds()

    except KeyboardInterrupt:
        timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] 👋 Stopping watcher...")
        observer.stop()

    observer.join()
    print("✅ Watcher stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
