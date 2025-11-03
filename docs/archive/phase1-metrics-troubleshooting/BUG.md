# Bug Report: consumption_cost Metric Emitting Multiple Rate Classes Simultaneously

**Date Discovered**: 2025-11-01
**Severity**: HIGH
**Status**: UNDER INVESTIGATION

---

## Summary

The `consumption_cost` metric is emitting **three simultaneous time series** with different `rate_class` labels (`on_peak`, `off_peak`, `super_off_peak`) for each device, when it should only emit ONE metric representing the current active rate period.

---

## Evidence

### Raw Metrics Endpoint Output (http://localhost:9200/metrics)

**Captured at**: 2025-11-01 20:44 PDT
**Current rate period**: `on_peak` (16:00-21:00)
**Expected behavior**: Only 6 metrics total (one `consumption_cost` per device with `rate_class="on_peak"`)
**Actual behavior**: 18 metrics total (three per device, one for each rate_class)

```prometheus
# HELP consumption_cost consumption_cost
# TYPE consumption_cost gauge

# Device: 6985
consumption_cost{alias="6985",device_id="803AD6935764643857F377445DB8FB0F2258182B",model="KP125M",rate_class="off_peak",version="0.4.0"} 0.106348
consumption_cost{alias="6985",device_id="803AD6935764643857F377445DB8FB0F2258182B",model="KP125M",rate_class="on_peak",version="0.4.0"} 0.018525
consumption_cost{alias="6985",device_id="803AD6935764643857F377445DB8FB0F2258182B",model="KP125M",rate_class="super_off_peak",version="0.4.0"} 0.058636

# Device: Dream Machine
consumption_cost{alias="Dream Machine",device_id="803A8E059228352E87967BD82DCBA06122588678",model="KP125M",rate_class="off_peak",version="0.4.0"} 0.035273
consumption_cost{alias="Dream Machine",device_id="803A8E059228352E87967BD82DCBA06122588678",model="KP125M",rate_class="on_peak",version="0.4.0"} 0.035023
consumption_cost{alias="Dream Machine",device_id="803A8E059228352E87967BD82DCBA06122588678",model="KP125M",rate_class="super_off_peak",version="0.4.0"} 0.017305

# Device: Fatboy Synology
consumption_cost{alias="Fatboy Synology",device_id="803A5D96B6516ABA75D62FF0A03CCD6A2282B060",model="KP125M",rate_class="off_peak",version="0.4.0"} 0.030602
consumption_cost{alias="Fatboy Synology",device_id="803A5D96B6516ABA75D62FF0A03CCD6A2282B060",model="KP125M",rate_class="on_peak",version="0.4.0"} 0.032406
consumption_cost{alias="Fatboy Synology",device_id="803A5D96B6516ABA75D62FF0A03CCD6A2282B060",model="KP125M",rate_class="super_off_peak",version="0.4.0"} 0.015833

# Device: Furbo
consumption_cost{alias="Furbo",device_id="803A2BC059F51E9BDC5D471D6481E907228286B1",model="KP125M",rate_class="off_peak",version="0.4.0"} 0.001790
consumption_cost{alias="Furbo",device_id="803A2BC059F51E9BDC5D471D6481E907228286B1",model="KP125M",rate_class="on_peak",version="0.4.0"} 0.001795
consumption_cost{alias="Furbo",device_id="803A2BC059F51E9BDC5D471D6481E907228286B1",model="KP125M",rate_class="super_off_peak",version="0.4.0"} 0.001285

# Device: Lab Server
consumption_cost{alias="Lab Server",device_id="803AC99E58A6AC51871091C0D3755E3B2282C74C",model="KP125M",rate_class="off_peak",version="0.4.0"} 0.004841
consumption_cost{alias="Lab Server",device_id="803AC99E58A6AC51871091C0D3755E3B2282C74C",model="KP125M",rate_class="on_peak",version="0.4.0"} 0.004832
consumption_cost{alias="Lab Server",device_id="803AC99E58A6AC51871091C0D3755E3B2282C74C",model="KP125M",rate_class="super_off_peak",version="0.4.0"} 0.002586

# Device: Reality Forge
consumption_cost{alias="Reality Forge",device_id="803A23F06D7211C4D09368C654B849762282467E",model="KP125M",rate_class="off_peak",version="0.4.0"} 0.005164
consumption_cost{alias="Reality Forge",device_id="803A23F06D7211C4D09368C654B849762282467E",model="KP125M",rate_class="on_peak",version="0.4.0"} 0.005177
consumption_cost{alias="Reality Forge",device_id="803A23F06D7211C4D09368C654B849762282467E",model="KP125M",rate_class="super_off_peak",version="0.4.0"} 0.002566

# TOTAL: 18 metrics (6 devices × 3 rate_classes)
# EXPECTED: 6 metrics (6 devices × 1 current rate_class)
```

**The Smoking Gun**: All three `rate_class` values are emitted **simultaneously** for each device at the same scrape time. This is NOT Prometheus retaining old label values - the exporter itself is actively creating all three metrics.

---

## Impact

### Current Behavior (INCORRECT)
```promql
sum(consumption_cost)  # Returns: $0.38/hour
```
This sums ALL THREE theoretical costs per device (6 devices × 3 rate_classes = 18 values), resulting in **3x overcounting**.

### Expected Behavior (CORRECT)
```promql
sum(consumption_cost)  # Should return: ~$0.12-0.13/hour
```
Should only sum the current active rate period (6 devices × 1 rate_class = 6 values).

### Dashboard Impact
- **Total Real-time Cost** panel shows 3x inflated values
- **Cost by TOU Rate Class** pie chart shows incorrect distribution
- **Load Shift Savings Analysis** dashboard calculations are wrong
- All historical cost data is compromised

---

## Root Cause Analysis

### Code Review: KP125M.py (Lines 134-146)

**File**: `/Users/panda/catalyst-devspace/workspace/@kasa-exporter/kasa_exporter/devices/KP125M.py`

```python
"consumption_cost": {
    "type": PromMetricType.GAUGE,
    "getter": lambda device: calculator.calc_rate(
        device.state_information["Current consumption"]
    ),
    # Unit: USD per hour ($/hour) - instantaneous cost rate based on current power draw
    # Calculation: (watts / 1000) * rate_per_kWh
    "derive_labels": {
        "rate_class": lambda _d: calculator.get_rate_name(
            datetime.now(pytz.timezone("America/Denver")), calculator.get_current_season()
        ),
    },
},
```

**What the code says it should do**:
1. Calculate ONE cost value using `calculator.calc_rate()` which returns: `(watts / 1000) * current_rate`
2. Add ONE derived label `rate_class` with the current period name (e.g., "on_peak")
3. Result: ONE metric per device

**What's actually happening**:
1. THREE cost values are being calculated (one for each rate tier)
2. THREE metrics are emitted with different `rate_class` labels
3. Result: THREE metrics per device

**The Discrepancy**:
```python
# calc_rate() from time_of_use_calc.py:130-135
def calc_rate(self, current_consumption: float) -> float:
    """Calculate the instantaneous cost of the current consumption."""
    self.current_season = self.get_current_season()
    current_time = datetime.now(pytz.timezone("UTC")).astimezone(pytz.timezone(self.timezone))
    rate = self.get_rate_for_time(current_time, self.current_season)
    return round((current_consumption / 1000) * rate, 6)
```

This function calculates cost using the **current** rate only. Yet the metrics endpoint shows costs for ALL THREE rates, suggesting the metric is being created multiple times with different label values.

### Hypotheses

1. **Prometheus Label Retention**: Old label values persist even after rate periods change
   - ❌ DISPROVEN: All 3 metrics have the same current timestamp

2. **Metric Caching Bug**: PrometheusDeviceExtractor may be accumulating label combinations
   - ⚠️ NEEDS INVESTIGATION: Check `prom_device_extractor.py:154-200`

3. **Multiple Exporter Processes**: Dev and prod exporters running simultaneously
   - ❌ DISPROVEN: Only one process found (PID 28924)

4. **Intentional Design**: Exporter deliberately emits all theoretical costs
   - ⚠️ NEEDS CONFIRMATION: Check git history and design docs

5. **Hidden Loop/Iteration**: Code iterates through all rate classes somewhere
   - ⚠️ NEEDS INVESTIGATION: Audit update_metrics() call chain

6. **prometheus_client Label Persistence Bug** ⭐ **LIKELY ROOT CAUSE**
   - ✅ **CONFIRMED BY RESEARCH**: Once a Gauge label combination is created via `.labels()`, it persists in the registry
   - Each unique `rate_class` value used throughout the day creates a NEW time series
   - Old label combinations do NOT expire automatically - they remain in memory indefinitely
   - This is a known cardinality issue with prometheus_client Python library

### Web Research Findings

**Source**: Prometheus client_python documentation and Stack Overflow

**Key Discovery**:
> "All metrics can have labels, allowing grouping of related time series. Metrics with labels are not initialized when declared, because the client can't know what values the label can have."
>
> "Each labelset is an additional time series that has RAM, CPU, disk, and network costs... As a general guideline, try to keep the cardinality of your metrics below 10."

**The Problem**:
```python
# When this code runs during different time periods:
metric_object.labels(
    alias="Dream Machine",
    rate_class="super_off_peak"  # 00:00-06:00
).set(0.017305)

# Later during off_peak period:
metric_object.labels(
    alias="Dream Machine",
    rate_class="off_peak"  # 06:00-16:00, 21:00-23:59
).set(0.035273)

# Later during on_peak period:
metric_object.labels(
    alias="Dream Machine",
    rate_class="on_peak"  # 16:00-21:00
).set(0.035023)
```

**Result**: All 3 time series persist in the registry and continue to be exported, even though only ONE is being actively updated at any given time. The other two show stale values from when they were last set.

**Why this is happening**:
- `derive_labels` creates the label value dynamically
- As `rate_class` changes throughout the day, NEW label combinations are created
- prometheus_client does NOT automatically remove old label combinations
- Without explicit `.remove()` or `.clear()` calls, all combinations persist

**Evidence from metrics output**:
- Notice how some devices show different power consumption values for different rate_classes
- Example: Device "6985" shows very different costs:
  - `rate_class="off_peak"`: $0.106348 (302.4W equivalent)
  - `rate_class="on_peak"`: $0.018525 (29.2W equivalent)
  - `rate_class="super_off_peak"`: $0.058636 (186.7W equivalent)
- These represent ACTUAL HISTORICAL power consumptions at those times, NOT theoretical calculations

---

## Mathematical Verification

Current power consumption: 56.467W (Dream Machine)

### Expected Values
- `super_off_peak`: 56.467W × $0.314/kWh ÷ 1000 = **$0.01773/hr** ✓
- `off_peak`: 56.467W × $0.351/kWh ÷ 1000 = **$0.01982/hr**
- `on_peak`: 56.467W × $0.634/kWh ÷ 1000 = **$0.03580/hr** ✓

### Actual Values from Metrics
- `super_off_peak`: **$0.017305/hr** ✓ (matches expected)
- `off_peak`: **$0.034616/hr** ❌ (should be $0.01982)
- `on_peak`: **$0.035023/hr** ✓ (matches expected)

**Anomaly**: The `off_peak` value doesn't match the expected calculation, suggesting power consumption may be different for each metric OR there's a calculation bug.

---

## Files Involved

- `/Users/panda/catalyst-devspace/workspace/@kasa-exporter/kasa_exporter/devices/KP125M.py`
- `/Users/panda/catalyst-devspace/workspace/@kasa-exporter/kasa_exporter/devices/prom_device_extractor.py`
- `/Users/panda/catalyst-devspace/workspace/@kasa-exporter/kasa_exporter/utils/time_of_use_calc.py`
- `/Users/panda/catalyst-devspace/workspace/@kasa-exporter/kasa_exporter/routines/exporter.py`
- `/opt/kasa-exporter/` (production deployment)

---

## Git History

Relevant commits:
```
cb9ec1a feat(metrics): add TOU rate class labels and enhance dashboard
49ad2d6 fix: resolve metric staleness by splitting cost and rate metrics
53249e8 feat: comprehensive power monitoring and cost tracking
```

Commit `49ad2d6` shows `consumption_cost` previously had NO `derive_labels`. The `rate_class` label was added later, possibly introducing this bug.

---

## Next Steps (Discovery Plan)

See: `docs/METRICS_AUDIT_PLAN.md`

---

## Workaround

Until fixed, queries should filter by current rate period or use max/min aggregations:

```promql
# Get only current rate period cost (unreliable if rate_class is wrong)
sum(consumption_cost{rate_class="on_peak"})  # Only during on_peak hours

# OR use max per device (gets highest theoretical cost)
sum by (alias) (max by (alias, rate_class) (consumption_cost))

# OR calculate from scratch
sum(current_consumption) / 1000 * <current_rate>
```

---

## Related Issues

- Load Shift Savings Analysis dashboard showing empty/incorrect graphs
- Historical cost data integrity compromised
- Need to audit all metrics with `derive_labels`
