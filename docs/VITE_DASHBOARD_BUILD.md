# Vite Dashboard Build System

This project uses Vite as a fast, reliable build tool for Grafana dashboard development.

## Why Vite?

- **Fast file watching** - Reliable on macOS and all platforms
- **Sub-second rebuilds** - Instant feedback on changes
- **Modern tooling** - Industry-standard dev experience
- **Minimal configuration** - Just works out of the box

## Quick Start

```bash
# Install dependencies (first time only)
yarn install

# Start dashboard watcher
task dashboards:watch

# Or run directly
yarn watch
```

## How It Works

The Vite plugin (`vite.config.js`) watches the source directory and automatically:

1. Detects changes to any `.json` files in `etc/grafana/dashboards-src/`
2. Identifies which dashboard the file belongs to
3. Rebuilds that specific dashboard
4. Writes the output to `etc/grafana/provisioning/dashboards/.out/`

## Project Structure

```
etc/grafana/
├── dashboards-src/              # Source files (edit these)
│   ├── 1-real-time-monitoring/
│   │   ├── _dashboard.json      # Dashboard metadata
│   │   ├── 101-panel-name.json  # Individual panels
│   │   └── ...
│   └── ...
└── provisioning/
    └── dashboards/
        ├── .out/                # Consolidated dashboards (Grafana reads these)
        │   ├── 1-real-time-monitoring.json
        │   └── ...
        └── .src/                # Exploded dashboards (for debugging/reference)
            ├── 1-real-time-monitoring/
            │   ├── _dashboard.json
            │   ├── 101-panel.json
            │   └── ...
            └── ...
```

**Important**: Grafana only provisions from `.out/` (flat, self-contained dashboards). The `.src/` directory is for debugging and reference only.

## Development Workflow

1. **Start the watcher**: `task dashboards:watch`
2. **Edit panel files**: Modify any `.json` file in `dashboards-src/`
3. **See instant rebuild**: Vite detects the change and rebuilds within milliseconds
4. **Check Grafana**: Reload the dashboard to see your changes

## Full Dev Environment

For the complete dev experience with both dashboard watching and the exporter:

```bash
task dev:dashboards
```

This starts both:
- Vite dashboard watcher
- Kasa Exporter with live reload
- Prometheus + Grafana containers

## Commands

```bash
# Watch for changes (Vite)
task dashboards:watch
yarn watch

# One-time build (Python - for CI/CD)
task dashboards:build

# Full dev stack
task dev:dashboards
```

## Configuration

The Vite configuration is in `vite.config.js`. Key settings:

- **Source directory**: `etc/grafana/dashboards-src` (edit these)
- **Output directory**: `etc/grafana/provisioning/dashboards/.out` (Grafana reads these)
- **Debug directory**: `etc/grafana/provisioning/dashboards/.src` (for reference)
- **Port**: 5174 (not used for serving, just for Vite's internal server)

Grafana provisioning configuration (`etc/grafana/dashboard.yaml`) points to `.out/` directory.

## Panel ID Assignment

Panel IDs are automatically assigned based on the filename:

- `101-panel-name.json` → Panel ID: 101
- `202-another-panel.json` → Panel ID: 202
- `panel-without-number.json` → Auto-assigned sequential ID

## Debugging

If the watcher isn't detecting changes:

1. Check that Vite is running: `ps aux | grep vite`
2. Look for error messages in the terminal
3. Verify file paths match the configuration
4. Try restarting: `Ctrl+C` then `task dashboards:watch`

## Migration Notes

This replaces the previous Python `watchdog` implementation with Vite for better reliability and performance. The Python build scripts are still available for CI/CD and one-time builds.
