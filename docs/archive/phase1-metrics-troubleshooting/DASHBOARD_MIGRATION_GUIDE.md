# Dashboard Migration Guide

**Related**: `docs/BUG.md`, `docs/METRIC_STRUCTURE_REDESIGN.md`

**Objective**: Update dashboard queries to handle the current broken state and prepare for Option 1 fix (removing `rate_class` label from `consumption_cost`)

---

## Current Problem

All queries using `sum(consumption_cost)` are returning **3x the actual value** because they're summing all three rate_class label combinations (on_peak, off_peak, super_off_peak) that persist in the Prometheus registry.

---

## Affected Dashboards

1. **power-analytics.json** - 5 queries affected
2. **load-shift-savings.json** - 10 queries affected

---

## Migration Strategy

### Phase 1: Immediate Workaround (Current Broken State)

Apply these fixes to dashboards **NOW** to get correct results despite the bug:

### Phase 2: Post-Fix Queries (After Removing rate_class Label)

After implementing Option 1, update queries to the simplified versions.

---

## Query-by-Query Migration

### 1. Total Real-time Cost

**Panel ID**: 10 (power-analytics.json)
**Panel Title**: "Total Real-time Cost"

#### Current Query (BROKEN):
```promql
sum(consumption_cost{version=~"$version"})
```
**Problem**: Returns 3x actual cost (sums all 3 rate_classes)

#### Phase 1 Workaround:
```promql
# Option A: Divide by 3 (HACK but works for now)
sum(consumption_cost{version=~"$version"}) / 3

# Option B: Only sum current rate period (requires knowing what it is)
sum(consumption_cost{version=~"$version", rate_class="on_peak"})  # Only during 16:00-21:00
sum(consumption_cost{version=~"$version", rate_class="off_peak"})  # Only during 06:00-16:00, 21:00-23:59
sum(consumption_cost{version=~"$version", rate_class="super_off_peak"})  # Only during 00:00-06:00

# Option C: Take max per device (gets highest of the 3 values)
sum(max by (alias) (consumption_cost{version=~"$version"}))
```

#### Phase 2 Final Query (After Fix):
```promql
sum(consumption_cost{version=~"$version"})
```
**Note**: After removing rate_class label, this will work correctly

---

### 2. Real-time Cost Rate by Device

**Panel ID**: 9 (power-analytics.json)
**Panel Title**: "Real-time Cost Rate by Device"

#### Current Query (BROKEN):
```promql
max by (alias) (consumption_cost{version=~"$version"})
```
**Problem**: Takes max of 3 values per device (usually returns on_peak cost even during off_peak)

#### Phase 1 Workaround:
```promql
# Best option: Calculate from power consumption directly
(max by (alias) (current_consumption{version=~"$version"}) / 1000)
*
on(alias) group_left(rate_class)
max by (alias, rate_class) (current_energy_rate{version=~"$version"})
```

#### Phase 2 Final Query (After Fix):
```promql
max by (alias) (consumption_cost{version=~"$version"})
```

---

### 3. Cost by TOU Rate Class

**Panel ID**: 14 (power-analytics.json)
**Panel Title**: "💰 Cost by TOU Rate Class"

#### Current Query (BROKEN):
```promql
sum by (rate_class) (avg_over_time(consumption_cost{version=~"$version"}[$__range]) * ($__range_s / 3600))
```
**Problem**: Shows how much was spent during each rate period, but includes stale values

#### Phase 1 Workaround:
```promql
# This query is actually OK if we accept historical interpretation
# It shows: "Total cost during periods when each rate_class was active"
# Keep as-is, but add annotation explaining the data
sum by (rate_class) (avg_over_time(consumption_cost{version=~"$version"}[$__range]) * ($__range_s / 3600))
```

#### Phase 2 Final Query (After Fix):
```promql
# After fix, need to join with current_energy_rate to get rate_class breakdown
sum by (rate_class) (
  avg_over_time(consumption_cost{version=~"$version"}[$__range])
  * on(alias) group_left(rate_class)
  current_energy_rate{version=~"$version"}
  * ($__range_s / 3600)
)
```

**Note**: This query becomes more complex after the fix. Consider if this visualization is worth keeping.

---

### 4. Instant Savings Potential (Load Shift Dashboard)

**Panel ID**: 2 (load-shift-savings.json)
**Panel Title**: "💰 Instant Savings Potential ($/hr)"

#### Current Query (BROKEN):
```promql
sum(consumption_cost{version=~"$version"}) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))
```
**Problem**: `sum(consumption_cost)` is 3x too high

#### Phase 1 Workaround:
```promql
# Divide consumption_cost by 3
(sum(consumption_cost{version=~"$version"}) / 3) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))

# OR calculate current cost from scratch
((sum(current_consumption{version=~"$version"}) / 1000) * max(current_energy_rate{version=~"$version"}))
-
(sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))
```

#### Phase 2 Final Query (After Fix):
```promql
sum(consumption_cost{version=~"$version"}) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))
```

---

### 5. Savings Percentage Gauge

**Panel ID**: 3 (load-shift-savings.json)
**Panel Title**: "📊 Savings Percentage"

#### Current Query (BROKEN):
```promql
((sum(consumption_cost{version=~"$version"}) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))) / sum(consumption_cost{version=~"$version"})) * 100
```

#### Phase 1 Workaround:
```promql
((sum(consumption_cost{version=~"$version"}) / 3 - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))) / (sum(consumption_cost{version=~"$version"}) / 3)) * 100
```

#### Phase 2 Final Query (After Fix):
```promql
((sum(consumption_cost{version=~"$version"}) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))) / sum(consumption_cost{version=~"$version"})) * 100
```

---

### 6. Current Cost (Load Shift Dashboard)

**Panel ID**: 4 (load-shift-savings.json)
**Panel Title**: "Current Cost ($/hr)"

#### Current Query (BROKEN):
```promql
sum(consumption_cost{version=~"$version"})
```

#### Phase 1 Workaround:
```promql
sum(consumption_cost{version=~"$version"}) / 3
```

#### Phase 2 Final Query (After Fix):
```promql
sum(consumption_cost{version=~"$version"})
```

---

### 7. Projected Savings (Daily/Monthly/Yearly)

**Panel ID**: 6 (load-shift-savings.json)
**Panel Title**: "📅 Projected Savings (Current Rate)"

#### Current Queries (BROKEN):
```promql
# Daily
(sum(consumption_cost{version=~"$version"}) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))) * 24

# Monthly
(sum(consumption_cost{version=~"$version"}) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))) * 24 * 30

# Yearly
(sum(consumption_cost{version=~"$version"}) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))) * 24 * 365
```

#### Phase 1 Workaround:
```promql
# Daily
((sum(consumption_cost{version=~"$version"}) / 3) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))) * 24

# Monthly
((sum(consumption_cost{version=~"$version"}) / 3) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))) * 24 * 30

# Yearly
((sum(consumption_cost{version=~"$version"}) / 3) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))) * 24 * 365
```

#### Phase 2 Final Query (After Fix):
Same as current broken queries (will work correctly after fix)

---

### 8. Cost Comparison Over Time

**Panel ID**: 8 (load-shift-savings.json)
**Panel Title**: "💸 Cost Comparison Over Time"

#### Current Queries (BROKEN):
```promql
# Actual Cost
sum(consumption_cost{version=~"$version"})

# Theoretical Min Cost
sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"})

# Potential Savings
sum(consumption_cost{version=~"$version"}) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))
```

#### Phase 1 Workaround:
```promql
# Actual Cost
sum(consumption_cost{version=~"$version"}) / 3

# Theoretical Min Cost (unchanged)
sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"})

# Potential Savings
(sum(consumption_cost{version=~"$version"}) / 3) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))
```

#### Phase 2 Final Query (After Fix):
Same as current broken queries

---

### 9. Energy/Cost by Rate Class (Pie Charts)

**Panel IDs**: 10, 11 (load-shift-savings.json)
**Panel Titles**: "⚡ Energy by Rate Class", "💰 Cost by Rate Class"

#### Current Query (BROKEN):
```promql
sum by (rate_class) (avg_over_time(consumption_cost{version=~"$version"}[$__range]) * ($__range_s / 3600))
```

#### Phase 1 Workaround:
```promql
# Keep as-is - shows historical breakdown of when each rate was active
# Add annotation: "Shows cost during periods when each rate class was active"
sum by (rate_class) (avg_over_time(consumption_cost{version=~"$version"}[$__range]) * ($__range_s / 3600))
```

#### Phase 2 Final Query (After Fix):
```promql
# Will need to recalculate from power consumption
sum by (rate_class) (
  avg_over_time(current_consumption{version=~"$version"}[$__range])
  / 1000
  * on() group_left(rate_class)
  current_energy_rate{version=~"$version"}
  * ($__range_s / 3600)
)
```

**Note**: This is complex. Consider removing these pie charts or redesigning.

---

### 10. Savings Opportunity by Device

**Panel ID**: 14 (load-shift-savings.json)
**Panel Title**: "🔌 Savings Opportunity by Device"

#### Current Query (BROKEN):
```promql
max by (alias) (consumption_cost{version=~"$version"}) - (max by (alias) (current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))
```
**Problem**: `max by (alias)` takes the highest of 3 values (often on_peak even during off_peak)

#### Phase 1 Workaround:
```promql
# Calculate current cost from power consumption
(max by (alias) (current_consumption{version=~"$version"}) / 1000 * max(current_energy_rate{version=~"$version"}))
-
(max by (alias) (current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))
```

#### Phase 2 Final Query (After Fix):
```promql
max by (alias) (consumption_cost{version=~"$version"}) - (max by (alias) (current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"}))
```

---

### 11. Total Missed Savings (Time Range)

**Panel ID**: 15 (load-shift-savings.json)
**Panel Title**: "💸 Total Missed Savings (Time Range)"

#### Current Query (BROKEN):
```promql
sum_over_time((sum(consumption_cost{version=~"$version"}) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"})))[$__range:]) * ($__range_s / 3600)
```

#### Phase 1 Workaround:
```promql
sum_over_time(((sum(consumption_cost{version=~"$version"}) / 3) - (sum(current_consumption{version=~"$version"}) / 1000 * min(current_energy_rate{rate_class="super_off_peak"})))[$__range:]) * ($__range_s / 3600)
```

#### Phase 2 Final Query (After Fix):
Same as current broken query

---

## Summary of Changes

### Phase 1 Workaround (Apply NOW)

| Query Pattern | Fix | Count |
|--------------|-----|-------|
| `sum(consumption_cost)` | Divide by 3: `sum(consumption_cost) / 3` | 8 queries |
| `max by (alias) (consumption_cost)` | Calculate from power: see query #2 | 2 queries |
| `sum by (rate_class) (consumption_cost)` | Keep as-is (historical interpretation) | 2 queries |

**Total Queries to Update**: 10 out of 15

### Phase 2 Post-Fix (After removing rate_class label)

Most queries revert to their original form. Only complex queries (pie charts by rate_class) need redesign.

---

## Implementation Checklist

### Immediate (Phase 1):
- [ ] Backup current dashboards
  ```bash
  cp etc/grafana/dashboards/power-analytics.json etc/grafana/dashboards/power-analytics.json.pre-fix
  cp etc/grafana/dashboards/load-shift-savings.json etc/grafana/dashboards/load-shift-savings.json.pre-fix
  ```

- [ ] Apply workarounds to power-analytics.json (3 queries)
- [ ] Apply workarounds to load-shift-savings.json (7 queries)
- [ ] Restart Grafana to reload dashboards
- [ ] Verify panels show correct values

### Post-Fix (Phase 2):
- [ ] Implement Option 1 (remove rate_class label from consumption_cost)
- [ ] Restart kasa-exporter
- [ ] Revert most queries to original form
- [ ] Redesign or remove rate_class pie charts
- [ ] Test all panels
- [ ] Document final query patterns

---

## Testing Validation

After applying fixes, verify:

```bash
# 1. Current total cost should be reasonable (~$0.12-0.38/hour)
curl -s 'http://localhost:9090/api/v1/query?query=sum(consumption_cost)/3' | jq '.data.result[0].value[1]'

# 2. Savings calculation should show positive value
curl -s 'http://localhost:9090/api/v1/query?query=(sum(consumption_cost)/3)-(sum(current_consumption)/1000*min(current_energy_rate{rate_class="super_off_peak"}))' | jq '.data.result[0].value[1]'

# 3. After fix, verify only 6 time series exist
curl -s 'http://localhost:9090/api/v1/query?query=count(consumption_cost)' | jq '.data.result[0].value[1]'
# Should return: 6 (not 18)
```

---

## Notes

- **Phase 1** is a temporary workaround - dashboards will show correct data but queries are hacky
- **Phase 2** is the proper fix - cleaner queries, better performance, no cardinality issues
- Consider adding panel annotations explaining the metrics during transition
- Monitor Prometheus memory usage after fix (should decrease with fewer time series)
