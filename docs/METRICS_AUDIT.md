# Metrics Audit - Actual vs Dashboard Queries

**Date**: 2025-11-02
**Purpose**: Audit all dashboard queries against actual available metrics

---

## ✅ Available Metrics (Complete List)

### Raw Metrics from Kasa Exporter

**Power & Energy**:
- `current_consumption` - Current power draw (watts)
- `consumption_today` - Energy consumed today (Wh)
- `consumption_this_month` - Energy consumed this month (Wh)

**Cost**:
- `consumption_cost` - Current cost rate ($/hour)
- `current_energy_rate` - Current TOU rate ($/kWh) with labels: season, rate_class

**Device State**:
- `state` - Device on/off state (enum: on, off)
- `on_since` - Hours since device turned on
- `led` - LED status
- `cloud_connection` - Cloud connection status (enum: connected, disconnected)

**WiFi**:
- `rssi` - WiFi signal strength (dBm)
- `signal_level` - WiFi signal level (0-4)
- `ssid_info` - SSID information metric

**Firmware**:
- `current_firmware_version_info` - Current firmware version (info metric)
- `available_firmware_version_info` - Available firmware version (info metric)
- `update_available` - Update available flag (enum: yes, no)
- `auto_update_enabled` - Auto-update status

**Auto-off**:
- `auto_off_enabled` - Auto-off feature status
- `auto_off_minutes` - Auto-off delay in minutes
- `auto_off_at_info` - Auto-off timestamp info metric

**Exporter Metrics**:
- `device_registry_total_devices` - Total devices in registry
- `device_registry_discovered_devices_total` - Counter of discovered devices
- `device_registry_pruned_devices_total` - Counter of pruned devices
- `update_attempts_total` - Counter of device update attempts
- `scrape_duration_seconds` - Scrape duration
- `up` - Target up status

### Recording Rules (Pre-computed)

**Cost Aggregations**:
- `consumption_cost:total` - Total system cost
- `consumption_cost:by_device` - Cost per device
- `consumption_cost:by_rate_class` - Cost by TOU period
- `consumption_cost:by_device_and_rate_class` - Cost by device and TOU period
- `consumption_cost_with_rate_class` - Cost with rate_class label joined

**Power Aggregations**:
- `current_consumption:total` - Total system power
- `current_consumption:by_device` - Power per device

**Time-Based Averages**:
- `consumption_cost:avg_5m` - 5-minute average cost
- `consumption_cost:avg_1h` - 1-hour average cost
- `consumption_cost:avg_24h` - 24-hour average cost
- `current_consumption:avg_5m` - 5-minute average power
- `current_consumption:avg_1h` - 1-hour average power

**Projections**:
- `consumption_cost:projected_hour` - Hourly cost projection
- `consumption_cost:projected_day` - Daily cost projection
- `consumption_cost:projected_month` - Monthly cost projection

**Savings**:
- `consumption_cost:potential_savings_super_off_peak` - Savings at $0.314/kWh
- `consumption_cost:potential_savings_off_peak` - Savings at $0.351/kWh

**Efficiency**:
- `cost_efficiency:by_device` - $/W per device
- `power_utilization:by_device` - % of total power per device

**Anomaly Detection**:
- `consumption_cost:zscore` - Statistical z-score
- `consumption_cost:stddev_1h` - 1-hour standard deviation
- `consumption_cost:anomaly` - Boolean anomaly indicator

**TOU Metrics**:
- `current_energy_rate:current` - Current $/kWh rate
- `rate_class:numeric` - TOU period as number (1=super_off_peak, 2=off_peak, 3=on_peak)

### Common Labels

All device metrics include:
- `alias` - Device friendly name
- `device_id` - Unique device ID
- `model` - Device model (e.g., "KP125M")
- `version` - Exporter version
- `env` - Environment (development/production)
- `instance` - Exporter instance
- `job` - Prometheus job name

TOU metrics include additional labels:
- `season` - TOU season (summer/winter)
- `rate_class` - TOU period (super_off_peak, off_peak, on_peak)

---

## ❌ Metrics Used in Dashboards That DON'T EXIST

### Dashboard: 3-battery-sizing.json

**Non-existent metrics**:
- `device_state` → Should be `state`
- `energy_usage_today` → Should be `consumption_today`
- `energy_usage_month` → Should be `consumption_this_month`
- `device_uptime` → Should be `on_since`
- `device_rssi` → Should be `rssi`

### Dashboard: 1-real-time-monitoring.json

**Non-existent metrics**:
- Same issues as battery sizing dashboard

### All Dashboards

**Common issues**:
- Using `device_state` instead of `state`
- Using `energy_usage_*` instead of `consumption_*`
- Using `device_rssi` instead of `rssi`
- Using `device_uptime` instead of `on_since`

---

## 🔧 Required Fixes

### 1. State Metric
```promql
# WRONG
device_state{state="on"}

# CORRECT
state{state="on"}
```

### 2. Energy Consumption
```promql
# WRONG
energy_usage_today
energy_usage_month

# CORRECT
consumption_today
consumption_this_month
```

### 3. Uptime
```promql
# WRONG
device_uptime

# CORRECT
on_since
```

### 4. WiFi Signal
```promql
# WRONG
device_rssi

# CORRECT
rssi
```

### 5. Device Selection for Battery Sizing

The `$device` variable filter needs to work with the `alias` label:

```promql
# For summing selected devices
sum(current_consumption{alias=~"$device"})

# For average over time
avg_over_time(sum(current_consumption{alias=~"$device"})[1h])

# For max over time
max_over_time(sum(current_consumption{alias=~"$device"})[24h])
```

---

## ✅ Correct Query Patterns

### Total Load (for battery sizing)
```promql
# Total load from selected devices
sum(current_consumption{alias=~"$device", version=~"$version"})

# Or using recording rule
sum(current_consumption:by_device{alias=~"$device"})
```

### Average Load (1 hour)
```promql
# Average over last hour
avg_over_time(sum(current_consumption{alias=~"$device"})[1h])

# Or simpler with recording rule
sum(current_consumption:avg_1h{alias=~"$device"})
```

### Peak Load (24 hours)
```promql
# Maximum in last 24h
max_over_time(sum(current_consumption{alias=~"$device"})[24h])
```

### Device Status Table
```promql
# State
state{state="on", version=~"$version"}

# Power
current_consumption{version=~"$version"}
# Or: current_consumption:by_device

# Cost
consumption_cost{version=~"$version"}
# Or: consumption_cost:by_device

# Energy today
consumption_today{version=~"$version"}

# Energy this month
consumption_this_month{version=~"$version"}

# Uptime
on_since{version=~"$version"}

# WiFi
rssi{version=~"$version"}
```

### Battery Runtime Calculation
```promql
# Runtime in hours
(
  $battery_voltage *
  $battery_capacity_ah *
  $depth_of_discharge *
  $inverter_efficiency
) / sum(current_consumption{alias=~"$device"})
```

---

## 📝 Dashboard Fix Checklist

### Dashboard 1: Real-Time Monitoring
- [ ] Fix device status table queries
- [ ] Update state metric name
- [ ] Update energy consumption metric names
- [ ] Update uptime and RSSI metric names

### Dashboard 2: TOU Cost Optimization
- [ ] Verify all queries use existing metrics
- [ ] Check rate_class label usage
- [ ] Validate recording rule names

### Dashboard 3: Battery Sizing
- [ ] Fix all metric names (state, consumption_today, on_since, rssi)
- [ ] Verify $device variable filtering
- [ ] Test battery runtime calculations
- [ ] Update load profile queries
- [ ] Fix energy integration queries

### Dashboard 4: Forecasting
- [ ] Verify anomaly detection metric names
- [ ] Check projection queries
- [ ] Validate time-based aggregations

### Dashboard 5: Comparative Analytics
- [ ] Check device ranking queries
- [ ] Verify efficiency calculations
- [ ] Update period comparison queries

### Dashboard 6: Alerts & Thresholds
- [ ] Fix device status queries
- [ ] Update state/connectivity checks
- [ ] Verify threshold comparisons

---

## 🎯 Priority Fixes

**High Priority** (Breaking queries):
1. Replace `device_state` → `state`
2. Replace `energy_usage_today` → `consumption_today`
3. Replace `energy_usage_month` → `consumption_this_month`
4. Replace `device_uptime` → `on_since`
5. Replace `device_rssi` → `rssi`

**Medium Priority** (Optimization):
1. Use recording rules where available
2. Simplify complex aggregations
3. Add proper label filters

**Low Priority** (Nice to have):
1. Add comments to complex queries
2. Document formulas in panel descriptions
3. Add query examples to dashboard
