# Dashboard Development - Quick Start Guide

**TL;DR**: Edit dashboard panels individually with live reload.

---

## 🚀 Quick Start (3 steps)

### 1. Initialize Dashboard Source Files

```bash
task dashboards:dev:init
```

This explodes the monolithic dashboard JSON files into individual panel files in `etc/grafana/dashboards/src/`.

### 2. Start Development Mode

```bash
task dev:dashboards
```

This starts:
- ✅ Prometheus (metrics database)
- ✅ Grafana (dashboard UI)
- ✅ Kasa Exporter (metrics collector) with live reload
- ✅ Dashboard Watcher (auto-rebuild on panel changes)

### 3. Edit Panels

Open any panel file in `etc/grafana/dashboards/src/` and save:

```bash
# Example: Edit the total power panel
vim etc/grafana/dashboards/src/1-real-time-monitoring/101-total-power-draw.json
```

**What happens**:
1. You save the file
2. Dashboard watcher detects the change (within 1 second)
3. Dashboard is automatically rebuilt
4. Grafana detects the new file and reloads it
5. Refresh your browser to see the changes

---

## 📂 File Structure

```
etc/grafana/dashboards/           # ← Grafana reads from here (auto-generated)
├── 1-real-time-monitoring.json
└── 2-tou-cost-optimization.json

etc/grafana/dashboards/src/       # ← You edit here
├── 1-real-time-monitoring/
│   ├── _dashboard.json           # Dashboard metadata
│   ├── 101-total-power-draw.json # Individual panels
│   ├── 102-current-cost-rate.json
│   └── ...
└── 2-tou-cost-optimization/
    ├── _dashboard.json
    └── ...
```

**Rule**: Never edit `etc/grafana/dashboards/*.json` directly - they're auto-generated!

---

## 🎯 Common Tasks

### Edit a Panel Query

```bash
# 1. Find the panel
task dashboards:query -- --title "power"

# 2. Edit it
vim etc/grafana/dashboards/src/1-real-time-monitoring/101-total-power-draw.json

# 3. Change the query
{
  "targets": [
    {
      "expr": "current_consumption:total"  // ← Change this
    }
  ]
}

# 4. Save (auto-rebuilds)
# 5. Refresh Grafana browser
```

### Find All Pie Charts

```bash
task dashboards:query:pie
```

### View Dashboard Statistics

```bash
task dashboards:stats
```

### Manual Build (if not using watcher)

```bash
task dashboards:build
```

---

## 🔄 Live Reload Workflow

```
┌─────────────────────┐
│  Edit panel file    │
│  in src/ directory  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Dashboard Watcher  │  ← Detects change (1s debounce)
│  auto-rebuilds      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Built dashboard    │  ← Writes to etc/grafana/dashboards/
│  JSON file updated  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Grafana detects    │  ← Provisioner watches directory
│  new file & reloads │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Refresh browser    │  ← See your changes!
└─────────────────────┘
```

**Note**: Grafana's dashboard provisioner automatically detects file changes and reloads dashboards. No container restart needed!

---

## 💡 Tips

### 1. Use VSCode/Vim with JSON Schema

Add JSON schema for autocomplete:

```json
{
  "$schema": "https://grafana.com/grafana/schemas/dashboard/v1.json"
}
```

### 2. Format Panel JSON

```bash
# Format a panel file
python -m json.tool etc/grafana/dashboards/src/1-real-time-monitoring/101-panel.json > tmp.json && mv tmp.json etc/grafana/dashboards/src/1-real-time-monitoring/101-panel.json
```

### 3. Duplicate a Panel

```bash
# Copy panel
cp etc/grafana/dashboards/src/1-real-time-monitoring/101-power.json \
   etc/grafana/dashboards/src/1-real-time-monitoring/201-power-copy.json

# Edit ID and title
vim etc/grafana/dashboards/src/1-real-time-monitoring/201-power-copy.json
```

### 4. Validate Before Committing

```bash
# Build all dashboards
task dashboards:build

# Validate JSON
for file in etc/grafana/dashboards/*.json; do
  python -m json.tool "$file" > /dev/null || echo "❌ Invalid: $file"
done
```

---

## 🐛 Troubleshooting

### Changes Not Showing in Grafana

**Try**:
1. Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+R)
2. Check dashboard file timestamp:
   ```bash
   ls -la etc/grafana/dashboards/1-real-time-monitoring.json
   ```
3. Check Grafana logs:
   ```bash
   docker compose logs -f grafana
   ```
4. Manually restart Grafana:
   ```bash
   docker compose restart grafana
   ```

### Dashboard Watcher Not Running

**Check**:
```bash
# Is foreman installed?
which foreman

# Install if needed
gem install foreman

# Or run watcher manually
task dashboards:watch
```

### Build Failed

**Check**:
```bash
# Missing _dashboard.json?
ls etc/grafana/dashboards/src/*/

# Re-explode if needed
task dashboards:explode:force
```

---

## 📚 Full Documentation

For complete details, see:

- **Development Workflow**: `docs/dashboard-development-workflow.md`
- **Panel Reference**: `docs/dashboard-panels-canon.md`
- **Utilities**: `scripts/utils/README.md`
- **Task Commands**: `task dashboards:help`

---

## 🎉 You're Ready!

```bash
# Start everything
task dev:dashboards

# Edit panels in etc/grafana/dashboards/src/
# Changes auto-rebuild
# Refresh browser to see updates
# Profit! 🚀
```

---

**Questions?** Check `task dashboards:help` or read the full docs.
