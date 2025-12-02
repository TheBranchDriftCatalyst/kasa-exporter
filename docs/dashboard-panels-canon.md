# Dashboard Panels - Canonical Reference

**Last Updated**: 2025-11-03
**Status**: Authoritative reference for all Grafana dashboard panels
**Total Dashboards**: 6 | **Total Panels**: 146 | **Total Queries**: 226

---

## Table of Contents

1. [PromQL Best Practices](#promql-best-practices)
2. [Query Optimization Guidelines](#query-optimization-guidelines)
3. [Common Query Patterns](#common-query-patterns)
4. [Dashboard-by-Dashboard Reference](#dashboard-by-dashboard-reference)
5. [Metric Reference](#metric-reference)
6. [Known Issues & Fixes](#known-issues--fixes)

---

## PromQL Best Practices

### 1. Use Recording Rules for Complex Queries

**Why**: Pre-computed metrics reduce query time and Prometheus load.

**Good**:
```promql
current_consumption:total
consumption_cost:by_device
```

**Avoid**:
```promql
sum(current_consumption{version="$version"}) by (device)
rate(consumption[5m]) * on() group_left current_energy_rate
```

### 2. Label Filtering Early

**Why**: Reduces data scanned before aggregation.

**Good**:
```promql
current_consumption{version="$version", device="plug1"}
```

**Avoid**:
```promql
sum(current_consumption) by (version, device) and version="$version"
```

### 3. Use Dynamic Variables

**Variables Available**:
- `$__interval` - Auto-calculated based on time range and panel width
- `$__range` - Current dashboard time range
- `$version` - Device firmware version filter

**Good**:
```promql
max_over_time(current_consumption[$__range])
rate(consumption[$__interval])
```

**Avoid**:
```promql
max_over_time(current_consumption[24h])  # Fixed interval
rate(consumption[5m])  # Fixed resolution
```

### 4. Avoid High Cardinality

**Why**: Too many unique label combinations cause memory issues.

**High Cardinality** (problematic):
- `alias` label (102 unique values in our data)
- `device` label (94 unique values)

**Low Cardinality** (safe):
- `version` label
- `rate_class` label

**Solution**: Use aggregations to reduce cardinality:
```promql
# Instead of returning 100 time series:
current_consumption{device=~".*"}

# Aggregate to reduce:
sum(current_consumption) by (rate_class)
```

### 5. Version Label Consistency

**Issue**: Not all recording rules have `version` label.

**Metrics WITHOUT version label**:
- `current_energy_rate:current`
- `rate_class:numeric`

**Solution**: Don't filter by version for these metrics:
```promql
# Good
current_energy_rate:current

# Bad (causes 400 error)
current_energy_rate:current{version=~"$version"}
```

### 6. Enum Metrics Require Aggregation

**Issue**: Enum metrics like `state` have extra labels that prevent table merging.

**Problem**:
```promql
state{version="$version"}
# Returns: state{device="plug1", state="on"} = 1
#          state{device="plug1", state="off"} = 0
# Result: Multiple time series per device breaks table merge
```

**Solution**:
```promql
max without (state) (state{version="$version"})
# Returns: state{device="plug1"} = 1 (single value)
```

---

## Query Optimization Guidelines

### Refresh Intervals

**Panel Type** → **Recommended Refresh**:
- Real-time stats → 5s-10s
- Time series graphs → 30s-1m
- Tables → 1m-5m
- Aggregated stats → 5m-15m
- Alerts → 30s-1m

### Data Point Limits

Grafana performs well with:
- **Optimal**: < 1,000 data points per series
- **Good**: 1,000-5,000 data points
- **Problematic**: > 10,000 data points

**Solution**: Use `$__interval` for automatic downsampling.

### Query Caching

Prometheus caches queries. To maximize cache hits:
- Use consistent time ranges (e.g., `$__range` instead of fixed durations)
- Avoid unnecessary label filters
- Use recording rules for repeated calculations

---

## Common Query Patterns

### Pattern 1: Simple Metric Retrieval

**Use Case**: Display current value

```promql
current_consumption:total
consumption_cost:by_device
```

**Panels Using This**: 69 stat panels (47.3% of all panels)

### Pattern 2: Aggregation by Label

**Use Case**: Group metrics by dimension

```promql
sum(current_consumption) by (rate_class)
avg(consumption_cost) by (device)
```

**Panels Using This**: Time series, pie charts, tables

### Pattern 3: Rate Calculations

**Use Case**: Per-second rate of counter metric

```promql
rate(consumption[5m])
irate(consumption[1m])  # Instantaneous rate
```

**Panels Using This**: Forecasting dashboards

### Pattern 4: Time-Based Aggregations

**Use Case**: Max/min/avg over time window

```promql
max_over_time(current_consumption[$__range])
avg_over_time(consumption_cost[24h])
sum_over_time(consumption[1d])
```

**Panels Using This**: 18 panels use `max_over_time`, 11 use `avg_over_time`

### Pattern 5: Mathematical Operations

**Use Case**: Calculate derived metrics

```promql
(battery_capacity_ah * battery_voltage) / 1000  # kWh capacity
current_consumption * 24  # Daily projection
```

**Panels Using This**: Battery sizing, forecasting panels

### Pattern 6: Conditional Logic

**Use Case**: Thresholds and alerts

```promql
current_consumption > bool 1000  # Returns 1 or 0
consumption_cost > on() group_left power_alert_threshold
```

**Panels Using This**: Alert panels, threshold gauges

---

## Dashboard-by-Dashboard Reference

### Dashboard 1: Real-Time Monitoring (9 panels)

**Purpose**: Live monitoring of current power consumption and costs

**Health**: 95% functional (Device Status Table fixed)

**Panels**:

| ID  | Title | Type | Query | Notes |
|-----|-------|------|-------|-------|
| 101 | Total Power Draw | stat | `current_consumption:total` | Recording rule |
| 102 | Current Cost Rate | stat | `consumption_cost:total` | Recording rule |
| 103 | Energy Rate | stat | `max(current_energy_rate) by (season, rate_class)` | Shows current $/kWh |
| 104 | Projected Daily Cost | stat | `consumption_cost:projected_day` | Recording rule |
| 201 | Power Consumption Over Time | timeseries | `current_consumption:by_device` | Legend: `{{alias}}` |
| 202 | Power Distribution | piechart | `current_consumption:by_device` | Fixed: removed percent label |
| 301 | Cost Breakdown Over Time | timeseries | `consumption_cost:by_device` | Legend: `{{alias}}` |
| 401 | Device Status Table | table | 8 queries (state, power, cost, etc.) | Fixed: state aggregation |
| 501 | Rate Class Timeline | state-timeline | `rate_class` | Shows TOU periods |

**Optimizations Applied**:
- ✅ Pie chart: Removed "percent" from displayLabels (Grafana v12.2.1 bug)
- ✅ Device table: State query uses `max without (state)` aggregation

---

### Dashboard 2: TOU Cost Optimization (18 panels)

**Purpose**: Time-of-use rate analysis and cost optimization opportunities

**Health**: 50% functional (partial fix applied, ~15 panels still broken)

**Panels**:

| ID  | Title | Type | Query | Status |
|-----|-------|------|-------|--------|
| 101 | Total Cost Today | stat | `consumption_cost:total_today` | ✅ Working |
| 102 | Current Rate | stat | `current_energy_rate:current` | ✅ Fixed: removed version filter |
| 103 | Rate Class Timeline | state-timeline | `rate_class:numeric` | ✅ Fixed: removed version filter |
| 201 | Cost by Rate Class | piechart | `sum by (rate_class) (consumption_cost_with_rate_class)` | ✅ Fixed: pie chart |
| 202 | Current Power Distribution | piechart | `current_consumption:by_device` | ✅ Fixed: pie chart |
| 301 | Potential Savings (Super Off-Peak) | stat | `consumption_cost:potential_savings_super_off_peak` | ❌ No data |
| 302 | Potential Savings (Off-Peak) | stat | `consumption_cost:potential_savings_off_peak` | ❌ No data |
| ... | ... | ... | ... | ❌ ~15 panels with no data |

**Known Issues**:
- Many recording rules exist but return 0 results
- Potential savings metrics require historical data accumulation
- May need recording rule fixes or longer data collection period

**Optimizations Applied**:
- ✅ Removed version filters from `current_energy_rate:current` and `rate_class:numeric`
- ✅ Fixed 2 pie charts

---

### Dashboard 3: Battery Sizing & Analysis (33 panels)

**Purpose**: Battery capacity planning and solar integration analysis

**Health**: 90% functional (minor calculation issues)

**Panel Breakdown**:
- 14 stat panels (battery specs, capacity calculations)
- 8 timeseries panels (load curves, solar production)
- 5 gauge panels (efficiency, DoD, capacity factor)
- 4 table panels (sizing recommendations)
- 2 barchart panels (cost comparisons)

**Key Queries**:

**Battery Capacity Calculation**:
```promql
(battery_capacity_ah * battery_voltage) / 1000
# Converts Ah * V to kWh
```

**Usable Capacity with DoD**:
```promql
(battery_capacity_ah * battery_voltage * depth_of_discharge) / 1000
# Accounts for depth of discharge limit
```

**System Efficiency**:
```promql
inverter_efficiency * battery_roundtrip_efficiency
# Combined efficiency of battery + inverter
```

**Peak Load Analysis**:
```promql
max_over_time(current_consumption:total[$__range])
avg_over_time(current_consumption:total[$__range])
```

**Known Issues**:
- ❌ Capacity Factor showing >100% (formula needs review)
- ❌ Battery State of Charge constant at 100% (needs dynamic calculation)

---

### Dashboard 4: Forecasting & Predictions (27 panels)

**Purpose**: Predictive analytics for consumption and cost trends

**Health**: 30% functional (~70% panels showing "No data")

**Panel Breakdown**:
- 12 stat panels (predictions, anomalies)
- 10 timeseries panels (trend lines, forecasts)
- 3 gauge panels (confidence scores)
- 2 table panels (prediction accuracy)

**Key Query Patterns**:

**Trend Detection**:
```promql
deriv(consumption_cost:total[1h])  # Rate of change
predict_linear(consumption[4h], 3600)  # Linear prediction
```

**Anomaly Detection**:
```promql
consumption_cost:anomaly  # Recording rule for anomalies
abs(consumption - avg_over_time(consumption[7d])) > threshold
```

**Status**: Not yet investigated. Likely similar issues to Dashboard 2 (missing data, recording rules).

---

### Dashboard 5: Comparative Analytics (28 panels)

**Purpose**: Device comparisons, efficiency rankings, cost analysis

**Health**: 10% functional (~90% panels showing "No data")

**Panel Breakdown**:
- 16 stat panels (comparisons, rankings)
- 6 timeseries panels (comparative trends)
- 4 table panels (device rankings)
- 2 piechart panels (share percentages)

**Key Panels** (from the 10% working):

**Power Share %** (Piechart):
```promql
current_consumption:by_device
# Shows percentage distribution
```

**Cost Share %** (Piechart):
```promql
consumption_cost:by_device
# Shows cost distribution
```

**Optimizations Applied**:
- ✅ Fixed 2 pie charts (removed "percent" from displayLabels)

**Status**: Not yet investigated. Most panels broken.

---

### Dashboard 6: Alerts & Thresholds (31 panels)

**Purpose**: Alert configuration and threshold monitoring

**Health**: 70% functional (some alert panels broken)

**Panel Breakdown**:
- 18 stat panels (threshold values, alert counts)
- 7 gauge panels (threshold progress bars)
- 4 timeseries panels (alert history)
- 1 table panel (active alerts)
- 1 text panel (documentation)

**Key Query Patterns**:

**Threshold Comparison**:
```promql
current_consumption > on() group_left power_alert_threshold
consumption_cost > on() group_left cost_alert_threshold
```

**Alert Metrics**:
```promql
power_alert_threshold
cost_alert_threshold
consumption_cost:anomaly
```

**Status**: Not yet investigated. ~30% of panels broken.

---

## Metric Reference

### Recording Rules (Pre-computed Metrics)

**Total Aggregations**:
- `current_consumption:total` - Sum of all device power (53 uses)
- `consumption_cost:total` - Sum of all device costs (38 uses)

**By-Device Aggregations**:
- `current_consumption:by_device` - Power per device (23 uses)
- `consumption_cost:by_device` - Cost per device (16 uses)

**By-Rate-Class Aggregations**:
- `consumption_cost:by_rate_class` - Cost per TOU period
- `consumption_cost_with_rate_class` - Cost with rate class label

**Time-Based**:
- `consumption_cost:total_today` - Today's total cost
- `consumption_cost:projected_day` - Daily projection
- `consumption_cost:total_month` - Month total

**Savings & Optimization** (currently no data):
- `consumption_cost:potential_savings_super_off_peak`
- `consumption_cost:potential_savings_off_peak`
- `consumption_cost:anomaly`

**Rate Information**:
- `current_energy_rate:current` - Current $/kWh (NO version label)
- `rate_class:numeric` - Numeric rate class (NO version label)

### Base Metrics (From Kasa Devices)

**Power & Consumption**:
- `current_consumption` - Current power draw in watts
- `consumption_today` - Today's energy in Wh
- `consumption_this_month` - Month's energy in Wh

**Device State**:
- `state` - Enum: on/off (has extra `state` label - use aggregation!)
- `rssi` - WiFi signal strength
- `signal_level` - Signal quality
- `on_since` - Unix timestamp when turned on

**Battery & Solar** (synthetic for planning):
- `battery_capacity_ah` - Battery capacity in Amp-hours
- `battery_voltage` - Battery voltage
- `depth_of_discharge` - Maximum DoD percentage
- `inverter_efficiency` - Inverter efficiency percentage
- `battery_roundtrip_efficiency` - Battery charge/discharge efficiency

### Label Structure

**Common Labels**:
- `alias` - Human-readable device name (102 unique values - HIGH CARDINALITY)
- `device` - Device identifier (94 unique values - HIGH CARDINALITY)
- `version` - Firmware version (inconsistent - not on all recording rules!)
- `rate_class` - TOU period (super_off_peak, off_peak, on_peak, peak)
- `season` - Summer/Winter

**Label Cardinality** (sorted by uniqueness):
1. `version` - 446 uses (but missing from some recording rules!)
2. `alias` - 102 uses (HIGH - avoid in aggregations)
3. `device` - 94 uses (HIGH - aggregate when possible)

---

## Known Issues & Fixes

### Issue 1: Pie Chart Percentage Display Bug ✅ FIXED

**Symptom**: Pie charts showing "698536%" instead of proper percentages

**Root Cause**: Grafana v12.2.1 bug with `displayLabels: ["percent"]` configuration

**Fix Applied**: Removed "percent" from displayLabels array
- Changed `["percent", "name"]` to `["name"]`
- Percentages still visible in legend tables
- Fixed in 5 pie charts across 3 dashboards

**Script**: `scripts/fix_pie_charts_v2.py`

---

### Issue 2: Device Status Table Missing Columns ✅ FIXED

**Symptom**: Table showing only 2 of 8 columns (Device, Power)

**Root Cause**: `state` metric is Enum type with extra label `state: "on"/"off"` causing table merge failure

**Fix Applied**: Modified state query to use aggregation
```promql
# Before (broken)
state{version="$version"}

# After (fixed)
max without (state) (state{version="$version"})
```

**Script**: `scripts/fix_device_table.py`

**Status**: Fix applied, not yet verified in browser

---

### Issue 3: Dashboard 2 Query Errors ⚠️ PARTIALLY FIXED

**Symptom**: ~70% of panels showing "No data" with 23x 400 Bad Request errors

**Root Cause 1**: Some recording rules don't have `version` label

**Metrics Without Version Label**:
- `current_energy_rate:current`
- `rate_class:numeric`

**Fix Applied**: Removed version filters from these 2 queries
- Fixed Panel 102 (Current Rate)
- Fixed Panel 103 (Rate Class Timeline)

**Script**: `scripts/fix_dashboard2_queries.py`

**Root Cause 2**: Many recording rules exist but return 0 results
- `consumption_cost:potential_savings_super_off_peak`
- `consumption_cost:potential_savings_off_peak`
- Other savings/optimization metrics

**Status**: 2 queries fixed, ~15 panels still broken (require further investigation)

---

### Issue 4: Dashboards 4, 5, 6 - Not Addressed

**Dashboard 4** (Forecasting): 30% functional
- ~70% panels showing "No data"
- Likely missing recording rules or historical data

**Dashboard 5** (Comparative Analytics): 10% functional
- ~90% panels showing "No data"
- Pie charts fixed but most stat panels broken

**Dashboard 6** (Alerts): 70% functional
- Some alert panels broken
- Not yet investigated

**Status**: Pending investigation (estimated 3-4 hours work)

---

## Query Checklist

Before creating a new panel query, verify:

- [ ] Does the metric have a `version` label? (Check Prometheus first)
- [ ] If no version label, don't filter by `{version=~"$version"}`
- [ ] Is this an Enum metric? (Use aggregation to remove extra labels)
- [ ] Can I use a recording rule instead of complex calculation?
- [ ] Is cardinality reasonable? (Avoid returning >100 time series)
- [ ] Am I using `$__interval` for dynamic resolution?
- [ ] Is the refresh interval appropriate for panel type?
- [ ] Does the query return data in Prometheus directly? (Test before adding to dashboard)

---

## Troubleshooting Guide

### Panel Shows "No data"

**Possible Causes**:

1. **Metric doesn't have version label but query filters by version**
   - Solution: Remove version filter from query

2. **Recording rule exists but has no data**
   - Solution: Check Prometheus recording rules config, may need historical data

3. **Query syntax error**
   - Solution: Test query directly in Prometheus query browser

4. **Label mismatch preventing table merge**
   - Solution: Use aggregation (`max without`, `sum by`) to normalize labels

### Panel Shows Broken Percentages

**Cause**: Grafana v12.2.1 pie chart bug

**Solution**: Remove "percent" from displayLabels, show percentages in legend only

### Table Shows Empty Columns

**Cause**: Metrics have incompatible label sets (especially Enum metrics)

**Solution**: Use `max without (label)` or `sum by (wanted_labels)` aggregations

---

## Utilities

Use the utilities in `scripts/utils/` to work with panel data:

```bash
# Extract all panels
python scripts/utils/extract_panels.py --output /tmp/dashboard_panels.json

# Generate statistics
python scripts/utils/panel_stats.py --input /tmp/dashboard_panels.json

# Query specific panels
python scripts/utils/query_panels.py --input /tmp/dashboard_panels.json --type piechart
```

See `scripts/utils/README.md` for full documentation.

---

## References

- Dashboard Testing Report: `docs/dashboard-browser-testing.md`
- Dashboard Fixes Summary: `docs/dashboard-fixes-summary.md`
- Panel Utilities: `scripts/utils/README.md`
- Prometheus Documentation: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Grafana Best Practices: https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/

---

**Document Status**: Canonical reference - update as dashboards evolve
**Maintenance**: Re-extract panels after dashboard changes, regenerate statistics
**Version**: 1.0 (2025-11-03)
