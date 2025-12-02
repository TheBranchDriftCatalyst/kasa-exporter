# Dashboard Common Configuration

## Overview

The `_common.json` file in `etc/grafana/dashboards/src/` contains shared configuration that gets injected into all dashboards at build time. This ensures consistency across all dashboards while keeping the source files DRY (Don't Repeat Yourself).

## Location

```
etc/grafana/dashboards/src/_common.json
```

## What Gets Injected

The following configuration is automatically injected into every dashboard:

### 1. Datasource Configuration

```json
{
  "datasource": {
    "type": "prometheus",
    "uid": "PBFA97CFB590B2093"
  }
}
```

**Why**: Ensures all dashboards use the same Prometheus datasource. Change it once, updates everywhere.

### 2. Timezone

```json
{
  "timezone": "America/Denver"
}
```

**Why**: Consistent timezone across all dashboards.

### 3. Template Variables

```json
{
  "templating": {
    "list": [
      {
        "name": "version",
        "type": "query",
        "query": "label_values(current_consumption, version)",
        "datasource": {
          "type": "prometheus",
          "uid": "PBFA97CFB590B2093"
        }
      }
    ]
  }
}
```

**Why**: All dashboards have the same template variables (like `$version` filter).

### 4. Annotations

```json
{
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": {
          "type": "grafana",
          "uid": "-- Grafana --"
        },
        "enable": true,
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  }
}
```

**Why**: Consistent annotation settings.

### 5. Time Picker

```json
{
  "timepicker": {
    "refresh_intervals": [
      "5s",
      "10s",
      "30s",
      "1m",
      "5m",
      "15m",
      "30m",
      "1h",
      "2h",
      "1d"
    ]
  }
}
```

**Why**: Same refresh interval options across all dashboards.

### 6. Other Settings

- `editable`: true
- `graphTooltip`: 2 (shared crosshair)
- `fiscalYearStartMonth`: 0
- `schemaVersion`: 39
- `tags`: ["kasa"]
- `links`: []

---

## How It Works

### Build Process

1. **Load Common Config**
   ```bash
   task dashboards:build
   ```
   - Reads `etc/grafana/dashboards/src/_common.json`
   - Parses JSON, removes `$schema` and `_comment` fields

2. **For Each Dashboard**
   - Loads dashboard-specific `_dashboard.json`
   - **Merges** common config with dashboard config
   - Dashboard-specific settings **override** common settings
   - Adds panels
   - Writes final dashboard to `etc/grafana/dashboards/`

3. **Merge Strategy**
   ```
   Final Dashboard = Common Config + Dashboard Config + Panels
                     └─ Common defaults ─┘
                                └─ Dashboard-specific overrides ─┘
   ```

### Example

**Common Config** (`_common.json`):
```json
{
  "timezone": "America/Denver",
  "refresh": "10s"
}
```

**Dashboard Config** (`1-real-time-monitoring/_dashboard.json`):
```json
{
  "title": "Real-Time Monitoring",
  "refresh": "5s"  // Override
}
```

**Final Built Dashboard**:
```json
{
  "timezone": "America/Denver",  // From common
  "refresh": "5s",               // From dashboard (overridden)
  "title": "Real-Time Monitoring",
  "panels": [...]
}
```

---

## Editing Common Config

### Change Datasource UID

Edit `_common.json`:

```json
{
  "datasource": {
    "type": "prometheus",
    "uid": "NEW_UID_HERE"  // ← Change this
  }
}
```

Rebuild:
```bash
task dashboards:build
```

All dashboards now use the new datasource UID!

### Change Timezone

```json
{
  "timezone": "UTC"  // ← Change from "America/Denver"
}
```

### Add New Template Variable

Add to `templating.list`:

```json
{
  "templating": {
    "list": [
      {
        "name": "version",
        "type": "query",
        "query": "label_values(current_consumption, version)"
      },
      {
        "name": "device",  // ← New variable
        "type": "query",
        "query": "label_values(current_consumption, device)"
      }
    ]
  }
}
```

Now all dashboards have a `$device` variable!

---

## Dashboard-Specific Overrides

Individual dashboards can override common settings.

**Example**: Different refresh rate for one dashboard:

`etc/grafana/dashboards/src/1-real-time-monitoring/_dashboard.json`:
```json
{
  "title": "Real-Time Monitoring",
  "uid": "kasa-realtime-v2",
  "refresh": "5s",  // ← Override common default
  "time": {
    "from": "now-1h",
    "to": "now"
  }
}
```

**Result**: This dashboard refreshes every 5s, others use the common default (10s).

---

## Benefits

### 1. DRY (Don't Repeat Yourself)

**Before** (without `_common.json`):
- Each `_dashboard.json`: ~100 lines
- Change datasource UID → Edit 6 files
- Add template variable → Edit 6 files

**After** (with `_common.json`):
- Each `_dashboard.json`: ~20 lines (only unique settings)
- Change datasource UID → Edit 1 file
- Add template variable → Edit 1 file

### 2. Consistency

All dashboards automatically have:
- Same datasource
- Same timezone
- Same template variables
- Same refresh intervals
- Same annotation settings

### 3. Easy Updates

Need to change Prometheus datasource?

```bash
# Edit one file
vim etc/grafana/dashboards/src/_common.json

# Rebuild all dashboards
task dashboards:build

# Done! All 6 dashboards updated
```

### 4. Dashboard-Specific Customization

Still allows individual dashboards to override when needed:
- Different refresh rates
- Custom time ranges
- Additional template variables
- Dashboard-specific tags

---

## Common Use Cases

### 1. Change Prometheus Datasource

```bash
# Edit common config
vim etc/grafana/dashboards/src/_common.json

# Change datasource.uid
# Save

# Rebuild
task dashboards:build

# All dashboards now use new datasource
```

### 2. Add Global Template Variable

Want a `$environment` filter across all dashboards?

```json
{
  "templating": {
    "list": [
      {
        "name": "version",
        "type": "query",
        "query": "label_values(current_consumption, version)"
      },
      {
        "name": "environment",
        "type": "custom",
        "options": [
          {"text": "Production", "value": "prod"},
          {"text": "Staging", "value": "staging"}
        ]
      }
    ]
  }
}
```

Rebuild → All dashboards have `$environment`.

### 3. Change Timezone for All Dashboards

```json
{
  "timezone": "UTC"  // Or "browser", "America/New_York", etc.
}
```

### 4. Update Refresh Intervals

```json
{
  "timepicker": {
    "refresh_intervals": [
      "10s",   // Removed 5s
      "30s",
      "1m",
      "5m"
    ]
  }
}
```

---

## Advanced Usage

### Conditional Common Config

You could maintain multiple common config files:

```
etc/grafana/dashboards/src/
├── _common.json          # Default
├── _common.prod.json     # Production settings
├── _common.dev.json      # Development settings
```

Then build with different configs:
```bash
# Development
cp _common.dev.json _common.json && task dashboards:build

# Production
cp _common.prod.json _common.json && task dashboards:build
```

### Per-Dashboard Customization

Dashboard can extend or override:

```json
{
  "title": "Special Dashboard",
  "templating": {
    "list": [
      // This dashboard has ADDITIONAL variables beyond common
      {
        "name": "special_metric",
        "type": "query",
        "query": "label_values(special_metric, label)"
      }
    ]
  }
}
```

**Note**: Currently dashboard-specific templating replaces common templating. For merging, you'd need to enhance the build script.

---

## Troubleshooting

### Common Config Not Applied

**Check**:
1. File exists: `ls etc/grafana/dashboards/src/_common.json`
2. Valid JSON: `python -m json.tool etc/grafana/dashboards/src/_common.json`
3. Rebuild: `task dashboards:build`
4. Check build output for "Loaded common configuration"

### Dashboard Override Not Working

**Remember**: Dashboard-specific settings override common.

**Merge Order**:
```
Common → Dashboard → Result
```

If dashboard specifies a value, it wins.

### Want to Merge Template Variables

**Current**: Dashboard variables replace common variables.

**Workaround**: Manually copy common variables to dashboard `_dashboard.json`.

**Future Enhancement**: Could modify `build_dashboards.py` to deep-merge `templating.list`.

---

## File Format

### Full `_common.json` Schema

```json
{
  "$schema": "https://grafana.com/schema/dashboard-common-config-v1.json",
  "_comment": "Common configuration shared across all dashboards",

  "datasource": {
    "type": "prometheus",
    "uid": "DATASOURCE_UID"
  },

  "timezone": "America/Denver",
  "editable": true,
  "graphTooltip": 2,
  "fiscalYearStartMonth": 0,
  "schemaVersion": 39,

  "annotations": {
    "list": [...]
  },

  "templating": {
    "list": [...]
  },

  "timepicker": {
    "refresh_intervals": [...]
  },

  "tags": ["tag1", "tag2"],
  "links": []
}
```

### Metadata Fields (Ignored)

- `$schema` - For IDE autocomplete
- `_comment` - For documentation

These are stripped before injection.

---

## Version Control

**Commit**:
- ✅ `etc/grafana/dashboards/src/_common.json`
- ✅ `etc/grafana/dashboards/src/*/_dashboard.json`

**Don't Commit**:
- ❌ `etc/grafana/dashboards/*.json` (built files)

---

## Related Documentation

- **Development Workflow**: `docs/dashboard-development-workflow.md`
- **Quick Start**: `docs/DASHBOARD_QUICKSTART.md`
- **Panel Reference**: `docs/dashboard-panels-canon.md`
- **Build Script**: `scripts/utils/build_dashboards.py`

---

**Last Updated**: 2025-11-03
