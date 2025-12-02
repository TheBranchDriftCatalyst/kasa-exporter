# Dashboard Panel Utilities

Utilities for extracting, querying, and analyzing Grafana dashboard panels without loading massive JSON files into context.

## Problem

The dashboard JSON files are too large (>100KB each) to read directly, causing context limit issues. These utilities extract the relevant panel information into manageable chunks.

## Utilities

### 1. `extract_panels.py` - Extract Panel Data

Extract panels from dashboard JSON files into a lightweight format.

```bash
# Extract all panels from all dashboards
python scripts/utils/extract_panels.py --output /tmp/dashboard_panels.json

# Extract from specific dashboard
python scripts/utils/extract_panels.py --dashboard 1-real-time-monitoring.json

# Extract only specific fields (smaller output)
python scripts/utils/extract_panels.py --fields id,title,type,targets
```

**Output**: JSON file with dashboard metadata and panel information.

### 2. `query_panels.py` - Query Specific Panels

Query and filter panels from extracted data without loading full dashboards.

```bash
# Find panel by ID
python scripts/utils/query_panels.py --input /tmp/dashboard_panels.json --id 101

# Find panels by title (partial match, case-insensitive)
python scripts/utils/query_panels.py --title "power"

# Find panels in specific dashboard
python scripts/utils/query_panels.py --dashboard "2-tou"

# Find panels by type
python scripts/utils/query_panels.py --type "piechart"

# Find panels using specific metric
python scripts/utils/query_panels.py --query-pattern "current_consumption"

# Combine filters
python scripts/utils/query_panels.py --dashboard "1-real" --type "stat"

# Show only specific fields
python scripts/utils/query_panels.py --id 101 --fields id,title,targets

# Count matching panels
python scripts/utils/query_panels.py --type "timeseries" --count
```

### 3. `panel_stats.py` - Generate Statistics

Analyze panels and generate statistics reports.

```bash
# Full statistics report
python scripts/utils/panel_stats.py --input /tmp/dashboard_panels.json

# Statistics for specific dashboard
python scripts/utils/panel_stats.py --dashboard "2-tou"

# Export statistics as JSON
python scripts/utils/panel_stats.py --output stats.json
```

**Statistics Included**:
- Total dashboards, panels, queries
- Panels per dashboard
- Panel type distribution
- Top metrics by usage
- Version filtering usage
- Panels without queries

## Typical Workflow

```bash
# Step 1: Extract panels from dashboards
python scripts/utils/extract_panels.py --output /tmp/dashboard_panels.json

# Step 2: Generate statistics overview
python scripts/utils/panel_stats.py --input /tmp/dashboard_panels.json

# Step 3: Query specific panels for analysis
python scripts/utils/query_panels.py --input /tmp/dashboard_panels.json --type piechart

# Step 4: Export specific panel data
python scripts/utils/query_panels.py --id 101 --fields title,targets > panel_101.json
```

## Use Cases

### Finding All Pie Charts

```bash
python scripts/utils/query_panels.py --type piechart
```

### Finding Panels Using Specific Metric

```bash
python scripts/utils/query_panels.py --query-pattern "consumption_cost:potential_savings"
```

### Analyzing Dashboard Complexity

```bash
# How many queries per dashboard?
python scripts/utils/panel_stats.py

# Which metrics are most used?
python scripts/utils/panel_stats.py | grep -A 20 "TOP 20 METRICS"
```

### Getting Panel Details for Documentation

```bash
# Get all panels from Dashboard 1 with only essential fields
python scripts/utils/query_panels.py --dashboard "1-real" --fields id,title,type,targets
```

## Output Format

### Extracted Panels JSON

```json
[
  {
    "file": "1-real-time-monitoring.json",
    "title": "🌊 Real-Time Monitoring",
    "uid": "kasa-realtime",
    "description": "Real-time power consumption monitoring",
    "panel_count": 9,
    "panels": [
      {
        "id": 101,
        "title": "⚡ Total Power Draw",
        "type": "stat",
        "gridPos": {...},
        "targets": [
          {
            "refId": "A",
            "expr": "current_consumption:total",
            "legendFormat": ""
          }
        ],
        "fieldConfig": {...},
        "options": {...}
      }
    ]
  }
]
```

### Statistics JSON

```json
{
  "total_dashboards": 6,
  "total_panels": 146,
  "total_queries": 226,
  "unique_metrics": 92,
  "panels_by_dashboard": {
    "1-real-time-monitoring.json": 9,
    "2-tou-cost-optimization.json": 18
  },
  "panel_types": {
    "stat": 69,
    "timeseries": 33,
    "table": 20
  },
  "metrics_used": {
    "current_consumption": 53,
    "consumption_cost:total": 38
  }
}
```

## Benefits

1. **Context Efficient**: Extract only what you need instead of loading 100KB+ files
2. **Fast Queries**: Filter and search without parsing full JSON each time
3. **Analytics**: Understand dashboard composition and metric usage patterns
4. **Documentation**: Generate canonical documentation from extracted data
5. **Debugging**: Quickly find problematic panels or queries

## Current Dashboard Stats

As of last extraction:

- **Total Dashboards**: 6
- **Total Panels**: 146
- **Total Queries**: 226
- **Unique Metrics**: 92
- **Most Common Panel Type**: stat (47.3%)
- **Version Filtered Queries**: 90.3%

## Related Documentation

- `docs/dashboard-browser-testing.md` - Original browser testing report
- `docs/dashboard-fixes-summary.md` - Dashboard fixes session summary
- `docs/dashboard-panels-canon.md` - Canonical panel documentation (generated from these utilities)
