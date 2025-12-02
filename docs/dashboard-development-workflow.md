# Dashboard Development Workflow

**Last Updated**: 2025-11-03

## Overview

This document describes the dashboard development workflow that enables **live-reload editing** of individual Grafana dashboard panels.

Instead of editing massive monolithic JSON files (100KB+), you can:
1. **Explode** dashboards into individual panel files
2. **Edit** panels in isolation with proper version control
3. **Watch** for changes and auto-rebuild dashboards
4. **Reload** Grafana automatically to see changes live

---

## Architecture

```
etc/grafana/dashboards/              # Built dashboards (for Grafana)
├── 1-real-time-monitoring.json      # ← Complete dashboard (auto-generated)
├── 2-tou-cost-optimization.json
└── ...

etc/grafana/dashboards/src/          # Source panels (for editing)
├── 1-real-time-monitoring/
│   ├── _dashboard.json               # ← Dashboard metadata only
│   ├── 101-total-power-draw.json     # ← Individual panel
│   ├── 102-current-cost-rate.json
│   └── ...
├── 2-tou-cost-optimization/
│   ├── _dashboard.json
│   └── ...
└── ...
```

### Key Concepts

**Exploded Format** (`etc/grafana/dashboards/src/`):
- One directory per dashboard
- `_dashboard.json` contains metadata (title, UID, settings)
- Each panel in its own file: `{id}-{slug}.json`
- Easy to edit, review, and version control

**Built Format** (`etc/grafana/dashboards/`):
- Complete dashboard JSON files
- Ready for Grafana provisioning
- Auto-generated from source files
- **Never edit these directly!**

---

## Quick Start

### 1. Initialize Development Environment

```bash
# One-time setup: explode existing dashboards
task dashboards:dev:init
```

This will:
- Explode all dashboards into `etc/grafana/dashboards/src/`
- Extract panel metadata to `/tmp/dashboard_panels.json`
- Show next steps

### 2. Start Watch Mode

```bash
# Basic watch (auto-rebuild on changes)
task dashboards:watch

# Watch + auto-restart Grafana (true live reload)
task dashboards:watch:reload
```

### 3. Edit Panels

Open and edit any panel file in `etc/grafana/dashboards/src/`:

```bash
# Edit a specific panel
vim etc/grafana/dashboards/src/1-real-time-monitoring/101-total-power-draw.json

# Or use your favorite editor
code etc/grafana/dashboards/src/
```

### 4. See Changes

**With `task dashboards:watch`**:
- Panel file saved → Dashboard auto-rebuilt
- Refresh Grafana browser manually

**With `task dashboards:watch:reload`**:
- Panel file saved → Dashboard auto-rebuilt → Grafana auto-restarted
- Refresh browser to see changes (Grafana takes ~5s to restart)

---

## Task Commands Reference

### Development Workflow

```bash
# Initialize (first time)
task dashboards:dev:init         # Explode + extract metadata

# Start development
task dashboards:watch            # Watch for changes
task dashboards:watch:reload     # Watch + restart Grafana

# Manual operations
task dashboards:build            # Build all dashboards
task dashboards:explode          # Explode all dashboards
```

### Panel Analysis

```bash
# Extract panel metadata
task dashboards:extract          # Creates /tmp/dashboard_panels.json

# Statistics
task dashboards:stats            # Show panel statistics

# Query panels
task dashboards:query:pie        # Find pie charts
task dashboards:query:table      # Find tables
task dashboards:query:broken     # Find panels without queries

# Custom queries
task dashboards:query -- --type stat
task dashboards:query -- --title "power"
task dashboards:query -- --dashboard "2-tou"
```

### Cleanup

```bash
# Remove source files (keep built dashboards)
task dashboards:clean:src

# Remove metadata cache
task dashboards:clean:metadata
```

### Help

```bash
# Show all dashboard commands
task dashboards:help

# List all dashboard tasks
task --list | grep dashboards
```

---

## Detailed Workflow

### Exploding Dashboards

**Command**: `task dashboards:explode`

**What it does**:
1. Reads dashboard JSON files from `etc/grafana/dashboards/`
2. Separates metadata from panels
3. Creates directory per dashboard in `etc/grafana/dashboards/src/`
4. Writes `_dashboard.json` (metadata only)
5. Writes individual panel files: `{id}-{slug}.json`

**Example**:
```bash
$ task dashboards:explode

📦 Exploding 1-real-time-monitoring.json...
  ✅ Created _dashboard.json
  ✅ Created 101-total-power-draw.json
  ✅ Created 102-current-cost-rate.json
  ...

======================================================================
📊 EXPLOSION SUMMARY
======================================================================
1-real-time-monitoring.json                      9 panels
2-tou-cost-optimization.json                    18 panels
...
======================================================================
✅ Exploded 6 dashboard(s), 146 total panels
📂 Output: etc/grafana/dashboards/src
======================================================================
```

**Options**:
```bash
# Explode specific dashboard
python scripts/utils/explode_dashboards.py --dashboard 1-real-time-monitoring.json

# Overwrite existing files
task dashboards:explode:force
```

---

### Building Dashboards

**Command**: `task dashboards:build`

**What it does**:
1. Reads source directory `etc/grafana/dashboards/src/`
2. For each dashboard directory:
   - Loads `_dashboard.json` metadata
   - Loads all panel files
   - Combines into complete dashboard
   - Writes to `etc/grafana/dashboards/{name}.json`

**Example**:
```bash
$ task dashboards:build

🔨 Building 1-real-time-monitoring.json...
  ✅ Built with 9 panels → 1-real-time-monitoring.json

🔨 Building 2-tou-cost-optimization.json...
  ✅ Built with 18 panels → 2-tou-cost-optimization.json

======================================================================
📊 BUILD SUMMARY
======================================================================
✅ 1-real-time-monitoring                        9 panels
✅ 2-tou-cost-optimization                      18 panels
...
======================================================================
✅ Built 6 dashboard(s), 146 total panels
📂 Output: etc/grafana/dashboards
======================================================================
```

**Options**:
```bash
# Build specific dashboard
python scripts/utils/build_dashboards.py --dashboard 1-real-time-monitoring
```

---

### Watch Mode

**Command**: `task dashboards:watch`

**What it does**:
1. Starts file watcher on `etc/grafana/dashboards/src/`
2. Monitors for changes to `.json` files
3. Debounces rapid changes (waits 1 second after last change)
4. Auto-rebuilds affected dashboard
5. Optionally restarts Grafana (with `--restart-grafana`)

**Example**:
```bash
$ task dashboards:watch

======================================================================
👀 DASHBOARD WATCHER
======================================================================
Source: etc/grafana/dashboards/src
Destination: etc/grafana/dashboards
Restart Grafana: False
Debounce: 1.0s
======================================================================
Watching for changes... (Ctrl+C to stop)
======================================================================

[14:23:45] 📝 Changed: 1-real-time-monitoring/101-total-power-draw.json
[14:23:46] 🔨 Rebuilding 1-real-time-monitoring...
[14:23:46] ✅ Built 9 panels → 1-real-time-monitoring.json
```

**With Grafana Restart**:
```bash
$ task dashboards:watch:reload

[14:23:46] ✅ Built 9 panels → 1-real-time-monitoring.json
[14:23:46] 🔄 Restarting Grafana container...
[14:23:51] ✅ Grafana restarted
```

**Features**:
- **Debouncing**: Waits for 1 second of quiet before rebuilding (configurable)
- **Selective rebuild**: Only rebuilds the changed dashboard, not all
- **Error handling**: Shows errors but continues watching

**Requirements**:
```bash
# Watchdog package (auto-installed by task)
pip install watchdog

# For Grafana restart (requires docker-compose)
docker-compose restart grafana
```

---

## Editing Panel Files

### Panel File Structure

Each panel file contains a complete panel definition:

```json
{
  "id": 101,
  "title": "⚡ Total Power Draw",
  "type": "stat",
  "gridPos": {
    "h": 4,
    "w": 6,
    "x": 0,
    "y": 0
  },
  "targets": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "PBFA97CFB590B2093"
      },
      "expr": "current_consumption:total",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "watt"
    }
  },
  "options": {
    "reduceOptions": {
      "calcs": ["lastNotNull"]
    }
  }
}
```

### Common Edits

**Change Query**:
```json
{
  "targets": [
    {
      "expr": "current_consumption:total",  // ← Edit this
      "legendFormat": "{{alias}}"           // ← Or this
    }
  ]
}
```

**Change Title**:
```json
{
  "title": "⚡ Total Power Draw"  // ← Edit this
}
```

**Change Visualization Type**:
```json
{
  "type": "stat"  // ← Change to: timeseries, gauge, table, etc.
}
```

**Change Position/Size**:
```json
{
  "gridPos": {
    "h": 4,   // ← Height (grid units)
    "w": 6,   // ← Width (grid units, max 24)
    "x": 0,   // ← X position
    "y": 0    // ← Y position
  }
}
```

### Dashboard Metadata

Edit `_dashboard.json` to change dashboard-level settings:

```json
{
  "title": "🌊 Real-Time Monitoring",
  "uid": "kasa-realtime",
  "timezone": "browser",
  "refresh": "5s",
  "time": {
    "from": "now-6h",
    "to": "now"
  },
  "templating": {
    "list": [
      {
        "name": "version",
        "type": "query",
        "query": "label_values(version)"
      }
    ]
  }
}
```

---

## Version Control Best Practices

### What to Commit

**✅ Commit**:
- `etc/grafana/dashboards/src/` - Source panel files
- `scripts/utils/*.py` - Build scripts
- `Taskfile.dashboards.yml` - Task definitions

**❌ Don't Commit**:
- `etc/grafana/dashboards/*.json` - Built dashboards (auto-generated)
- `/tmp/dashboard_panels.json` - Metadata cache (temporary)

### .gitignore Recommendations

Add to `.gitignore`:
```
# Built dashboards (generated from src/)
etc/grafana/dashboards/*.json

# Keep the src/ directory
!etc/grafana/dashboards/src/

# Temporary metadata
/tmp/dashboard_panels.json
```

### Merge Conflicts

With exploded format, merge conflicts are:
- **Isolated** to specific panel files
- **Easier to review** (one panel per file)
- **Faster to resolve** (edit the conflicting panel file)

Before:
```diff
<<<<<<< HEAD
  "panels": [{"id": 101, "title": "Power", "expr": "query1"}, ...]
=======
  "panels": [{"id": 101, "title": "Power Draw", "expr": "query2"}, ...]
>>>>>>> feature-branch
```

After (with exploded format):
```diff
# Only in 101-power-draw.json
<<<<<<< HEAD
  "title": "Power"
  "expr": "query1"
=======
  "title": "Power Draw"
  "expr": "query2"
>>>>>>> feature-branch
```

---

## Troubleshooting

### Build Fails: Missing _dashboard.json

**Error**:
```
❌ Missing _dashboard.json in 1-real-time-monitoring
```

**Solution**: Run explode first:
```bash
task dashboards:explode
```

### Watch Not Detecting Changes

**Issue**: File saved but no rebuild triggered

**Solutions**:
1. Check debounce period (default 1s) - may need to wait
2. Verify watching correct directory:
   ```bash
   ls etc/grafana/dashboards/src/
   ```
3. Check file permissions
4. Restart watcher

### Grafana Not Showing Changes

**Issue**: Dashboard rebuilt but Grafana shows old version

**Solutions**:

1. **Manual refresh**: Refresh browser (Cmd+R / Ctrl+R)

2. **Hard refresh**: Clear cache (Cmd+Shift+R / Ctrl+Shift+R)

3. **Restart Grafana**:
   ```bash
   docker compose restart grafana
   # or
   task dashboards:watch:reload  # Auto-restart mode
   ```

4. **Check provisioning**: Verify dashboard file timestamp:
   ```bash
   ls -la etc/grafana/dashboards/1-real-time-monitoring.json
   ```

5. **Grafana logs**:
   ```bash
   docker compose logs -f grafana
   ```

### Panel Not Appearing After Rebuild

**Issue**: Panel exists in source but not in built dashboard

**Debugging**:

1. Check panel file exists:
   ```bash
   ls etc/grafana/dashboards/src/1-real-time-monitoring/
   ```

2. Verify panel file is valid JSON:
   ```bash
   python -m json.tool etc/grafana/dashboards/src/1-real-time-monitoring/101-panel.json
   ```

3. Check build output for errors:
   ```bash
   task dashboards:build
   ```

4. Check panel type (row panels don't count):
   ```json
   {
     "type": "row"  // ← This is just a layout container
   }
   ```

### Watchdog Not Installed

**Error**:
```
❌ Error: watchdog package not installed
```

**Solution**:
```bash
poetry add --group dev watchdog
```

---

## Advanced Usage

### Custom Build Pipeline

Create a custom build script for additional processing:

```python
#!/usr/bin/env python3
"""Custom dashboard build with validation."""

from pathlib import Path
from build_dashboards import build_dashboard

# Build with custom logic
dashboard_dir = Path("etc/grafana/dashboards/src/1-real-time-monitoring")
output_file = Path("etc/grafana/dashboards/1-real-time-monitoring.json")

# Build
panel_count, success = build_dashboard(dashboard_dir, output_file)

# Validate
if success:
    # Custom validation logic here
    print(f"✅ Built and validated {panel_count} panels")
```

### Bulk Panel Editing

Use the query utilities to find and edit multiple panels:

```bash
# Find all pie charts
task dashboards:query:pie > pie_charts.json

# Edit them (example: Python script)
python scripts/fix_pie_charts_v2.py

# Rebuild
task dashboards:build
```

### Integration with CI/CD

```yaml
# .github/workflows/dashboards.yml
name: Validate Dashboards

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Build dashboards
        run: python scripts/utils/build_dashboards.py

      - name: Validate JSON
        run: |
          for file in etc/grafana/dashboards/*.json; do
            python -m json.tool "$file" > /dev/null || exit 1
          done
```

---

## Tips & Tricks

### 1. Quick Panel Duplication

```bash
# Copy a panel
cp etc/grafana/dashboards/src/1-real-time-monitoring/101-power.json \
   etc/grafana/dashboards/src/1-real-time-monitoring/201-power-copy.json

# Edit the copy
vim etc/grafana/dashboards/src/1-real-time-monitoring/201-power-copy.json

# Change ID and title
jq '.id = 201 | .title = "New Panel"' 201-power-copy.json > tmp && mv tmp 201-power-copy.json
```

### 2. Find Panels Using Specific Metric

```bash
# Find all panels querying current_consumption
task dashboards:query -- --query-pattern "current_consumption"

# Count them
task dashboards:query -- --query-pattern "current_consumption" --count
```

### 3. Panel Naming Convention

Use consistent naming for easy sorting:
- `{id}-{slug}.json`
- ID ranges: 100s = stats, 200s = graphs, 300s = tables, etc.
- Slugs: lowercase-with-hyphens

Examples:
```
101-total-power-draw.json
102-current-cost-rate.json
201-power-over-time.json
301-device-status-table.json
```

### 4. Dashboard Templates

Create template directories for new dashboards:

```bash
# Create new dashboard from template
cp -r etc/grafana/dashboards/src/_template \
      etc/grafana/dashboards/src/7-new-dashboard

# Edit metadata
vim etc/grafana/dashboards/src/7-new-dashboard/_dashboard.json

# Add panels
# ...

# Build
task dashboards:build
```

---

## Related Documentation

- **Panel Utilities**: `scripts/utils/README.md`
- **Canonical Reference**: `docs/dashboard-panels-canon.md`
- **Testing Report**: `docs/dashboard-browser-testing.md`
- **Fixes Summary**: `docs/dashboard-fixes-summary.md`

---

## Maintenance

### When to Rebuild Source Files

Re-run `task dashboards:explode:force` when:
- Dashboards are edited directly in Grafana UI
- External tools modify dashboard JSON files
- After importing dashboards from Grafana Cloud
- After major Grafana version upgrades

### Keeping Documentation in Sync

After dashboard changes:

```bash
# Re-extract panel metadata
task dashboards:extract

# Regenerate statistics
task dashboards:stats > docs/dashboard-stats.txt

# Update canonical docs if needed
vim docs/dashboard-panels-canon.md
```

---

**Document Version**: 1.0 (2025-11-03)
**Maintained By**: Dashboard Development Team
