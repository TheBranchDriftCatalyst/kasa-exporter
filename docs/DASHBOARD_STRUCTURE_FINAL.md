# Dashboard Structure - Final Implementation

## 🎉 Complete! You Have BOTH Formats

### Consolidated Dashboards (Production)
**Location**: `etc/grafana/dashboards/*.json`
**Purpose**: Full dashboards with all panels (for production use)
**Example**: `1-real-time-monitoring.json` (30KB, 9 panels)

### Individual Panel Dashboards (Debugging)
**Location**: `etc/grafana/dashboards/_panels/*/`  
**Purpose**: Each panel as a standalone dashboard (for debugging)
**Example**: `_panels/1-real-time-monitoring/101-total-power-draw.json` (3KB, 1 panel)

---

## 📂 Complete Directory Structure

```
etc/grafana/
├── dashboards-src/              # ← SOURCE (you edit here)
│   ├── _common.json             #    Common config injected into all dashboards
│   ├── 1-real-time-monitoring/
│   │   ├── _dashboard.json      #    Dashboard metadata
│   │   ├── 101-total-power-draw.json
│   │   ├── 102-current-cost-rate.json
│   │   └── ...
│   ├── 2-tou-cost-optimization/
│   └── ... (6 dashboards total)
│
└── dashboards/                   # ← BUILT (Grafana reads from here)
    ├── 1-real-time-monitoring.json          # Full dashboard
    ├── 2-tou-cost-optimization.json
    ├── ... (6 consolidated dashboards)
    │
    └── _panels/                  # Individual panel dashboards
        ├── 1-real-time-monitoring/
        │   ├── 101-total-power-draw.json    # Single panel dashboard
        │   ├── 102-current-cost-rate.json
        │   └── ... (9 panels)
        ├── 2-tou-cost-optimization/
        │   └── ... (18 panels)
        └── ... (146 individual panel dashboards total)
```

**Grafana Sees**:
- ✅ 6 consolidated dashboards (production view)
- ✅ 146 individual panel dashboards (debugging view)
- ❌ Nothing from `dashboards-src/` (isolated from Grafana)

---

## 🔨 How to Use

### Edit a Panel

```bash
vim etc/grafana/dashboards-src/1-real-time-monitoring/101-total-power-draw.json
# Edit the query, title, etc.
# Save
```

### Build

```bash
task dashboards:build
```

**Outputs**:
1. **Consolidated**: `dashboards/1-real-time-monitoring.json` (full dashboard)
2. **Individual**: `dashboards/_panels/1-real-time-monitoring/101-total-power-draw.json` (single panel)

### View in Grafana

**Production View** (all panels together):
- Open: `http://localhost:3000/dashboards`
- Click: "Real-Time Monitoring"
- See: Complete dashboard with all 9 panels

**Debug View** (single panel):
- Open: `http://localhost:3000/dashboards`
- Navigate to folder: `_panels` → `1-real-time-monitoring`
- Click: "1-real-time-monitoring/101-total-power-draw"
- See: Just that one panel in isolation

---

## 💡 Why Both Formats?

### Consolidated Dashboards (Production)
✅ See all panels together  
✅ Compare multiple metrics  
✅ Production-ready view  
✅ What users see  

### Individual Panel Dashboards (Debugging)
✅ Test single panel in isolation  
✅ Debug queries without distractions  
✅ Faster iteration (less data to load)  
✅ Check panel-specific config  

---

## 🔧 Common Config Injection

The `_common.json` file contains settings shared across ALL dashboards:

```json
{
  "datasource": {"uid": "PBFA97CFB590B2093"},
  "timezone": "America/Denver",
  "templating": {
    "list": [{"name": "version", ...}]
  },
  "annotations": {...},
  "timepicker": {...}
}
```

**Benefits**:
- Change datasource UID → Edit 1 file, rebuild, ALL 152 dashboards updated (6 + 146)
- Change timezone → Edit 1 file, rebuild, ALL dashboards updated
- Add template variable → Edit 1 file, ALL dashboards get it

---

## 📊 What Gets Built

Running `task dashboards:build` creates:

**6 Consolidated Dashboards**:
1. `1-real-time-monitoring.json` (9 panels)
2. `2-tou-cost-optimization.json` (18 panels)
3. `3-battery-sizing.json` (33 panels)
4. `4-forecasting-analytics.json` (27 panels)
5. `5-comparative-analytics.json` (28 panels)
6. `6-alerts-monitoring.json` (31 panels)

**146 Individual Panel Dashboards** in `_panels/`:
- Dashboard 1: 9 individual panel dashboards
- Dashboard 2: 18 individual panel dashboards
- Dashboard 3: 33 individual panel dashboards
- Dashboard 4: 27 individual panel dashboards
- Dashboard 5: 28 individual panel dashboards
- Dashboard 6: 31 individual panel dashboards

**Total**: 152 dashboards visible to Grafana!

---

## 🎯 Workflow Examples

### Example 1: Debug a Broken Panel

**Problem**: Panel 101 not showing data

**Debug**:
```bash
# Open just that panel
http://localhost:3000/d/panel-101/1-real-time-monitoring-101-total-power-draw

# Check query in isolation
# No distractions from other panels
```

### Example 2: Test Query Changes

**Before** (old way):
1. Edit full dashboard JSON
2. Reload full dashboard (all 9 panels)
3. Find your panel among 9 others
4. Check if query works

**Now**:
```bash
# Edit panel source
vim etc/grafana/dashboards-src/1-real-time-monitoring/101-total-power-draw.json

# Build
task dashboards:build

# Open individual panel dashboard
http://localhost:3000/dashboards → _panels → 1-real-time-monitoring → 101

# See JUST your panel, test query in isolation
```

### Example 3: Compare Panel vs Full Dashboard

**Individual Panel**: `http://localhost:3000/d/panel-101/...`
- Loads fast
- Single query
- Easy to debug

**Full Dashboard**: `http://localhost:3000/d/kasa-realtime-v2/...`
- All 9 panels
- Multiple queries
- Production view

---

## 🚀 Live Reload

```bash
task dev:dashboards
```

**Auto-rebuilds**:
1. Edit any panel source file
2. Watcher detects change
3. Rebuilds BOTH formats:
   - Consolidated dashboard
   - Individual panel dashboard
4. Grafana auto-reloads both
5. Refresh browser

---

## 📝 Version Control

**Commit**:
- ✅ `etc/grafana/dashboards-src/` (source files)
- ✅ `etc/grafana/dashboards-src/_common.json` (common config)

**Don't Commit**:
- ❌ `etc/grafana/dashboards/*.json` (built consolidated dashboards)
- ❌ `etc/grafana/dashboards/_panels/` (built individual dashboards)

**.gitignore**:
```gitignore
# Built dashboards (auto-generated)
etc/grafana/dashboards/*.json
etc/grafana/dashboards/_panels/

# Keep source
!etc/grafana/dashboards-src/
```

---

## 🎉 Summary

You now have:

✅ **152 dashboards in Grafana**:
   - 6 consolidated (production view)
   - 146 individual (debugging view)

✅ **1 source of truth**:
   - Edit `dashboards-src/`
   - Auto-generates both formats

✅ **Common config injection**:
   - Change once, updates everywhere

✅ **Live reload**:
   - Save file → auto-rebuild → auto-reload

✅ **Best of both worlds**:
   - Production: Full dashboards
   - Debugging: Individual panels

**Happy Dashboard Development! 🚀**
