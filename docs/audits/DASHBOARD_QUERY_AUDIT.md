# Power Analytics Dashboard Query Audit

**Date**: 2025-11-01
**Dashboard**: `power-analytics.json` (WC - Kasa Power Analytics)
**Purpose**: Audit all Prometheus queries for correct integration/differentiation and instant vs range query usage

---

## Executive Summary

### Critical Findings

1. **✅ CORRECT**: "💰 Cost by TOU Rate Class" (Panel 14) uses `instant=true` with integration
2. **⚠️ ISSUE**: Panel uses `$__range` which creates overlapping windows in range queries
3. **✅ CORRECT**: All device-level queries correctly use `max by (alias)` for differentiation
4. **✅ CORRECT**: Battery runtime calculations correctly use `sum()` for total system power

---

## Query Inventory by Panel

### 📊 Overview & Real-time Monitoring Section

#### Panel 13: ⚡ Current Energy Rate ($/kWh)
- **Type**: `stat`
- **Query**: `max(current_energy_rate{version=~"$version"}) by (season, rate_class)`
- **instant**: `null` (range query)
- **Analysis**:
  - ✅ **CORRECT**: Uses `max by (season, rate_class)` to show current rate per rate class
  - ℹ️ This is a **rate** ($/kWh), not accumulated, so range query is appropriate for showing current value
  - The metric has labels: `season`, `rate_class`

#### Panel 10: Total Real-time Cost
- **Type**: `stat`
- **Query**: `sum by (alias) (consumption_cost{version=~"$version"})`
- **instant**: `null` (range query)
- **Analysis**:
  - ⚠️ **POTENTIAL ISSUE**: Uses `sum by (alias)` but this is showing cost **rate** ($/hour)
  - Should this be showing total across all devices? If so, remove `by (alias)`
  - **Recommendation**: Change to `sum(consumption_cost{version=~"$version"})` for total system cost rate

#### Panel 2: Lab Server - Current Draw
- **Type**: `gauge`
- **Query**: `max by (alias) (current_consumption{version=~"$version"})`
- **instant**: `null` (range query)
- **Analysis**:
  - ✅ **CORRECT**: Shows instantaneous power per device
  - Uses `max by (alias)` for per-device differentiation

#### Panel 6: Energy Consumed Today
- **Type**: `bargauge`
- **Query**: `max by (alias) (consumption_today{version=~"$version"}) / 1000`
- **instant**: `null` (range query)
- **Analysis**:
  - ✅ **CORRECT**: Shows per-device cumulative energy (converted to kWh)
  - `consumption_today` is already accumulated by the device, so this is correct

---

### 📈 Time Series Visualizations

#### Panel 8: Stacked Power Consumption Over Time
- **Type**: `timeseries`
- **Query**: `max by (alias) (current_consumption{version=~"$version"})`
- **instant**: `null` (range query)
- **Analysis**:
  - ✅ **CORRECT**: Range query for time series visualization
  - Correctly differentiates by device with `max by (alias)`

#### Panel 9: Real-time Cost Rate by Device
- **Type**: `timeseries`
- **Query**: `max by (alias) (consumption_cost{version=~"$version"})`
- **instant**: `null` (range query)
- **Analysis**:
  - ✅ **CORRECT**: Range query for time series
  - Shows cost **rate** ($/hour) per device over time
  - Correctly uses `max by (alias)` for per-device differentiation

#### Panel 17: 💵 Cost Rate History (Stacked)
- **Type**: `timeseries`
- **Query**: `max by (alias) (consumption_cost{version=~"$version"})`
- **instant**: `null` (range query)
- **Analysis**:
  - ✅ **CORRECT**: Same as Panel 9, appropriate for time series

#### Panel 16: 📈 Monthly Energy Consumption Trend
- **Type**: `timeseries`
- **Query**: `max by (alias) (consumption_this_month{version=~"$version"}) / 1000`
- **instant**: `null` (range query)
- **Analysis**:
  - ✅ **CORRECT**: Shows cumulative monthly consumption over time
  - `consumption_this_month` accumulates within the month, resets monthly

#### Panel 12: Device Uptime (Hours Since On)
- **Type**: `timeseries`
- **Query**: `max by (alias) (on_since{version=~"$version"})`
- **instant**: `null` (range query)
- **Analysis**:
  - ✅ **CORRECT**: Shows uptime counter over time

#### Panel 11: WiFi Signal Strength (RSSI)
- **Type**: `timeseries`
- **Query**: `max by (alias) (rssi{version=~"$version"})`
- **instant**: `null` (range query)
- **Analysis**:
  - ✅ **CORRECT**: Time series of signal strength

---

### 🥧 Pie Charts & Distribution

#### Panel 7: Power Distribution (Current)
- **Type**: `piechart`
- **Query**: `max by (alias) (current_consumption{version=~"$version"})`
- **instant**: `null` (range query)
- **Analysis**:
  - ⚠️ **SHOULD USE INSTANT**: Pie charts should show a single snapshot
  - **Recommendation**: Change to `instant: true`

#### Panel 14: 💰 Cost by TOU Rate Class
- **Type**: `piechart`
- **Query**:
  ```promql
  sum by (rate_class) (avg_over_time(consumption_cost{version=~"$version"}[$__range]) * ($__range_s / 3600))
  ```
- **instant**: `true` ✅
- **Analysis**:
  - ✅ **CORRECT APPROACH**: Uses instant query for integration
  - ✅ **CORRECT**: Sums by rate_class (not by device) to aggregate cost across TOU buckets
  - ⚠️ **VERIFICATION NEEDED**: The formula integrates cost over time

  **How it works**:
  1. `consumption_cost` = instantaneous cost rate in $/hour per device (with `rate_class` label)
  2. `avg_over_time(...[$__range])` = average cost rate over the dashboard time range
  3. `* ($__range_s / 3600)` = multiply by hours to get total cost
  4. `sum by (rate_class)` = aggregate all devices' costs into TOU buckets

  **Math check**:
  - If `consumption_cost` = 0.05 $/hour (constant)
  - Over 6 hours: `avg_over_time = 0.05 $/hour`
  - Integration: `0.05 * 6 = $0.30` total cost ✅

  **Correctness**: ✅ This is the right approach for "total cost spent in each TOU period"

#### Panel 20: 🥧 Monthly Energy Distribution
- **Type**: `piechart`
- **Query**: `max by (alias) (consumption_this_month{version=~"$version"}) / 1000`
- **instant**: `null` (range query)
- **Analysis**:
  - ⚠️ **SHOULD USE INSTANT**: Pie charts should show a single snapshot
  - **Recommendation**: Change to `instant: true`

---

### 🔋 Battery Runtime Calculations

#### Panel 21: 🔋 Total System Battery Runtime (All Voltages)
- **Type**: `timeseries`
- **Multiple queries**: 15 queries for different battery capacities (12V, 24V, 48V at various Ah)
- **Example query**: `(100 * 12 * 0.8 * 0.9) / sum(max by (alias) (current_consumption{version=~"$version"}))`
- **instant**: `null` (range query)
- **Analysis**:
  - ✅ **CORRECT**: Uses `sum()` to integrate total system power consumption
  - Formula: `Runtime (hours) = (Ah * Voltage * DoD * Efficiency) / Total_Watts`
  - Where: DoD=0.8 (80% depth of discharge), Efficiency=0.9 (90% inverter efficiency)
  - ✅ Correctly shows time series of how runtime would change as load changes

#### Panel 106: ⚡ Battery Capacity Comparison (Current Runtime)
- **Type**: `bargauge`
- **Same queries as Panel 21**
- **instant**: `true` ✅
- **Analysis**:
  - ✅ **CORRECT**: Uses instant query for current snapshot comparison
  - Shows current runtime estimates for different battery configurations

---

### 📊 Status & Info Panels

#### Panel 15: 📊 Device Status Table
- **Type**: `table`
- **7 queries**, all with `instant: true` ✅:
  1. `max by (alias) (state{state="on", version=~"$version"})`
  2. `max by (alias) (current_consumption{version=~"$version"})`
  3. `max by (alias) (consumption_cost{version=~"$version"})`
  4. `max by (alias) (consumption_today{version=~"$version"}) / 1000`
  5. `max by (alias) (consumption_this_month{version=~"$version"}) / 1000`
  6. `max by (alias) (on_since{version=~"$version"})`
  7. `max by (alias) (rssi{version=~"$version"})`
- **Analysis**:
  - ✅ **CORRECT**: All use instant queries for current status snapshot
  - ✅ **CORRECT**: All use `max by (alias)` for per-device breakdown

#### Panel 18: ☁️ Cloud Connection Status
- **Type**: `gauge`
- **Query**: `max by (alias) (cloud_connection{cloud_connection="connected", version=~"$version"})`
- **instant**: `null` (range query)
- **Analysis**:
  - ⚠️ **SHOULD USE INSTANT**: Status gauges should show current state
  - **Recommendation**: Change to `instant: true`

#### Panel 19: 🔄 Firmware Update Status
- **Type**: `gauge`
- **Query**: `max by (alias) (update_available{update_available="yes", version=~"$version"})`
- **instant**: `null` (range query)
- **Analysis**:
  - ⚠️ **SHOULD USE INSTANT**: Status gauges should show current state
  - **Recommendation**: Change to `instant: true`

---

## Metric Structure Reference

### `consumption_cost` Metric
- **Type**: Gauge
- **Unit**: $/hour (instantaneous cost rate)
- **Formula**: `(watts / 1000) * rate_per_kWh`
- **Labels**:
  - `device_id`: Device identifier
  - `alias`: Device name
  - `model`: Device model
  - `rate_class`: TOU period (super_off_peak, off_peak, on_peak)
  - `version`: Exporter version

### `current_energy_rate` Metric
- **Type**: Gauge
- **Unit**: $/kWh
- **Values**: 0.314 (super_off_peak), 0.351 (off_peak), 0.634 (on_peak)
- **Labels**:
  - `season`: summer or winter
  - `rate_class`: TOU period name
  - `version`: Exporter version

---

## Integration vs Differentiation Analysis

### When to Integrate (sum without by)
✅ **Panel 14**: Cost by TOU Rate Class
- Uses `sum by (rate_class)` to aggregate all devices into TOU buckets
- **Correct**: We want total cost per rate class across all devices

✅ **Panel 21/106**: Battery Runtime
- Uses `sum()` to get total system power consumption
- **Correct**: Battery must power the entire system

### When to Differentiate (max by alias)
✅ **Most panels**: Per-device metrics
- Uses `max by (alias)` to show individual device metrics
- **Correct**: Allows tracking individual device consumption and cost

### Potential Issues
⚠️ **Panel 10**: "Total Real-time Cost"
- Currently uses `sum by (alias)` which still differentiates by device
- Title says "Total" but query shows per-device breakdown
- **Recommendation**: Either:
  - Change query to `sum(consumption_cost{version=~"$version"})` for true total
  - Or change title to "Real-time Cost per Device"

---

## Instant vs Range Query Analysis

### Should Use Instant Query ✅
1. ✅ **Panel 14**: Cost by TOU (pie chart) - Uses instant ✓
2. ✅ **Panel 15**: Device Status Table - Uses instant ✓
3. ✅ **Panel 106**: Battery Capacity Comparison - Uses instant ✓
4. ⚠️ **Panel 7**: Power Distribution (pie chart) - Should use instant
5. ⚠️ **Panel 20**: Monthly Energy Distribution (pie chart) - Should use instant
6. ⚠️ **Panel 18**: Cloud Connection Status (gauge) - Should use instant
7. ⚠️ **Panel 19**: Firmware Update (gauge) - Should use instant

### Correctly Use Range Query ✅
All time series panels (8, 9, 11, 12, 16, 17, 21) correctly use range queries

---

## TOU Calculation Verification

### How TOU Labels Are Assigned

From `KP125M.py:134-145`:
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
}
```

### TOU Rate Assignment Logic

From `time_of_use_calc.py:108-117`:
```python
def get_rate_name(self, current_time: datetime, season: str) -> str:
    """Determine the rate name based on the current time and time ranges."""
    current_time_str = current_time.strftime("%H:%M")
    for period, ranges in self.config[season].items():
        if period == "rate":  # Skip rate dict
            continue
        for time_range in ranges:
            if self._time_in_range(current_time_str, time_range[0], time_range[1]):
                return period
    return "off_peak"
```

### Cost Calculation

From `time_of_use_calc.py:130-135`:
```python
def calc_rate(self, current_consumption: float) -> float:
    """Calculate the instantaneous cost of the current consumption."""
    self.current_season = self.get_current_season()
    current_time = datetime.now(pytz.timezone("UTC")).astimezone(pytz.timezone(self.timezone))
    rate = self.get_rate_for_time(current_time, self.current_season)
    return round((current_consumption / 1000) * rate, 6)
```

### Verification
✅ **CORRECT BEHAVIOR**:
1. Each metric scrape captures the current time's rate_class as a label
2. `consumption_cost` metric = instantaneous cost rate ($/hour) with rate_class label
3. Over time, metrics accumulate with different rate_class labels
4. Panel 14 aggregates historical costs by rate_class using `sum by (rate_class)`

**Example**:
- 8:00 AM (off_peak): `consumption_cost{alias="Lab Server", rate_class="off_peak"} = 0.0351`
- 4:00 PM (on_peak): `consumption_cost{alias="Lab Server", rate_class="on_peak"} = 0.0634`
- Query: `sum by (rate_class) (avg_over_time(...))` correctly buckets these into rate classes

---

## Recommendations Summary

### High Priority
1. ⚠️ **Panel 10**: Clarify if "Total" means sum across devices or per-device
   - If total: Change to `sum(consumption_cost{version=~"$version"})`
   - If per-device: Rename to "Real-time Cost per Device"

### Medium Priority
2. ⚠️ **Pie Charts** (Panels 7, 20): Change to `instant: true`
3. ⚠️ **Status Gauges** (Panels 18, 19): Change to `instant: true`

### Low Priority / Nice to Have
4. ℹ️ Consider adding a panel showing total accumulated cost across all TOU periods
5. ℹ️ Consider adding trend analysis showing cost savings by shifting usage to off-peak

---

## Conclusion

✅ **Overall Assessment**: Dashboard is well-structured with mostly correct query patterns

**Key Strengths**:
- Panel 14 (Cost by TOU) correctly uses instant query with integration
- Battery runtime calculations correctly integrate total system power
- Per-device metrics correctly use differentiation with `max by (alias)`
- Time series panels appropriately use range queries

**Areas for Improvement**:
- Some snapshot panels (pie charts, status gauges) should use instant queries
- Panel 10 title/query mismatch needs clarification
