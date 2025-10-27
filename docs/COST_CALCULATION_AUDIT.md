# Cost Calculation Audit

## Overview

The Kasa Exporter implements a time-of-use (TOU) pricing model to calculate real-time energy costs based on:
- Current power consumption (watts)
- Time of day (off-peak, mid-peak, on-peak)
- Season (summer, winter)

## Implementation Details

### Location
- **Calculator**: `kasa_exporter/utils/time_of_use_calc.py`
- **Usage**: `kasa_exporter/devices/KP125M.py` (line 113-128)
- **Metric**: `consumption_cost` (Prometheus gauge)

### Formula

```python
cost_rate = (current_consumption_watts / 1000) * rate_per_kwh
```

This gives you the **instantaneous cost rate in $/hour**.

**Example:**
- Device drawing 50W during summer on-peak ($0.28/kWh)
- Cost rate = (50 / 1000) * 0.28 = $0.014/hour
- Over 1 hour = $0.014
- Over 24 hours (if constant) = $0.336

## Current Configuration

### Summer Rates (June 1 - Sept 30)
- **Off-Peak** ($0.11/kWh): 00:00-13:00, 19:00-00:00
- **Mid-Peak** ($0.19/kWh): 13:00-15:00
- **On-Peak** ($0.28/kWh): 15:00-19:00

### Winter Rates (Dec 1 - Feb 28)
- **Off-Peak** ($0.10/kWh): 00:00-06:00, 20:00-23:59
- **Mid-Peak** ($0.17/kWh): 06:00-14:00, 18:00-20:00
- **On-Peak** ($0.25/kWh): 14:00-18:00

### Timezone
- Uses **America/Denver** timezone
- Configured in `time_of_use_calc.py:76-78`

## Issues Found & Fixed

### ✅ FIXED: Wrong date type in rate_name calculation

**Original Problem (KP125M.py:125):**
```python
"rate_class": lambda _d: calculator.get_rate_name(
    date.today(), calculator.get_current_season()
),
```

**Impact:**
- `date.today()` doesn't have time component
- Function always returned "off_peak" as default
- All cost metrics showed wrong rate_class label

**First Fix (Commit 53249e8):**
```python
"rate_class": lambda _d: calculator.get_rate_name(
    datetime.now(pytz.timezone("America/Denver")),
    calculator.get_current_season()
),
```

**Problem with First Fix:**
- Caused **metric staleness** when rate_class changed
- Old label combinations persisted in Prometheus
- Created visual artifacts in Grafana (flat lines at old values)

**Final Fix (Option 4 - Metric Separation):**
Split into two metrics to avoid derive_labels cardinality explosion:

```python
"consumption_cost": {
    "type": PromMetricType.GAUGE,
    "getter": lambda device: calculator.calc_rate(
        device.state_information["Current consumption"]
    ),
    # No derive_labels - simple per-device cost rate
},
"current_energy_rate": {
    "type": PromMetricType.GAUGE,
    "getter": lambda _d: calculator.get_rate_for_time(
        datetime.now(pytz.timezone("America/Denver")),
        calculator.get_current_season()
    ),
    "derive_labels": {
        "season": lambda _d: calculator.get_current_season(),
        "rate_class": lambda _d: calculator.get_rate_name(...)
    },
},
```

**Why This Works:**
- `consumption_cost` - Simple gauge per device (no stale labels)
- `current_energy_rate` - Single metric tracks current rate with season/rate_class
- When rate changes, only ONE metric updates (not per-device)
- No cardinality explosion (devices × seasons × rate_classes)
- Grafana can join them if needed: `consumption_cost * on() group_left() current_energy_rate`

### 🟡 MEDIUM: Season gap coverage (March-May, October-November)

**Problem:**
```python
"season": {
    "summer": ["06-01", "09-30"],
    "winter": ["12-01", "02-28"],
}
```

**Missing months:**
- Spring: March 1 - May 31
- Fall: October 1 - November 30

**Current behavior:**
- Falls back to "summer" rates (line 47)
- Not ideal - should have explicit spring/fall rates or expand summer/winter

**Fix Options:**
1. Add spring/fall seasons with their own rates
2. Extend summer to cover Mar-Nov
3. Extend winter to cover Oct-May

### 🟡 MEDIUM: Year-wrap logic untested (winter spanning Dec-Feb)

**Problem:**
```python
if start <= today <= end or (start > end and (today >= start or today <= end)):
```

**Issue:**
- Winter is defined as "12-01" to "02-28"
- The year-wrap logic attempts to handle this, but it's complex
- Leap years (Feb 29) not handled
- Untested edge case

**Test cases needed:**
- Dec 15 → should be winter ✓
- Jan 15 → should be winter ✓
- Feb 29 (leap year) → currently would NOT match "02-28"

### 🟢 LOW: Time range comparison uses string comparison

**Problem:**
```python
if start <= current_time_str <= end:
```

**Issue:**
- Works for most cases but fails for ranges spanning midnight
- Example: `("19:00", "00:00")` in summer off-peak
- String comparison: "19:00" <= "23:30" <= "00:00" → FALSE
- "23:30" is NOT less than "00:00" in string comparison

**Current behavior:**
- The time range `("00:00", "13:00"), ("19:00", "00:00")` is split into two tuples
- This works around the issue, but it's fragile
- If someone writes `("19:00", "01:00")` it would break

**Better approach:**
Convert to datetime objects for comparison, or handle midnight wrap explicitly.

### 🟢 LOW: Hardcoded timezone

**Problem:**
```python
current_time = datetime.now(pytz.timezone("UTC")).astimezone(
    pytz.timezone("America/Denver")
)
```

**Issue:**
- Timezone is hardcoded to Denver (Mountain Time)
- Should be configurable via environment variable

**Suggested fix:**
```python
TZ = os.getenv("EXPORTER_TIMEZONE", "America/Denver")
current_time = datetime.now(pytz.timezone("UTC")).astimezone(pytz.timezone(TZ))
```

## Dashboard Implications

The Grafana dashboard uses the `consumption_cost` metric with labels:
- `rate_class` - Shows which rate tier (off_peak/mid_peak/on_peak)
- `season` - Shows current season (summer/winter)

**Current state:**
- Season detection is working correctly
- Rate class is BROKEN due to date.today() bug
- All devices likely showing "off_peak" regardless of actual time

**After fix:**
- Dashboard will correctly show rate transitions throughout the day
- Cost calculations will be accurate
- Can track peak vs off-peak usage patterns

## Recommendations

### Immediate (Critical)
1. ✅ Fix `date.today()` → `datetime.now()` bug in KP125M.py
2. ✅ Test rate_class label updates in real-time
3. ✅ Verify Grafana dashboard shows correct rate transitions

### Short-term (Medium Priority)
1. ✅ Define spring/fall seasons or extend existing seasons
2. ✅ Add leap year handling for winter (Feb 29)
3. ✅ Add unit tests for season detection edge cases

### Long-term (Low Priority)
1. ✅ Make timezone configurable via environment variable
2. ✅ Refactor time range comparison to handle midnight wrapping
3. ✅ Add validation for TOU configuration on startup
4. ✅ Consider moving to a TOU pricing library or database

## Testing Checklist

- [ ] Test during each time period (off-peak, mid-peak, on-peak)
- [ ] Verify rate transitions happen at correct times
- [ ] Test season transitions (May 31→June 1, Sept 30→Oct 1, etc.)
- [ ] Verify winter season detection (Dec, Jan, Feb)
- [ ] Test leap year (Feb 29)
- [ ] Verify timezone handling
- [ ] Check Prometheus metrics have correct labels
- [ ] Verify Grafana dashboard displays correct rates

## Related Files

- `kasa_exporter/utils/time_of_use_calc.py` - Core calculator
- `kasa_exporter/devices/KP125M.py` - Device metric definitions
- `etc/grafana/dashboards/power-analytics.json` - Dashboard using cost data
