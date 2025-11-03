# Phase 1: Metrics Troubleshooting & Bug Fix

**Status**: ✅ COMPLETED
**Date Range**: 2025-11-01 to 2025-11-02

---

## Summary

This phase addressed a critical bug in the `consumption_cost` metric that was causing label cardinality explosion and incorrect cost calculations in dashboards.

### Problem

The `consumption_cost` metric was emitting 3 simultaneous time series per device (one for each rate class: `on_peak`, `off_peak`, `super_off_peak`), when it should only emit one representing the current active rate period.

**Impact**:
- Cardinality: 18 metrics instead of 6 (3× explosion)
- Dashboard queries returning 3× actual costs
- Stale label persistence in Prometheus client registry

### Solution Implemented

Implemented **Option 1** from the Metric Structure Redesign:
- Removed `rate_class` label from `consumption_cost` metric
- Rate class information now available via separate `current_energy_rate` metric
- Clean, simple design following Prometheus best practices

### Changes Made

1. **Metric Definition** (`kasa_exporter/devices/KP125M.py:134-143`)
   - Removed `derive_labels` from `consumption_cost` metric
   - Added documentation comment explaining the change

2. **Cardinality Reduction**
   - Before: 18 time series (6 devices × 3 rate_classes)
   - After: 6 time series (6 devices × 1 metric)

3. **Dashboard Updates**
   - Updated power analytics dashboard queries
   - Migrated to join pattern where rate class info needed

---

## Documents Archived

- `BUG.md` - Original bug report with evidence
- `FIX_APPLIED.md` - Implementation details and code changes
- `METRICS_AUDIT_PLAN.md` - Investigation checklist
- `DASHBOARD_MIGRATION_GUIDE.md` - Dashboard query migration guide
- `troubleshooting/` - Various troubleshooting guides and scripts

---

## Lessons Learned

1. **Prometheus Client Label Persistence**: Labels set on metrics persist in the registry even after they're no longer being updated
2. **Cardinality Management**: Dynamic labels that change over time can cause cardinality explosion
3. **Best Practice**: Keep metric cardinality low; use separate metrics or joins for dimensional analysis

---

## Related Issues

### Known Issue: TP-Link Authentication Errors

During this phase, authentication errors were observed with certain TP-Link devices:

```
Error updating device 192.168.1.245: Server response doesn't match our challenge
Error updating device 192.168.1.143: Server response doesn't match our challenge
Error updating device 192.168.1.248: Server response doesn't match our challenge
Error updating device 192.168.1.165: Server response doesn't match our challenge
```

**Status**: Under investigation
**Next Phase**: Will address authentication and device discovery improvements

---

## Next Phase Preview

Phase 2 will focus on:
- PostgreSQL/TimescaleDB integration for long-term storage
- Advanced analytics and metric redesign
- Load-shift savings analysis
- Device authentication improvements
