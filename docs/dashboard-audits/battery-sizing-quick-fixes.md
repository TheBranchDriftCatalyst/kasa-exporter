# Battery Sizing Dashboard - Quick Fix Guide

**Dashboard:** `3-battery-sizing.json`  
**Priority:** Address 3 critical issues + 4 medium priority optimizations

---

## Critical Issues (Fix Immediately)

### 1. Panel 402: Cumulative Energy Draw ⚠️
**Current Query:**
```promql
sum by(alias) (increase(current_consumption{alias=~"$device", version=~"$version"}[1h]) / 3600)
```

**Problem:** `increase()` doesn't work on gauge metrics (current_consumption is instantaneous power)

**Fix Option A** (if energy counter exists):
```promql
sum by(alias) (energy_consumption_wh{alias=~"$device", version=~"$version"})
```

**Fix Option B** (approximate using power):
```promql
sum by(alias) (avg_over_time(current_consumption{alias=~"$device", version=~"$version"}[1h]))
```

---

### 2. Panel 603: ROI Payback Period ⚠️
**Current Query:**
```promql
(($battery_voltage * $battery_capacity_ah * 1.5) / (sum(increase(consumption_cost{alias=~"$device", version=~"$version"}[24h])) * 0.3 * 365))
```

**Problem:** Numerator is Wh (energy), denominator is $ (currency) - unit mismatch

**Fix:** Add battery cost per Wh (assume $0.50/Wh for example):
```promql
(($battery_voltage * $battery_capacity_ah * 1.5 * 0.50) / (sum(increase(consumption_cost{alias=~"$device", version=~"$version"}[24h])) * 0.3 * 365))
```

Or add a template variable `$battery_cost_per_wh` and use:
```promql
(($battery_voltage * $battery_capacity_ah * 1.5 * $battery_cost_per_wh) / (sum(increase(consumption_cost{alias=~"$device", version=~"$version"}[24h])) * 0.3 * 365))
```

---

### 3. Panel 702: Capacity Factor ⚠️
**Current Query:**
```promql
sum(current_consumption{alias=~"$device", version=~"$version"}) / ($battery_voltage * $battery_capacity_ah * $inverter_efficiency)
```

**Problem:** Divides power (W) by energy (Wh) - dimensionally inconsistent

**Fix:** Invert to show "runtime remaining":
```promql
($battery_voltage * $battery_capacity_ah * $inverter_efficiency) / sum(current_consumption{alias=~"$device", version=~"$version"})
```

And change title to: "⏱️ Runtime Remaining (hours)" with unit "h"

**OR** keep formula but change title to: "⚡ Hourly Discharge Rate" and clarify it shows "fraction of battery capacity used per hour"

---

## Medium Priority (Optimize Performance)

### 4. Panel 101: Total Load
**Current:** Has `"range": true` in targets[0]

**Fix:** Change to instant query
```json
"range": false
```

---

### 5. Panel 403: Load Duration Curve
**Current Query:**
```promql
sort_desc(sum(current_consumption{alias=~"$device", version=~"$version"}))
```

**Problem:** Shows single point, not a curve

**Fix:** Use range query to build histogram:
```promql
histogram_quantile(0.95, sum(rate(current_consumption{alias=~"$device", version=~"$version"}[5m])) by (le))
```

Or simpler - just show distribution over time without sort_desc()

---

### 6. Panel 807: Runtime with Solar Recharge
**Current Query:**
```promql
($battery_voltage * $battery_capacity_ah * $depth_of_discharge * $inverter_efficiency) / (sum(current_consumption{alias=~"$device", version=~"$version"}) - ($solar_panel_watts * $inverter_efficiency * 0.5))
```

**Problem:** Can divide by negative number if solar > load

**Fix:** Add safety clamp:
```promql
($battery_voltage * $battery_capacity_ah * $depth_of_discharge * $inverter_efficiency) / clamp_min((sum(current_consumption{alias=~"$device", version=~"$version"}) - ($solar_panel_watts * $inverter_efficiency * 0.5)), 0.1)
```

---

### 7. Panel 808: Battery SoC Timeline (Low Priority)
**Issue:** Uses simulated data with `time() % 86400`, not real measurements

**Fix:** Either:
- Add clarifying title: "📈 Battery SoC Timeline (Theoretical Model)"
- Replace with actual battery SoC metric if available
- Add description: "Simulated discharge curves based on current load"

---

## Implementation Checklist

- [ ] Fix Panel 402 cumulative energy calculation
- [ ] Fix Panel 603 ROI formula (add cost conversion)
- [ ] Fix Panel 702 capacity factor (clarify or invert)
- [ ] Remove `range: true` from Panel 101
- [ ] Add clamp_min() to Panel 807
- [ ] Update Panel 808 title to indicate simulation
- [ ] Fix Panel 403 load duration curve
- [ ] Test all changes with real device data
- [ ] Update dashboard version number

---

## Validation Tests

After fixes, verify:
1. Panel 402 shows increasing energy values over time
2. Panel 603 shows realistic payback period (1-10 years typically)
3. Panel 702 shows meaningful value with correct units
4. Panel 807 never shows negative or extremely large values
5. All panels respond correctly to device filter changes

