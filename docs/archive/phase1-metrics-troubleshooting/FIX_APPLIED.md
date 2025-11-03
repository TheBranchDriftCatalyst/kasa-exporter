# Fix Applied: consumption_cost Metric Cardinality Bug

**Date**: 2025-11-01
**Status**: ✅ READY TO DEPLOY

---

## Summary

Fixed the label persistence bug where `consumption_cost` metric was emitting 3 time series per device (18 total) instead of 1 per device (6 total), causing all cost queries to return 3x the actual value.

**Solution**: Implemented Option 1 from `docs/METRIC_STRUCTURE_REDESIGN.md` - removed `rate_class` label from `consumption_cost` metric.

---

## Changes Made

### 1. Metric Definition (`kasa_exporter/devices/KP125M.py`)

**File**: `kasa_exporter/devices/KP125M.py:134-143`

**Before**:
```python
"consumption_cost": {
    "type": PromMetricType.GAUGE,
    "getter": lambda device: calculator.calc_rate(
        device.state_information["Current consumption"]
    ),
    "derive_labels": {
        "rate_class": lambda _d: calculator.get_rate_name(
            datetime.now(pytz.timezone("America/Denver")),
            calculator.get_current_season()
        ),
    },
},
```

**After**:
```python
"consumption_cost": {
    "type": PromMetricType.GAUGE,
    "getter": lambda device: calculator.calc_rate(
        device.state_information["Current consumption"]
    ),
    # Note: rate_class label removed to prevent label cardinality explosion
    # Rate class info available via current_energy_rate metric
},
```

**Impact**:
- ✅ Reduces metric cardinality from 18 to 6 time series
- ✅ Eliminates stale label combinations
- ✅ `sum(consumption_cost)` now returns correct value
- ℹ️ `rate_class` info still available via `current_energy_rate` metric

---

### 2. Dashboard Updates

#### power-analytics.json

**Panel 14**: "💰 Cost by TOU Rate Class" → "💰 Total Cost (Time Range)"

**Before**:
```promql
sum by (rate_class) (avg_over_time(consumption_cost{version=~"$version"}[$__range]) * ($__range_s / 3600))
```

**After**:
```promql
sum(avg_over_time(consumption_cost{version=~"$version"}[$__range]) * ($__range_s / 3600))
```

**Change**: Removed `by (rate_class)` grouping, changed from pie chart to stat panel

---

#### load-shift-savings.json

**Panel 10**: "⚡ Energy by Rate Class" → "⚡ Total Energy (Time Range)"

**Before**:
```promql
sum by (rate_class) (avg_over_time(current_consumption{version=~"$version"}[$__range]) * ($__range_s / 3600) / 1000)
```

**After**:
```promql
sum(avg_over_time(current_consumption{version=~"$version"}[$__range]) * ($__range_s / 3600) / 1000)
```

**Change**: Removed `by (rate_class)` grouping, changed from pie chart to stat panel

---

**Panel 11**: "💰 Cost by Rate Class" → "💰 Total Cost (Time Range)"

**Before**:
```promql
sum by (rate_class) (avg_over_time(consumption_cost{version=~"$version"}[$__range]) * ($__range_s / 3600))
```

**After**:
```promql
sum(avg_over_time(consumption_cost{version=~"$version"}[$__range]) * ($__range_s / 3600))
```

**Change**: Removed `by (rate_class)` grouping, changed from pie chart to stat panel

---

### 3. All Other Queries

The following queries **already work correctly** and need no changes:

✅ `sum(consumption_cost{version=~"$version"})` - Total Real-time Cost
✅ `max by (alias) (consumption_cost{version=~"$version"})` - Cost by Device
✅ Savings calculations in load-shift-savings dashboard
✅ All time series visualizations

---

## Deployment Instructions

### Quick Start

```bash
cd /Users/panda/catalyst-devspace/workspace/@kasa-exporter
./scripts/fix_consumption_cost_bug.sh
```

This script will:
1. Stop all services
2. Clear Prometheus database
3. Restart with fixed configuration
4. Verify the fix

### Manual Deployment

If you prefer to deploy manually:

```bash
# 1. Stop services
docker-compose down

# 2. Remove Prometheus data
docker volume rm kasa-exporter_prometheus-data
docker volume create kasa-exporter_prometheus-data

# 3. Restart services
docker-compose up -d

# 4. Verify (wait 30 seconds for first scrape)
curl -s 'http://localhost:9090/api/v1/query?query=count(consumption_cost)' | \
  jq -r '.data.result[0].value[1]'
# Should return: "6" (not "18")
```

---

## Verification

After deployment, verify the fix:

### 1. Check Metric Cardinality

```bash
# Should return exactly 6 (one per device)
curl -s 'http://localhost:9090/api/v1/query?query=count(consumption_cost)' | \
  jq -r '.data.result[0].value[1]'
```

**Expected**: `6`
**Before fix**: `18`

### 2. Check Metrics Endpoint

```bash
curl -s http://localhost:9200/metrics | grep '^consumption_cost{' | wc -l
```

**Expected**: `6` lines
**Before fix**: `18` lines

### 3. Verify No rate_class Label

```bash
curl -s http://localhost:9200/metrics | grep '^consumption_cost{' | head -3
```

**Expected output**:
```
consumption_cost{alias="Device1",device_id="...",model="KP125M",version="0.4.0"} 0.035
consumption_cost{alias="Device2",device_id="...",model="KP125M",version="0.4.0"} 0.012
consumption_cost{alias="Device3",device_id="...",model="KP125M",version="0.4.0"} 0.008
```

**Note**: No `rate_class` label present ✅

### 4. Check Dashboard Values

```bash
# Total cost should be reasonable (~$0.10-0.40/hour)
curl -s 'http://localhost:9090/api/v1/query?query=sum(consumption_cost)' | \
  jq -r '.data.result[0].value[1]'
```

**Expected**: `0.1` to `0.4` (depending on current consumption)
**Before fix**: `0.3` to `1.2` (3x too high)

### 5. Visual Verification

Open dashboards and verify panels show correct data:

- **Power Analytics**: http://localhost:3000/d/admmdt5
  - "Total Real-time Cost" should show reasonable value
  - "💰 Total Cost (Time Range)" should show accumulated cost

- **Load Shift Savings**: http://localhost:3000/d/loadshift001
  - "💰 Instant Savings Potential" should show positive value
  - "📊 Savings Percentage" should show 30-50%
  - "💸 Cost Comparison Over Time" should show 3 distinct lines

---

## Rollback Procedure

If you need to rollback:

```bash
cd /Users/panda/catalyst-devspace/workspace/@kasa-exporter

# 1. Revert code changes
git checkout HEAD -- kasa_exporter/devices/KP125M.py
git checkout HEAD -- etc/grafana/dashboards/power-analytics.json
git checkout HEAD -- etc/grafana/dashboards/load-shift-savings.json

# 2. Restart services
docker-compose restart kasa-exporter grafana
```

**Note**: Prometheus data doesn't need to be cleared for rollback.

---

## Expected Behavior After Fix

### Metrics Endpoint

```bash
$ curl -s http://localhost:9200/metrics | grep '^consumption_cost{'

consumption_cost{alias="6985",device_id="...",model="KP125M",version="0.4.0"} 0.106
consumption_cost{alias="Dream Machine",device_id="...",model="KP125M",version="0.4.0"} 0.035
consumption_cost{alias="Fatboy Synology",device_id="...",model="KP125M",version="0.4.0"} 0.031
consumption_cost{alias="Furbo",device_id="...",model="KP125M",version="0.4.0"} 0.001
consumption_cost{alias="Lab Server",device_id="...",model="KP125M",version="0.4.0"} 0.004
consumption_cost{alias="Reality Forge",device_id="...",model="KP125M",version="0.4.0"} 0.005
```

**Total: 6 metrics** (one per device, no rate_class label)

### Prometheus Query

```promql
sum(consumption_cost)
```

**Returns**: `~0.182` (actual current cost)
**Before**: `~0.546` (3x inflated)

### Dashboard "Load Shift Savings Analysis"

- **Instant Savings Potential**: `$0.09/hr`
- **Savings Percentage**: `40%`
- **Daily Savings**: `$2.16`
- **Monthly Savings**: `$64.80`
- **Yearly Savings**: `$788.40`

All values should now be **accurate** (not inflated by 3x).

---

## What We Lost

### ❌ Removed Features

1. **Cost by TOU Rate Class pie chart** - Can no longer show cost breakdown by on_peak/off_peak/super_off_peak
2. **Energy by TOU Rate Class pie chart** - Can no longer show energy breakdown by rate period

### ✅ Alternatives

To get rate class breakdown, you can still:

1. **Check current rate class**:
   ```promql
   current_energy_rate{version=~"$version"}
   ```
   This shows the current rate and includes `rate_class` label

2. **Calculate theoretical costs manually**:
   ```promql
   # Cost if all at super_off_peak
   sum(current_consumption) / 1000 * 0.314

   # Cost if all at off_peak
   sum(current_consumption) / 1000 * 0.351

   # Cost if all at on_peak
   sum(current_consumption) / 1000 * 0.634
   ```

3. **Future enhancement**: Implement Option 2 from redesign doc
   - Add explicit metrics: `consumption_cost_if_super_off_peak`, etc.
   - Would enable "what-if" analysis without label cardinality issues

---

## Benefits of This Fix

1. ✅ **Correct cost reporting** - Dashboards show actual costs (not 3x inflated)
2. ✅ **Reduced cardinality** - 6 metrics instead of 18 (better Prometheus performance)
3. ✅ **No stale metrics** - Label combinations don't accumulate over time
4. ✅ **Lower memory usage** - Fewer time series to track
5. ✅ **Simpler queries** - No need for workarounds or divisions by 3
6. ✅ **Follows best practices** - Prometheus recommends low cardinality

---

## Related Documentation

- `docs/BUG.md` - Original bug report with evidence
- `docs/METRIC_STRUCTURE_REDESIGN.md` - Solution options and Mermaid diagrams
- `docs/METRICS_AUDIT_PLAN.md` - Investigation plan (Phase 1-3 completed, Phase 4-6 skipped)
- `docs/DASHBOARD_MIGRATION_GUIDE.md` - Query migration reference
- `scripts/fix_consumption_cost_bug.sh` - Deployment automation

---

## Testing Checklist

After deployment, test:

- [ ] Metric cardinality is 6 (not 18)
- [ ] No `rate_class` label on `consumption_cost` metrics
- [ ] `sum(consumption_cost)` returns reasonable value (~$0.10-0.40/hr)
- [ ] Power Analytics dashboard displays correctly
- [ ] Load Shift Savings dashboard shows positive savings
- [ ] All panels render without errors
- [ ] Savings calculations are logical (30-50% potential savings)
- [ ] Historical cost data starts accumulating correctly

---

## Support

If you encounter issues:

1. Check logs: `docker-compose logs kasa-exporter`
2. Verify Prometheus is scraping: http://localhost:9090/targets
3. Check metrics endpoint: http://localhost:9200/metrics
4. Review `docs/BUG.md` for troubleshooting

---

**Status**: ✅ Ready for deployment
**Last Updated**: 2025-11-01
**Author**: Claude Code
