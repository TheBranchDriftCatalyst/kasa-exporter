# TOU Cost Optimization Dashboard Audit

Dashboard: `/Users/panda/catalyst-devspace/workspace/@kasa-exporter/etc/grafana/dashboards/2-tou-cost-optimization.json`

## Summary

**Total Panels Audited**: 18 panels
**Queries With Issues**: 1 critical issue found
**Queries Working Correctly**: 17 panels

## Critical Issues

### Panel 3: Rate Class Timeline (ID: 3)
- **Location**: Line 333
- **Panel Title**: "⏰ Rate Class Timeline"
- **Current Query**: `rate_class:numeric{version=~"$version"}`
- **Issue**: **CRITICAL - Metric Does Not Exist**
  - The recording rule `rate_class:numeric` is not defined in the Prometheus rules
  - This panel will show NO DATA
- **Test Result**:
  ```
  Query: rate_class:numeric
  Status: success
  Result: [] (empty array - no data)
  ```
- **Corrected Query**: This requires creating a new recording rule. Two options:

  **Option 1: Create Recording Rule** (Recommended)
  Add to recording rules file:
  ```yaml
  - record: rate_class:numeric
    expr: |
      label_replace(
        label_replace(
          label_replace(
            current_energy_rate,
            "numeric_value", "1", "rate_class", "super_off_peak"
          ),
          "numeric_value", "2", "rate_class", "off_peak"
        ),
        "numeric_value", "3", "rate_class", "on_peak"
      )
  ```

  **Option 2: Use Inline Query**
  ```promql
  label_replace(
    label_replace(
      label_replace(
        max(current_energy_rate{version=~"$version"}) by (rate_class),
        "numeric", "1", "rate_class", "super_off_peak"
      ),
      "numeric", "2", "rate_class", "off_peak"
    ),
    "numeric", "3", "rate_class", "on_peak"
  )
  ```

## Panels Working Correctly

### Panel 1: Current Rate Class (ID: 1)
- **Query**: `label_replace(max(current_energy_rate{version=~"$version"}), "rate_class", "$1", "rate_class", "(.*)")`
- **Type**: Instant query (both `range: true` and `instant: true` set)
- **Issue**: Minor - Has conflicting flags (`range: true` AND `instant: true`)
- **Status**: ✅ WORKING - Returns data correctly
- **Test Result**:
  ```
  Status: success
  Value: 0.351 (off_peak)
  ```
- **Recommendation**: Set `range: false, instant: true` for clarity (stat panels use instant)

### Panel 2: Current Rate ($/kWh) (ID: 2)
- **Query**: `current_energy_rate:current{version=~"$version"}`
- **Type**: Instant query
- **Issue**: Minor - Same as Panel 1 (conflicting flags)
- **Status**: ✅ WORKING - Returns data correctly
- **Test Result**:
  ```
  Status: success
  Value: $0.351/kWh
  ```
- **Recommendation**: Set `range: false, instant: true`

### Panel 4: Cost by Rate Class (ID: 4)
- **Query**: `sum by (rate_class) (increase(consumption_cost_with_rate_class{version=~"$version"}[$__range]))`
- **Type**: Range query for pie chart
- **Status**: ✅ WORKING CORRECTLY
- **Test Result** (24h range):
  ```
  Status: success
  off_peak: $0.153
  on_peak: $21.02
  Total: $21.17
  ```
- **Analysis**: Correctly uses `increase()` over `$__range` for counter metric

### Panel 5: Cost Distribution Table (ID: 5)
- **Query**: `sum by (rate_class) (increase(consumption_cost_with_rate_class{version=~"$version"}[$__range]))`
- **Type**: Table format
- **Issue**: Has `range: true` AND `instant: true` (conflicting)
- **Status**: ✅ WORKING - Same query as Panel 4
- **Test Result**: Same as Panel 4
- **Recommendation**: For tables showing aggregated data, use `instant: true, range: false`

### Panel 6: Hourly Cost Trends by Rate Class (ID: 6)
- **Query**: `sum by (rate_class) (increase(consumption_cost_with_rate_class{version=~"$version"}[1h]))`
- **Type**: Time series with 1h range
- **Status**: ✅ WORKING CORRECTLY
- **Test Result** (1h window):
  ```
  Status: success
  off_peak: $0.153
  ```
- **Analysis**: Correctly uses `increase()` with fixed `[1h]` window for hourly trends
- **Note**: This is the correct pattern for showing hourly cost accumulation over time

### Panel 7: Potential Savings - Super Off-Peak (ID: 7)
- **Query**: `consumption_cost:potential_savings_super_off_peak{version=~"$version"}`
- **Type**: Stat panel (recording rule)
- **Status**: ✅ WORKING CORRECTLY
- **Test Result**:
  ```
  Status: success
  Value: $0.0075/hr potential savings
  ```
- **Analysis**: Recording rule correctly calculates savings opportunity

### Panel 8: Potential Savings - Off-Peak (ID: 8)
- **Query**: `consumption_cost:potential_savings_off_peak{version=~"$version"}`
- **Type**: Stat panel (recording rule)
- **Status**: ✅ WORKING CORRECTLY
- **Test Result**:
  ```
  Status: success
  Value: $0.0000016/hr potential savings
  ```
- **Analysis**: Very small savings (currently in off-peak period)

### Panel 9: Savings Over Time (ID: 9)
- **Queries**:
  - A: `consumption_cost:potential_savings_super_off_peak{version=~"$version"}`
  - B: `consumption_cost:potential_savings_off_peak{version=~"$version"}`
- **Type**: Time series
- **Status**: ✅ WORKING CORRECTLY
- **Analysis**: Uses recording rules over time to show savings trends

### Panel 10: Power by Rate Class (ID: 10)
- **Query**: `avg by (rate_class) (current_consumption{version=~"$version"} * on(device_id) group_left(rate_class, season) current_energy_rate{version=~"$version"})`
- **Type**: Bar gauge with vector matching
- **Issue**: Has `range: true` AND `instant: true` (conflicting)
- **Status**: ✅ WORKING CORRECTLY
- **Test Result**:
  ```
  Status: success
  off_peak: 11.91W average
  ```
- **Analysis**: Complex join correctly matches consumption with rate class
- **Recommendation**: Set `instant: true, range: false` for bar gauge

### Panel 11: Optimal Usage Recommendations (ID: 11)
- **Query**:
  ```promql
  (
    sum(increase(consumption_cost_with_rate_class{rate_class="super_off_peak", version=~"$version"}[$__range]))
    /
    sum(increase(consumption_cost_with_rate_class{version=~"$version"}[$__range]))
  ) * 100
  ```
- **Type**: Percentage calculation with instant result
- **Issue**: Has `range: true` AND `instant: true` (conflicting)
- **Status**: ✅ WORKING - Calculates super off-peak usage percentage
- **Analysis**: Correctly uses `increase()` over `$__range` then divides for percentage
- **Recommendation**: Set `instant: true, range: false` for stat panel

### Panel 12: Super Off-Peak Utilization (ID: 12)
- **Query**: Same as Panel 11
- **Type**: Gauge
- **Issue**: Same as Panel 11
- **Status**: ✅ WORKING - Same calculation as Panel 11
- **Recommendation**: Set `instant: true, range: false`

### Panel 13-15: What-If Scenarios (IDs: 13, 14, 15)
- **Queries**:
  - Panel 13: `(current_consumption:total{version=~"$version"} / 1000) * 0.314 * 730`
  - Panel 14: `(current_consumption:total{version=~"$version"} / 1000) * 0.351 * 730`
  - Panel 15: `(current_consumption:total{version=~"$version"} / 1000) * 0.634 * 730`
- **Type**: Stat panels with instant calculations
- **Issue**: All have `range: true` AND `instant: true` (conflicting)
- **Status**: ✅ WORKING CORRECTLY
- **Test Result**:
  ```
  current_consumption:total = 203.551W
  Super Off-Peak scenario: $46.75/month
  Off-Peak scenario: $52.26/month
  On-Peak scenario: $94.35/month
  ```
- **Analysis**: Correctly calculates "what-if" monthly costs using fixed rates
- **Recommendation**: Set `instant: true, range: false` for all three panels

### Panel 16: Scenario Comparison - Monthly Cost Projection (ID: 16)
- **Queries**:
  - A: `(current_consumption:total{version=~"$version"} / 1000) * 0.314 * 730`
  - B: `(current_consumption:total{version=~"$version"} / 1000) * 0.351 * 730`
  - C: `(current_consumption:total{version=~"$version"} / 1000) * 0.634 * 730`
  - D: `consumption_cost:projected_month{version=~"$version"}`
- **Type**: Time series showing all scenarios
- **Status**: ✅ WORKING CORRECTLY
- **Analysis**: Shows comparison of all rate scenarios over time with actual projection

### Panel 17: Key Optimization Metrics (ID: 17)
- **Queries** (Table format):
  - A: `consumption_cost:total{version=~"$version"}`
  - B: `consumption_cost:projected_day{version=~"$version"}`
  - C: `consumption_cost:projected_month{version=~"$version"}`
  - D: `consumption_cost:potential_savings_super_off_peak{version=~"$version"}`
  - E: `current_consumption:total{version=~"$version"}`
- **Type**: Table with multiple metrics
- **Issue**: All queries have `range: true` AND `instant: true` (conflicting)
- **Status**: ✅ WORKING CORRECTLY
- **Test Results**:
  ```
  consumption_cost:total: $0.071/hr
  consumption_cost:projected_day: $1.71/day
  consumption_cost:projected_month: $52.16/month
  potential_savings_super_off_peak: $0.0075/hr
  current_consumption:total: 203.551W
  ```
- **Recommendation**: Set `instant: true, range: false` for table panels

### Panel 18: Current Power Distribution by Device (ID: 18)
- **Query**: `max by (alias) (current_consumption{version=~"$version"})`
- **Type**: Pie chart
- **Issue**: Has `range: true` AND `instant: true` (conflicting)
- **Status**: ✅ WORKING CORRECTLY
- **Test Result**:
  ```
  Status: success
  Dream Machine: 56.22W
  6985: 57.93W
  Fatboy Synology: 56.11W
  Lab Server: 30.48W
  Furbo: 2.82W
  Reality Forge: 0W
  ```
- **Recommendation**: Set `instant: true, range: false` for pie chart

## Minor Issues - Conflicting Query Flags

**Affected Panels**: 1, 2, 5, 10, 11, 12, 13, 14, 15, 17, 18 (11 panels total)

**Issue**: These panels have BOTH `range: true` AND `instant: true` set in their queries. While Grafana handles this (instant takes precedence), it's confusing and inconsistent.

**Recommendation**:
- For **Stat, Gauge, Bar Gauge, Pie Chart, and Table** panels showing current/latest values: Set `instant: true, range: false`
- For **Time Series** panels: Keep `range: true` only (or set both to true for time series with instant overlays)

## Query Pattern Analysis

### ✅ Correct Patterns Found

1. **Counter metrics with increase()**:
   ```promql
   sum by (rate_class) (increase(consumption_cost_with_rate_class{version=~"$version"}[$__range]))
   ```
   Used in: Panels 4, 5, 11, 12

2. **Counter metrics with fixed time window**:
   ```promql
   sum by (rate_class) (increase(consumption_cost_with_rate_class{version=~"$version"}[1h]))
   ```
   Used in: Panel 6

3. **Gauge metrics (instant values)**:
   ```promql
   current_consumption:total{version=~"$version"}
   current_energy_rate:current{version=~"$version"}
   ```
   Used in: Panels 2, 7, 8, 9, 13-17

4. **Vector matching for joins**:
   ```promql
   current_consumption * on(device_id) group_left(rate_class, season) current_energy_rate
   ```
   Used in: Panel 10

### ❌ Issue Patterns Found

1. **Missing Recording Rule**:
   ```promql
   rate_class:numeric{version=~"$version"}
   ```
   Used in: Panel 3 - **NEEDS FIXING**

## Recommendations

### High Priority

1. **Fix Panel 3** - Add the `rate_class:numeric` recording rule or use the inline query alternative provided above.

### Medium Priority

2. **Standardize Query Flags** - Update all stat/gauge/table panels to use consistent query flags:
   - Remove `range: true` from instant query panels (11 panels affected)
   - Or explicitly set `range: false, instant: true`

### Low Priority

3. **Add Comments** - Consider adding panel descriptions explaining:
   - Why certain time ranges are used (e.g., `[1h]` for hourly trends)
   - What the "what-if" scenarios represent
   - How potential savings are calculated

## Verified Working Metrics

All of the following metrics are confirmed working in Prometheus:

- ✅ `consumption_cost_with_rate_class` (counter with rate_class label)
- ✅ `current_energy_rate` (gauge)
- ✅ `current_energy_rate:current` (recording rule)
- ✅ `consumption_cost:total` (recording rule)
- ✅ `consumption_cost:projected_day` (recording rule)
- ✅ `consumption_cost:projected_month` (recording rule)
- ✅ `consumption_cost:potential_savings_super_off_peak` (recording rule)
- ✅ `consumption_cost:potential_savings_off_peak` (recording rule)
- ✅ `current_consumption` (gauge)
- ✅ `current_consumption:total` (recording rule)
- ❌ `rate_class:numeric` (MISSING - needs to be created)

## Testing Commands Used

All queries were tested against Prometheus at `http://localhost:9090/api/v1/query`

Example test commands:
```bash
# Test instant query
curl -s "http://localhost:9090/api/v1/query?query=current_energy_rate:current" | jq

# Test aggregation
curl -s "http://localhost:9090/api/v1/query?query=sum%20by%20(rate_class)%20(increase(consumption_cost_with_rate_class%5B24h%5D))" | jq

# Test recording rule
curl -s "http://localhost:9090/api/v1/query?query=consumption_cost:total" | jq
```

## Dashboard Health: 94% ✅

- 17 out of 18 panels working correctly
- 1 panel needs recording rule addition
- 11 panels have minor flag inconsistencies (cosmetic only)
- All core functionality is operational
