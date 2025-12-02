# Grafana Dashboard Browser Testing

**Date**: 2025-11-03
**Testing Environment**: http://localhost:3000
**Grafana Version**: v12.2.1 (563109b696)
**Credentials**: admin:turbopookipanda

## Testing Plan

Testing the following dashboards:
1. 1-real-time-monitoring.json
2. 2-tou-cost-optimization.json
3. 3-battery-sizing.json
4. 4-forecasting-analytics.json
5. 5-comparative-analytics.json
6. 6-alerts-monitoring.json

## Session Notes

### Initial Login
- ✅ Successfully logged into Grafana at http://localhost:3000
- Currently on home page, need to navigate to dashboards

---

## Dashboard Testing Results

### Dashboard 1: 🌊 Real-Time Monitoring
**URL**: http://localhost:3000/d/kasa-realtime-v2/f09f8c8a-real-time-monitoring
**Status**: ⚠️ Mostly working with several issues

#### Graph Analysis:

**⚡ System Overview - Stat Panels (4 panels):**
1. ✅ **Total Power Draw** (237 W) - Clean sparkline background, value looks correct
2. ✅ **Current Cost Rate** ($0.0833/hr) - Clean sparkline background, reasonable value
3. ✅ **Energy Rate** - Shows "Off-Peak" correctly with rate class and season labels visible
4. ✅ **Projected Daily Cost** ($2.00) - Clean sparkline background, reasonable projection

**🌊 Power Consumption Over Time - Time Series Graph:**
- ✅ Graph rendering properly with smooth colored lines
- ✅ Shows all active devices with different colors in stacked area format
- ✅ Stacked area chart working correctly, can see individual device contributions
- ✅ Legend table showing Mean, Max, Last values - all populated correctly
- ⚠️ **MINOR**: "None" device showing 0W (appears to be offline/unplugged - expected)
- ⚠️ **MINOR**: "Smart Plug" showing 0W (appears to be offline/unplugged - expected)

**🥧 Power Distribution - Pie Chart:**
- ⚠️ **CRITICAL BUG**: Shows "698536%" as the top label in the pie chart - This is clearly a calculation error
- ✅ Chart visual proportions look reasonable (shows proper slices)
- ✅ Legend table shows correct wattage values per device
- ❌ The percentage label calculation is completely broken - should show percentages, not 698536%

**💵 Cost Rate History ($/hr by Device) - Stacked Area Time Series:**
- ✅ Graph rendering properly with stacked colored areas
- ✅ Shows cost rates changing over time (visible spikes during on-peak hours around 14:20-14:30)
- ✅ Legend table with Mean, Max, Last values all working correctly
- ✅ Reasonable cost values per device ($0.03 for 6985, $0.02 for Dream Machine, etc.)
- ✅ Tooltip and hover functionality appears to be working

**📈 Projected Costs (Hour/Day/Month) - Time Series + Table:**
- ✅ Graph shows three lines (Hourly, Daily, Monthly) over time
- ✅ Stacked area visualization working
- ✅ Values look reasonable: $0.08/hr, $1.94/day, $59/month
- ✅ Mean, Max, Last columns all populated correctly
- ✅ Shows cost spikes during on-peak periods (visible around 14:20-14:30)

**📊 Device Status Table - Table Panel:**
- ❌ **CRITICAL BUG**: Most columns are completely empty!
  - ✅ Device name column populated
  - ✅ Power (W) column populated
  - ✅ State column shows green bars (but no text values visible)
  - ❌ Cost ($/hr) column - EMPTY (should show cost per device)
  - ❌ Energy Today (kWh) column - EMPTY
  - ❌ Energy Month (kWh) column - EMPTY
  - ❌ Uptime column - EMPTY
  - ❌ RSSI column - EMPTY (signal strength)
- ⚠️ **DATA ISSUE**: Shows "None" and "Smart Plug" with "OFF" status at bottom
- ❌ Query is not properly returning all the metrics, or panel field mapping is incorrect

**Console Errors:**
- ⚠️ 404 error loading a resource (likely a font or image file)

#### Summary of Issues for Dashboard 1:
1. 🔴 **HIGH PRIORITY**: Pie chart percentage calculation showing "698536%" instead of proper percentages
2. 🔴 **HIGH PRIORITY**: Device Status Table missing 6 out of 8 columns (Cost, Energy Today, Energy Month, Uptime, RSSI, State text)
3. 🟡 **LOW PRIORITY**: "None" and "Smart Plug" devices offline (0W) - likely intentional/unplugged

### Dashboard 2: ⚡ TOU Cost Optimization
**URL**: http://localhost:3000/d/kasa-tou-opt-v2/e29aa1-tou-cost-optimization
**Status**: 🔴 CRITICAL - Most panels showing "No data"

#### Graph Analysis:

**🌟 Current Rate Class Section:**
1. ⚠️ **Current Rate Class** - Shows two duplicate values "0.351" and "0.351" (should show rate class name like "Off-Peak")
2. ❌ **Current Rate ($/kWh)** - **NO DATA** (should show current rate)
3. ❌ **Rate Class Timeline** - **NO DATA** (should show timeline of rate classes over 24h)

**💰 Cost Breakdown Section:**
1. ⚠️ **Cost by Rate Class (Pie Chart)** -
   - Shows $4.95K for On-Peak (93%) and $361 for Off-Peak (7%)
   - ⚠️ **ISSUE**: Values seem unrealistically high ($4,950 for 24 hours?!)
   - ⚠️ **ISSUE**: Pie chart shows "698538%" label again (same bug as Dashboard 1)
   - ⚠️ Should be showing dollars, not thousands of dollars
2. ✅ **Cost Distribution Table** - Shows $6.27 total (this looks more realistic!)
3. ✅ **Hourly Cost Trends by Rate Class** - Graph showing Off-Peak $75.2 and On-Peak $252
   - ⚠️ **INCONSISTENCY**: Graph totals ($327) don't match pie chart ($5,311) or table ($6.27)

**💸 Savings Opportunities Section:**
1. ❌ **Potential Savings - Super Off-Peak** - **NO DATA**
2. ❌ **Potential Savings - Off-Peak** - **NO DATA**
3. ❌ **Savings Over Time** - **NO DATA**

**⚡ Load Shift Analysis Section:**
1. ❌ **Power by Rate Class** - **NO DATA** (shows panel status error icon)
2. ❌ **Optimal Usage Recommendations** - **NO DATA**
3. ❌ **Super Off-Peak Utilization** - **NO DATA**

**💡 What-If Scenarios Section:**
1. ❌ **What-If: All Super Off-Peak ($0.314/kWh)** - **NO DATA**
2. ❌ **What-If: All Off-Peak ($0.351/kWh)** - **NO DATA**
3. ❌ **What-If: All On-Peak ($0.634/kWh)** - **NO DATA**
4. ❌ **Scenario Comparison - Monthly Cost Projection** - **NO DATA**

**🎯 Optimization Insights Section:**
1. ❌ **Key Optimization Metrics Table** - Empty table with headers but no data rows
2. ⚠️ **Current Power Distribution by Device (Pie Chart)** -
   - Shows duplicate entries for each device (e.g., "6985" appears twice with different values)
   - ⚠️ **ISSUE**: Pie chart shows "69858" prefix on labels (same calculation bug)
   - ⚠️ Should aggregate by device, not show multiple entries per device

**Console Errors:**
- ⚠️ 404 error loading a resource
- ❌ **400 Bad Request** - Query error! This explains the "No data" panels

#### Summary of Issues for Dashboard 2:
1. 🔴 **CRITICAL**: ~70% of panels showing "No data" (15+ panels affected)
2. 🔴 **CRITICAL**: 400 Bad Request error in console - queries are broken
3. 🔴 **HIGH**: Data inconsistency - Cost by Rate Class shows $5.3K but table shows $6.27
4. 🔴 **HIGH**: Cost by Rate Class pie chart showing unrealistic values ($4,950 for 24h)
5. 🔴 **HIGH**: Pie charts showing broken percentage labels (698538%, 69858)
6. 🟡 **MEDIUM**: Current Rate Class showing numeric value instead of rate class name
7. 🟡 **MEDIUM**: Power Distribution showing duplicate device entries instead of aggregating
8. 🟡 **MEDIUM**: What-If scenarios all broken (no data)
9. 🟡 **MEDIUM**: Savings calculations all broken (no data)

### Dashboard 3: 🔋 Battery Sizing & Analysis
**URL**: http://localhost:3000/d/kasa-battery-v2/f09f948b-battery-sizing-and-analysis
**Status**: ✅ Mostly working with minor issues

#### Graph Analysis:

**⚡ Current Load Profile Section:**
1. ✅ **Total Load** - 232 W (with sparkline)
2. ✅ **Average Load (1h)** - 223 W (with sparkline)
3. ✅ **Peak Load (24h)** - 384 W (with sparkline)
4. ✅ **Min Load (24h)** - 115 W (with sparkline)

**⏱️ Battery Runtime Calculations Section:**
1. ✅ **Runtime @ Current Load** - 1.24 days (with sparkline)
2. ✅ **Runtime @ Average Load** - 1.25 days (with sparkline)
3. ✅ **Runtime @ Peak Load** - 18.0 hour (with sparkline)
4. ✅ **Recommended Capacity** - Shows three bars: No Backup (88.8 Ah), 12h Backup (133 Ah), 24h Backup (266 Ah)

**📊 Battery Comparison Matrix Section:**
1. ✅ **Runtime Comparison Table** - Shows time series data with multiple battery configurations (12V @ 100Ah, 12V @ 200Ah, etc.)
2. ✅ **Capacity Heatmap** - Red heatmap showing data patterns

**Additional Calculated Panels (bottom section):**
1. ✅ **Load Factor** - 48.9%
2. ⚠️ **Capacity Factor** - 3725% (seems unrealistically high - likely a calculation error)
3. ✅ **Autonomy Time @ Current Settings** - 1.21 days (shows formula)
4. ✅ **Solar Charge Rate** - 360 W (shows formula: 400 * 0.90)
5. ✅ **Time to Full Charge** - 1.11 days
6. ✅ **Time to Usable (0% → 80%)** - 21.3 hour
7. ✅ **Net Energy Balance** - 128 W
8. ✅ **Daily Solar Production** - 2 kWh (5 sun hours)
9. ✅ **Daily Load Coverage %** - 35.9%
10. ✅ **Runtime with Solar Recharge** - 5.54 days
11. ✅ **Days of Autonomy (No Sun)** - 1.24 days
12. ⚠️ **Battery State of Charge Timeline** - Graph shows data but has warning icon (panel status error)
    - Shows "Battery Discharge (Load Only)" - 49.8% mean, 18.8% min, 67.1% max
    - Shows "Net Battery State" - 100% constant (unrealistic - should vary)
13. ✅ **Recommended Solar Panel Sizes Table** - Shows multiple rows with Current Load and coverage percentages (100%, 150%, 200%)

**Interactive Controls:**
- ✅ All variable dropdowns working (Version, Device, Battery Voltage, Battery Capacity, Depth of Discharge, Inverter Efficiency, Solar Panel Wattage)

**Console Errors:**
- ⚠️ 404 error loading a resource
- ❌ **Two 400 Bad Request errors** - Some queries are failing

#### Summary of Issues for Dashboard 3:
1. 🟡 **MEDIUM**: Capacity Factor showing 3725% (unrealistic - should be < 100%)
2. 🟡 **MEDIUM**: Battery State of Charge Timeline has error icon (400 Bad Request)
3. 🟡 **MEDIUM**: Net Battery State showing constant 100% (unrealistic - should vary based on usage)
4. 🟢 **MINOR**: Two 400 Bad Request errors in console (affecting specific panels)
5. ✅ **Overall**: Most calculations and visualizations working correctly

### Dashboard 4: 🔮 Forecasting & Predictions
**URL**: http://localhost:3000/d/kasa-forecast-v2/f09f94ae-forecasting-and-predictions
**Status**: 🔴 CRITICAL - Most panels showing "No data"

#### Graph Analysis:

**💰 COST PROJECTIONS Section:**
1. ❌ **Projected Monthly Cost** - **NO DATA**
2. ✅ **Month Progress** - 9.86% (working)
3. ❌ **Budget Status (vs $100)** - **NO DATA**
4. ❌ **Cost Trend (24h with Prediction)** - **NO DATA**

**📈 TREND ANALYSIS Section:**
1. ❌ **Power Consumption Trend** - **NO DATA**
2. ❌ **Cost Rate Trend** - **NO DATA**
3. ❌ **Week-over-Week Comparison** - **NO DATA**
4. ❌ **Month-over-Month Comparison** - **NO DATA**

**🚨 ANOMALY DETECTION Section:**
1. ❌ **Anomaly Indicator** - **NO DATA**
2. ✅ **Z-Score (Anomaly Detection)** - Shows values (working)
3. ✅ **Standard Deviation** - Shows values (working)
4. ✅ **Outlier Detection (2σ Bounds)** - Shows values (working)

**Console Errors:**
- ⚠️ 404 error loading a resource

#### Summary of Issues for Dashboard 4:
1. 🔴 **CRITICAL**: ~70% of panels showing "No data" (8 out of 11 panels affected)
2. 🔴 **CRITICAL**: All forecasting/prediction queries appear to be broken
3. 🔴 **CRITICAL**: All trend analysis panels broken
4. ✅ Only 3 panels working: Month Progress, Z-Score, Standard Deviation, Outlier Detection

### Dashboard 5: 📊 Comparative Analytics
**URL**: http://localhost:3000/d/kasa-compare-v2/f09f938a-comparative-analytics
**Status**: 🔴 CRITICAL - Most panels showing "No data"

#### Graph Analysis:

**👑 Device Rankings Section:**
1. ❌ **Highest Power Consumer** - **NO DATA**
2. ❌ **Most Expensive Device** - **NO DATA**
3. ✅ **Most Efficient** - Shows efficiency ratings ($/W) for all devices (0.35 range)
4. ❌ **Device Count** - **NO DATA**

**📊 Power Comparison Section:**
1. ❌ **Power by Device** - **NO DATA**
2. ❌ **Power Share %** - **NO DATA**
3. ❌ **Power Comparison Timeline** - **NO DATA**
4. ⚠️ **Power Ranking Table** - Empty table (headers only, no data rows)

**💰 Cost Comparison Section:**
1. ❌ **Cost by Device** - **NO DATA**
2. ❌ **Cost Share %** - **NO DATA**
3. ❌ **Cost Comparison Timeline** - **NO DATA**

**Console Errors:**
- ⚠️ 404 error loading a resource

#### Summary of Issues for Dashboard 5:
1. 🔴 **CRITICAL**: ~90% of panels showing "No data" (10 out of 11 panels affected)
2. 🔴 **CRITICAL**: All comparison charts broken
3. 🔴 **CRITICAL**: All ranking panels except "Most Efficient" broken
4. ✅ Only 1 panel working: Most Efficient (efficiency ratings)

### Dashboard 6: 🚨 Alerts & Thresholds
**URL**: http://localhost:3000/d/kasa-alerts-v2/f09f9aa8-alerts-and-thresholds
**Status**: ⚠️ Partially working with some issues

#### Graph Analysis:

**🚨 Alert Status Overview Section:**
1. ⚠️ **Active Alerts** - **NO DATA** (has warning icon - 400 error)
2. ✅ **Warnings** - Shows "1" warning (formula visible)
3. ✅ **System Status** - Shows "✅ ALL SYSTEMS OK"
4. ⚠️ **Last Alert Time** - **NO DATA** (has warning icon)

**💰 Cost Alerts Section:**
1. ✅ **Cost Alert Status** - Shows "✅ UNDER THRESHOLD"
2. ✅ **Cost vs Threshold** - Shows Current Cost ($0.0874) vs Alert Threshold ($1)
3. ✅ **Cost Spike Detection** - Shows value "3.94" (formula: consumption_cost:anomaly)
4. ⚠️ **Cost Threshold History** - Empty graph with disabled pagination buttons

**⚡ Power Alerts Section:**
1. ✅ **Power Alert Status** - Shows "✅ NORMAL"
2. ✅ **Power vs Threshold** - Shows Current Power (249 W, max 333 W) vs Alert Threshold (500 W)
3. ✅ **Peak Power Alert** - Shows 68.8% of threshold

**Interactive Controls:**
- ✅ Cost Alert Threshold textbox (1.0)
- ✅ Power Alert Threshold textbox (500)
- ✅ Anomaly Sensitivity dropdown (3)
- ✅ Power Spikes toggle (enabled)
- ✅ Cost Anomalies toggle (enabled)
- ✅ "Kasa Dashboards" navigation button

**Console Errors:**
- ⚠️ 404 error loading a resource
- ❌ **Two 400 Bad Request errors** - Some queries failing

#### Summary of Issues for Dashboard 6:
1. 🟡 **MEDIUM**: Active Alerts panel showing "No data" (400 Bad Request)
2. 🟡 **MEDIUM**: Last Alert Time panel showing "No data"
3. 🟡 **MEDIUM**: Cost Threshold History panel empty
4. 🟢 **MINOR**: Two 400 Bad Request errors in console
5. ✅ **Overall**: Most alert and threshold panels working correctly (~70% functional)

---

## Summary of Issues Found

### 🔴 CRITICAL Issues (Must Fix)

1. **Pie Chart Percentage Bug** (Dashboards 1, 2)
   - All pie charts showing broken percentage labels (e.g., "698536%", "69858")
   - Affects: Real-Time Monitoring (Power Distribution), TOU Cost Optimization (multiple charts)

2. **Dashboard 2: TOU Cost Optimization - 70% No Data**
   - 15+ panels showing "No data"
   - 400 Bad Request errors in console
   - Broken: Rate Class Timeline, Cost projections, Savings calculations, What-If scenarios, Load shift analysis

3. **Dashboard 4: Forecasting & Predictions - 70% No Data**
   - 8 out of 11 panels showing "No data"
   - All forecasting/prediction queries broken
   - All trend analysis panels broken

4. **Dashboard 5: Comparative Analytics - 90% No Data**
   - 10 out of 11 panels showing "No data"
   - All comparison charts broken
   - All ranking panels except "Most Efficient" broken

5. **Dashboard 1: Device Status Table Missing Columns**
   - 6 out of 8 columns empty (Cost, Energy Today, Energy Month, Uptime, RSSI, State text)
   - Only Device name and Power columns populated

6. **Data Inconsistency - Dashboard 2**
   - Cost by Rate Class shows $5.3K but table shows $6.27
   - Hourly Cost Trends shows $327 total
   - Three different values for what should be the same metric

### 🟡 MEDIUM Priority Issues

7. **Dashboard 3: Battery Capacity Factor**
   - Showing 3725% (should be < 100%)

8. **Dashboard 3: Battery State of Charge**
   - Panel has error icon (400 Bad Request)
   - Net Battery State constant at 100% (unrealistic)

9. **Dashboard 2: Current Rate Class**
   - Showing numeric value "0.351" instead of rate class name "Off-Peak"

10. **Dashboard 2: Power Distribution**
    - Showing duplicate device entries instead of aggregating

11. **Dashboard 6: Active Alerts & Last Alert Time**
    - Both panels showing "No data" (400 Bad Request errors)

12. **Dashboard 6: Cost Threshold History**
    - Empty graph with disabled pagination

### 🟢 MINOR Issues

13. **404 Errors** (All dashboards)
    - Resource not found errors (likely font or image files)

14. **Offline Devices** (Dashboards 1, 2)
    - "None" and "Smart Plug" showing 0W (likely intentional/unplugged)

---

### Dashboard Health Summary

| Dashboard | Status | Working % | Critical Issues |
|-----------|---------|-----------|-----------------|
| 1. Real-Time Monitoring | ⚠️ Mostly Working | ~85% | Pie chart %, Device Status Table |
| 2. TOU Cost Optimization | 🔴 BROKEN | ~30% | 70% panels no data, 400 errors |
| 3. Battery Sizing | ✅ Good | ~90% | Minor calculation errors |
| 4. Forecasting & Predictions | 🔴 BROKEN | ~30% | 70% panels no data |
| 5. Comparative Analytics | 🔴 BROKEN | ~10% | 90% panels no data |
| 6. Alerts & Thresholds | ⚠️ Partially Working | ~70% | Some alert panels broken |

**Overall Dashboard Suite Health: 50% Functional**

---

### Root Causes Analysis

1. **Query Errors (400 Bad Request)**
   - Multiple dashboards affected (2, 3, 4, 5, 6)
   - Likely issues with Prometheus queries or metric names
   - Need to audit PromQL queries against available metrics

2. **Pie Chart Percentage Calculation**
   - Common bug across multiple pie charts
   - Likely in dashboard generation script or Grafana panel configuration

3. **Missing/Incomplete Metrics**
   - Device Status Table missing columns
   - Suggests metrics not being exported or queries not finding data

4. **Data Aggregation Issues**
   - Duplicate entries in tables
   - Inconsistent totals across different visualizations

## Recommended Next Steps

### Immediate Actions (Critical Fixes)

1. **Fix Pie Chart Percentage Bug**
   - File: `scripts/generate_dashboards.py`
   - Check pie chart panel configurations
   - Likely issue with percentage calculation in labels/legend

2. **Audit Prometheus Queries**
   - Test failing queries directly in Prometheus
   - Check metric names and labels match what's being exported
   - Fix 400 Bad Request errors in Dashboards 2, 4, 5, 6

3. **Fix Device Status Table**
   - Dashboard 1: `kasa_exporter/routines/exporter.py:26`
   - Verify all metrics are being exported (State, Cost, Energy, Uptime, RSSI)
   - Check table panel field mappings in dashboard JSON

### High Priority (Data Quality)

4. **Fix TOU Dashboard Data Inconsistency**
   - Investigate why Cost by Rate Class, table, and graph show different totals
   - Likely aggregation or time range issues in queries

5. **Fix Missing Metrics in Dashboards 2, 4, 5**
   - Review which metrics exist vs. which are being queried
   - May need to add new recording rules or fix metric names

### Medium Priority (Polish)

6. **Fix Battery Dashboard Calculations**
   - Capacity Factor formula showing >100%
   - Battery State of Charge should vary, not stay at 100%

7. **Fix Dashboard 2 Display Issues**
   - Current Rate Class should show text name, not numeric value
   - Power Distribution showing duplicates - needs aggregation

### Testing & Validation

8. **Re-test After Fixes**
   - Use this document as a checklist
   - Verify each issue is resolved
   - Document any remaining issues

---

**Testing Completed**: 2025-11-03
**Screenshots**: See `docs/screenshots/` directory
**Total Issues Found**: 14 (6 Critical, 6 Medium, 2 Minor)
