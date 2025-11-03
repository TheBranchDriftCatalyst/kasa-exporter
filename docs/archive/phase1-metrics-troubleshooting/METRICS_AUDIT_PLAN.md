# Metrics Endpoint Audit Plan

**Purpose**: Investigate and resolve the consumption_cost metric bug where multiple rate_class labels are emitted simultaneously

**Bug Reference**: `docs/BUG.md`

**Date**: 2025-11-01

---

## Phase 1: Data Collection & Verification

### 1.1 Snapshot Current Metrics State

**Objective**: Capture baseline metrics output for analysis

**Tasks**:
- [ ] Capture full `/metrics` endpoint output
  ```bash
  curl -s http://localhost:9200/metrics > /tmp/metrics_snapshot_$(date +%Y%m%d_%H%M%S).txt
  ```

- [ ] Count total time series per metric
  ```bash
  curl -s http://localhost:9200/metrics | grep "^consumption_cost{" | wc -l
  # Expected: 6 (one per device)
  # Actual: 18 (three per device)
  ```

- [ ] Verify `current_energy_rate` metric behavior
  ```bash
  curl -s http://localhost:9200/metrics | grep "^current_energy_rate{" | wc -l
  # Does this also emit 3 values per device?
  ```

- [ ] Check all metrics with `derive_labels`
  ```bash
  # Find all metrics in KP125M.py that use derive_labels
  grep -A 5 '"derive_labels":' kasa_exporter/devices/KP125M.py
  ```

### 1.2 Prometheus Query Verification

**Objective**: Understand how Prometheus stores these metrics

**Tasks**:
- [ ] Query total unique time series
  ```promql
  count(consumption_cost)
  # Expected: 6, Actual: 18
  ```

- [ ] Query cardinality by device
  ```promql
  count by (alias)(consumption_cost)
  # Each device should show: 1, Actual: 3
  ```

- [ ] Check metric timestamps
  ```promql
  consumption_cost{alias="Dream Machine"}
  # Verify all 3 rate_classes have identical timestamps
  ```

- [ ] Query historical data
  ```promql
  consumption_cost{alias="Dream Machine"}[6h]
  # Check if rate_class changes over time or all 3 persist
  ```

### 1.3 Code Execution Tracing

**Objective**: Add debug logging to understand metric creation flow

**Tasks**:
- [ ] Add logging to `KP125M.py` getter functions
  ```python
  "getter": lambda device: (
      logger.debug(f"calc_rate called for {device.alias}"),
      calculator.calc_rate(device.state_information["Current consumption"])
  )[1],
  ```

- [ ] Add logging to `derive_labels` functions
  ```python
  "rate_class": lambda _d: (
      logger.debug(f"get_rate_name called, returning: {calculator.get_rate_name(...)}"),
      calculator.get_rate_name(...)
  )[1],
  ```

- [ ] Add logging to `prom_device_extractor.py:update_metrics()`
  ```python
  # Line ~190: Before metric.labels(**all_labels).set(metric_value)
  logger.debug(
      f"Setting metric {metric_key}",
      device=getattr(device, 'alias', 'unknown'),
      labels=all_labels,
      value=metric_value
  )
  ```

- [ ] Restart exporter and capture logs
  ```bash
  sudo systemctl restart kasa-exporter
  sudo tail -f /opt/kasa-exporter/exporter.log | grep -i "consumption_cost\|rate_class"
  ```

---

## Phase 2: Root Cause Investigation

### 2.1 PrometheusDeviceExtractor Analysis

**Objective**: Determine if metric registration or update logic is creating duplicates

**Files**: `kasa_exporter/devices/prom_device_extractor.py`

**Tasks**:
- [ ] Review `register_metric()` (lines 105-152)
  - Does it register multiple metrics with different label combinations?
  - Is `derive_labels` processed correctly?

- [ ] Review `update_metrics()` (lines 154-200)
  - Is this called multiple times per device per scrape?
  - Are derived labels evaluated multiple times with different values?
  - Check if `all_labels` dict is mutated/accumulated

- [ ] Verify `get_device_labels()` (lines 88-103)
  - Are dimension labels consistent?
  - Check VERSION label injection

- [ ] Test with minimal metric
  ```python
  # Create test metric WITHOUT derive_labels
  "test_consumption_cost": {
      "type": PromMetricType.GAUGE,
      "getter": lambda device: calculator.calc_rate(
          device.state_information["Current consumption"]
      ),
      # NO derive_labels
  },
  ```
  - Does this emit 1 or 3 values?

### 2.2 TimeOfUseCalc Analysis

**Objective**: Verify calculator functions return single values

**Files**: `kasa_exporter/utils/time_of_use_calc.py`

**Tasks**:
- [ ] Unit test `get_rate_name()` at different times
  ```python
  # Test that it returns ONE string, not a list
  calculator = TimeOfUseCalc()
  current_time = datetime.now(pytz.timezone("America/Denver"))
  season = calculator.get_current_season()
  rate_name = calculator.get_rate_name(current_time, season)
  assert isinstance(rate_name, str)  # Should be "on_peak" or "off_peak" or "super_off_peak"
  ```

- [ ] Unit test `calc_rate()` determinism
  ```python
  # Calling multiple times should return same value
  cost1 = calculator.calc_rate(56.467)
  cost2 = calculator.calc_rate(56.467)
  assert cost1 == cost2
  ```

- [ ] Check for side effects
  - Does calculator maintain state that changes between calls?
  - Are there any caching mechanisms?

### 2.3 Scrape Loop Analysis

**Objective**: Determine if devices are being processed multiple times

**Files**: `kasa_exporter/routines/exporter.py`

**Tasks**:
- [ ] Verify `scrape_devices()` loop (lines 26-92)
  - Is `KP125MDeviceExtractor.update_metrics(device)` called once per device?
  - Could `devices_snapshot` contain duplicates?

- [ ] Add counter to track update_metrics calls
  ```python
  update_count = {}
  for addr, device in devices_snapshot:
      update_count[device.alias] = update_count.get(device.alias, 0) + 1
      KP125MDeviceExtractor.update_metrics(device)
  logger.info(f"Update counts: {update_count}")
  ```

- [ ] Check for concurrent/parallel execution
  - Are there multiple asyncio tasks calling update_metrics?

### 2.4 Git History Investigation

**Objective**: Understand when and why this behavior was introduced

**Tasks**:
- [ ] Review commit `cb9ec1a` (added rate_class labels)
  ```bash
  git show cb9ec1a
  ```

- [ ] Review commit `49ad2d6` (split cost and rate metrics)
  ```bash
  git show 49ad2d6
  git diff 49ad2d6^..49ad2d6 -- kasa_exporter/devices/KP125M.py
  ```

- [ ] Check if there's a feature branch or PR discussing this
  ```bash
  git log --all --grep="theoretical\|all.*rates\|multiple.*rate"
  ```

- [ ] Compare production vs development code
  ```bash
  diff /opt/kasa-exporter/kasa_exporter/devices/KP125M.py \
       /Users/panda/catalyst-devspace/workspace/@kasa-exporter/kasa_exporter/devices/KP125M.py
  ```

---

## Phase 3: Hypothesis Testing

### 3.1 Test Hypothesis: Intentional Design

**Theory**: Exporter is designed to show all theoretical costs for "what-if" analysis

**Tests**:
- [ ] Search for comments/docs mentioning "theoretical" or "all rates"
  ```bash
  grep -r "theoretical\|all.*rate.*class" kasa_exporter/ docs/
  ```

- [ ] Check if there's a config option to toggle this behavior
  ```bash
  grep -r "emit.*all\|theoretical.*cost" etc/
  ```

- [ ] Review dashboard queries to see if they expect 3 values
  ```bash
  jq '.panels[].targets[].expr' etc/grafana/dashboards/power-analytics.json | \
    grep "consumption_cost"
  ```

**Outcome**:
- If YES: This is a feature, dashboard queries need fixing
- If NO: This is a bug, exporter code needs fixing

### 3.2 Test Hypothesis: Derive Labels Bug

**Theory**: `derive_labels` evaluation creates multiple label combinations

**Tests**:
- [ ] Create test metric with static derive_label
  ```python
  "test_metric_static": {
      "type": PromMetricType.GAUGE,
      "getter": lambda device: 1.0,
      "derive_labels": {
          "static_label": lambda _d: "constant_value"
      },
  },
  ```
  - Does this emit 1 or multiple values?

- [ ] Create test metric with time-varying derive_label
  ```python
  "test_metric_time": {
      "type": PromMetricType.GAUGE,
      "getter": lambda device: 1.0,
      "derive_labels": {
          "hour": lambda _d: str(datetime.now().hour)
      },
  },
  ```
  - Over 24 hours, does it accumulate 24 time series?

- [ ] Review prometheus_client library documentation
  - Is there a known issue with labels changing values?
  - Are there best practices we're violating?

### 3.3 Test Hypothesis: Metric Staleness

**Theory**: Old metrics aren't expiring, causing accumulation

**Tests**:
- [ ] Check Prometheus scrape config
  ```yaml
  # /etc/prometheus/prometheus.yml
  scrape_configs:
    - job_name: 'kasa_exporter_prod'
      scrape_interval: 5s  # Very frequent
  ```

- [ ] Manually curl metrics endpoint repeatedly
  ```bash
  for i in {1..10}; do
    echo "=== Scrape $i ==="
    curl -s http://localhost:9200/metrics | grep 'consumption_cost{alias="Dream Machine"' | wc -l
    sleep 5
  done
  ```
  - Does the count stay at 3, or does it grow?

- [ ] Restart exporter and check immediately
  ```bash
  sudo systemctl restart kasa-exporter
  sleep 2
  curl -s http://localhost:9200/metrics | grep "^consumption_cost{" | wc -l
  ```
  - Do we start with 6 (correct) and grow to 18, or immediately see 18?

---

## Phase 4: Fix Implementation

### 4.1 Option A: Remove Theoretical Costs (if bug)

**If**: Exporter should only emit current rate period cost

**Fix**:
- Keep `consumption_cost` as-is (with rate_class derive_label)
- Ensure `get_rate_name()` returns current period only
- Verify metric is emitted once per device

**Verification**:
```promql
count(consumption_cost) == 6  # One per device
```

### 4.2 Option B: Separate Metrics (if feature)

**If**: Theoretical costs are desired, create explicit metrics

**Fix**:
```python
"consumption_cost_current": {
    "type": PromMetricType.GAUGE,
    "getter": lambda device: calculator.calc_rate(
        device.state_information["Current consumption"]
    ),
    "derive_labels": {
        "rate_class": lambda _d: calculator.get_rate_name(...)
    },
},
"consumption_cost_if_super_off_peak": {
    "type": PromMetricType.GAUGE,
    "getter": lambda device: (
        device.state_information["Current consumption"] / 1000 * 0.314
    ),
},
"consumption_cost_if_off_peak": {
    "type": PromMetricType.GAUGE,
    "getter": lambda device: (
        device.state_information["Current consumption"] / 1000 * 0.351
    ),
},
"consumption_cost_if_on_peak": {
    "type": PromMetricType.GAUGE,
    "getter": lambda device: (
        device.state_information["Current consumption"] / 1000 * 0.634
    ),
},
```

**Verification**:
```promql
count(consumption_cost_current) == 6
count(consumption_cost_if_super_off_peak) == 6
count(consumption_cost_if_off_peak) == 6
count(consumption_cost_if_on_peak) == 6
```

### 4.3 Option C: Remove derive_labels

**If**: derive_labels is causing the issue

**Fix**:
```python
"consumption_cost": {
    "type": PromMetricType.GAUGE,
    "getter": lambda device: calculator.calc_rate(
        device.state_information["Current consumption"]
    ),
    # NO derive_labels - rate_class info available in current_energy_rate metric
},
```

**Dashboard Adjustment**:
```promql
# Join with current_energy_rate to get rate_class
consumption_cost * on(alias) group_left(rate_class) current_energy_rate
```

---

## Phase 5: Dashboard Fixes

### 5.1 Update Existing Dashboards

**Tasks**:
- [ ] Audit `power-analytics.json` queries
  - Replace `sum(consumption_cost)` with correct aggregation
  - Add rate_class filters where needed

- [ ] Fix `load-shift-savings.json` queries
  - Ensure savings calculations use current cost only
  - Update theoretical min cost calculation

- [ ] Create dashboard audit report
  - Document all affected panels
  - Provide before/after queries

### 5.2 Data Cleanup

**Tasks**:
- [ ] Clear Prometheus data (if corrupted)
  ```bash
  docker stop prometheus
  docker volume rm prometheus-data  # WARNING: Deletes all history
  docker volume create prometheus-data
  docker start prometheus
  ```

- [ ] OR wait for staleness (retention period)
  - Default: 15 days
  - Stale metrics will naturally drop off

---

## Phase 6: Prevention & Monitoring

### 6.1 Add Metric Validation Tests

**Tasks**:
- [ ] Create pytest test for metric cardinality
  ```python
  def test_consumption_cost_cardinality():
      """Verify consumption_cost emits exactly 1 time series per device"""
      metrics_text = requests.get("http://localhost:9200/metrics").text
      device_count = len(set(re.findall(r'alias="([^"]+)"', metrics_text)))
      cost_metrics = len(re.findall(r'^consumption_cost{', metrics_text, re.M))
      assert cost_metrics == device_count, \
          f"Expected {device_count} consumption_cost metrics, got {cost_metrics}"
  ```

- [ ] Add CI/CD integration test
  - Start exporter in test mode
  - Verify metric counts
  - Fail build if duplicates detected

### 6.2 Add Monitoring Alerts

**Tasks**:
- [ ] Create Prometheus alert for metric cardinality
  ```yaml
  # alerts.yml
  - alert: ConsumptionCostCardinalityMismatch
    expr: |
      count(consumption_cost) != count(count by (alias)(current_consumption))
    for: 5m
    annotations:
      summary: "consumption_cost metric has wrong cardinality"
      description: "Expected 1 time series per device, got {{ $value }}"
  ```

### 6.3 Documentation Updates

**Tasks**:
- [ ] Document metric schema in `docs/METRICS.md`
  - Expected cardinality for each metric
  - Label combinations
  - Example queries

- [ ] Add troubleshooting guide
  - How to detect metric duplication
  - How to verify correct behavior
  - Dashboard query best practices

---

## Success Criteria

- [ ] `consumption_cost` metric emits exactly 1 time series per device (6 total)
- [ ] `sum(consumption_cost)` returns sensible value (~$0.12-0.38/hour depending on current rate)
- [ ] All dashboard panels show correct data
- [ ] Load Shift Savings Analysis dashboard works as expected
- [ ] Historical data integrity verified
- [ ] Tests added to prevent regression
- [ ] Documentation updated

---

## Timeline

- **Phase 1**: 2 hours (data collection)
- **Phase 2**: 4 hours (investigation)
- **Phase 3**: 2 hours (hypothesis testing)
- **Phase 4**: 2 hours (fix implementation)
- **Phase 5**: 2 hours (dashboard fixes)
- **Phase 6**: 2 hours (prevention)

**Total Estimated Time**: 14 hours

---

## Notes

- Keep `docs/BUG.md` updated with findings
- Document any assumptions or decisions made
- Take snapshots before making changes
- Test fixes in development before deploying to production
