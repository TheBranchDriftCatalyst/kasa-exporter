# Stability Improvements for Kasa Exporter

## Overview

This document describes the stability improvements implemented to fix issues where the kasa-exporter daemon would stop working after running for ~24 hours.

## Problems Fixed

### 1. **No Timeouts on Blocking Operations** (CRITICAL)
**Problem**: Device operations (`device.update()`, `Discover.discover()`) had no timeouts, causing the application to hang indefinitely if a device became unresponsive or network issues occurred.

**Solution**:
- Added `asyncio.wait_for()` with 30-second timeout for device discovery
- Added 10-second timeout for individual device updates
- Added 5-second timeout for device disconnections
- Added 10-second timeout for PushGateway operations

**Files Modified**:
- `kasa_exporter/routines/exporter.py:42-53,70`
- `kasa_exporter/routines/pushgateway.py:38-45`

---

### 2. **Unhandled Exceptions Killed Background Tasks** (CRITICAL)
**Problem**: Each background task ran in a `while True` loop. Any unhandled exception would terminate the entire task silently, leaving the app running but non-functional.

**Solution**:
- Wrapped entire `while True` loops in try/except blocks
- Added exponential backoff retry logic (1s, 2s, 4s, 8s... up to 60s max)
- After 5 consecutive failures, state is reset and retry count is zeroed
- All exceptions are logged with context

**Files Modified**:
- `kasa_exporter/routines/exporter.py:78-102`
- `kasa_exporter/routines/device_registry.py:91-101`
- `kasa_exporter/routines/pushgateway.py:75-85`

---

### 3. **Dictionary Race Condition** (CRITICAL)
**Problem**: The device registry pruning task modified `self.devices` and `self.last_checkin` dictionaries while the scraper task was iterating over them, causing potential `RuntimeError: dictionary changed size during iteration`.

**Solution**:
- Created immutable snapshots using `list()` and `dict()` before iteration
- Registry pruning now operates on snapshot, then modifies original dicts safely

**Files Modified**:
- `kasa_exporter/routines/exporter.py:48` (snapshot for device iteration)
- `kasa_exporter/routines/device_registry.py:71` (snapshot for checkin iteration)

---

### 4. **No Docker Restart Policy** (HIGH)
**Problem**: If the container crashed, it would not automatically restart.

**Solution**:
- Added `restart: unless-stopped` to docker-compose.yaml
- Container will now automatically restart on failure

**Files Modified**:
- `docker-compose.yaml:17`

---

### 5. **No Health Check Monitoring** (HIGH)
**Problem**: No way to detect if background tasks had crashed while the app appeared to be running.

**Solution**:
- Added `/health` endpoint that monitors all background tasks
- Returns HTTP 503 if any task is unhealthy (done but not cancelled = crashed)
- Reports exception information for crashed tasks
- Added `/ready` endpoint to verify device discovery is working
- Added Docker healthcheck that calls `/health` every 30 seconds
- After 3 failed health checks, Docker will restart the container

**Files Modified**:
- `kasa_exporter/__main__.py:33,39-55,72-142`
- `docker-compose.yaml:18-23`
- `Dockerfile:6` (added curl for health checks)

---

### 6. **PushGateway Failure Accumulation** (MEDIUM)
**Problem**: If PushGateway was unavailable, failures would accumulate without backoff.

**Solution**:
- Added consecutive failure tracking
- After 10 consecutive failures, backs off for 60 seconds before retrying
- Resets failure count on success

**Files Modified**:
- `kasa_exporter/routines/pushgateway.py:30-31,48,50-69`

---

### 7. **Network Interface State Persistence** (MEDIUM)
**Problem**: The `interface` dictionary used for device discovery was initialized once and never reset, causing potential stale state issues.

**Solution**:
- Interface dictionary is now reset to `{}` after max retries are reached
- Ensures clean state recovery after network issues

**Files Modified**:
- `kasa_exporter/routines/exporter.py:87,100`

---

## New Endpoints

### `/health`
- **Purpose**: Monitor background task health
- **Returns**:
  - HTTP 200 if all tasks are running
  - HTTP 503 if any task has crashed
- **Response**:
  ```json
  {
    "status": "healthy",
    "tasks": [
      {
        "name": "device_scraper",
        "running": true,
        "cancelled": false,
        "healthy": true
      }
    ],
    "device_count": 5
  }
  ```

### `/ready`
- **Purpose**: Readiness probe for orchestration systems
- **Returns**:
  - HTTP 200 if at least one device discovered
  - HTTP 503 if no devices found yet
- **Response**:
  ```json
  {
    "ready": true,
    "device_count": 5
  }
  ```

---

## Configuration Changes

### Docker Compose
```yaml
kasa_exporter:
  restart: unless-stopped  # Auto-restart on failure
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s    # Check every 30 seconds
    timeout: 10s     # Fail if check takes >10s
    retries: 3       # Restart after 3 failures
    start_period: 40s  # Grace period on startup
```

### Timeout Values
| Operation | Timeout | Rationale |
|-----------|---------|-----------|
| Device Discovery | 30s | Network scan can be slow |
| Device Update | 10s | Individual device should respond quickly |
| Device Disconnect | 5s | Cleanup operation, fail fast |
| PushGateway Push | 10s | Remote service, reasonable timeout |
| Health Check | 10s | Docker healthcheck timeout |

---

## Retry Strategy

All background tasks now use **exponential backoff** with the following parameters:

- **Base Delay**: 1 second
- **Max Retries**: 5 attempts
- **Max Delay**: 60 seconds
- **Backoff Formula**: `min(base_delay * (2 ** retry_count), 60)`

**Example sequence**:
1. Failure → retry in 1s
2. Failure → retry in 2s
3. Failure → retry in 4s
4. Failure → retry in 8s
5. Failure → retry in 16s
6. Max retries → reset state → retry in 32s
7. Continue with exponential backoff...

---

## Monitoring Recommendations

### Prometheus Alerts
Monitor these new metrics:

```yaml
# Alert if container is unhealthy
- alert: KasaExporterUnhealthy
  expr: up{job="kasa_exporter"} == 0
  for: 2m

# Alert if no devices discovered
- alert: KasaExporterNoDevices
  expr: device_registry_total_devices == 0
  for: 5m
```

### Log Monitoring
Watch for these critical log messages:

- `"Max retries reached"` - Task is repeatedly failing
- `"Timeout updating device"` - Specific device is unresponsive
- `"Device discovery timed out"` - Network issues
- `"Shutting down background tasks"` - App is stopping

---

## Testing

To verify the improvements work:

### 1. Build and Start
```bash
docker-compose build
docker-compose up -d
```

### 2. Check Health
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy",...}
```

### 3. Check Readiness
```bash
curl http://localhost:8000/ready
# Should return: {"ready":true,...}
```

### 4. Monitor Logs
```bash
docker-compose logs -f kasa_exporter
```

### 5. Simulate Device Failure
Unplug a device and watch logs - should see timeout warnings but app continues running.

### 6. Check Docker Health Status
```bash
docker-compose ps
# STATUS column should show "healthy"
```

---

## Migration Guide

### Existing Deployments

1. **Pull latest code**:
   ```bash
   git pull
   ```

2. **Rebuild container**:
   ```bash
   docker-compose build
   ```

3. **Restart with new configuration**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Verify health checks working**:
   ```bash
   docker-compose ps  # Should show "healthy"
   curl http://localhost:8000/health
   ```

### Systemd Deployments

If running via systemd instead of Docker, add health check monitoring:

```ini
[Unit]
Description=Kasa Exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/poetry run python -m kasa_exporter
Restart=always
RestartSec=10

# Health check
ExecStartPost=/bin/sleep 30
ExecStartPost=/usr/bin/curl -f http://localhost:8000/health

[Install]
WantedBy=multi-user.target
```

---

## Expected Behavior

### Normal Operation
- Tasks scrape devices every 10 seconds
- Timeouts logged as warnings, not errors
- Retry count stays at 0
- Health endpoint returns 200
- Docker status shows "healthy"

### During Network Issues
- Timeouts increase temporarily
- Exponential backoff kicks in
- Errors logged with retry count
- Eventually recovers when network stabilizes
- Health endpoint may briefly return 503, then recovers

### During Device Failure
- Individual device update times out
- Device marked as failed for that cycle
- Other devices continue to be scraped
- Failed device retried next cycle
- App remains healthy overall

### During Total Failure
- All tasks hit max retries
- State is reset (interface cleared)
- Tasks continue attempting recovery
- After 3 consecutive health check failures, Docker restarts container
- Fresh start should resolve transient issues

---

## Performance Impact

- **CPU**: Minimal increase (snapshot creation is fast)
- **Memory**: Negligible (snapshots are small lists/dicts)
- **Network**: No change
- **Latency**: Added timeouts prevent indefinite hangs
- **Logging**: Slightly more verbose (includes retry information)

---

## Future Improvements

Potential enhancements for even better stability:

1. **Circuit Breaker Pattern**: Skip devices that repeatedly fail
2. **Metrics for Task Health**: Expose task health as Prometheus metrics
3. **Configurable Timeouts**: Allow environment variable configuration
4. **Device-Level Retry Limits**: Mark devices as "degraded" after N failures
5. **Graceful Degradation**: Continue with partial device set if some fail
6. **Persistent State**: Save device registry to disk for faster startup
7. **Rate Limiting**: Prevent overwhelming network during discovery
8. **Connection Pooling**: Reuse device connections where possible

---

## Changelog

### Version: Latest (2024-10-27)
- ✅ Added timeouts to all blocking operations
- ✅ Implemented exponential backoff retry logic
- ✅ Fixed dictionary race conditions with snapshots
- ✅ Added `/health` and `/ready` endpoints
- ✅ Configured Docker health checks
- ✅ Added `restart: unless-stopped` policy
- ✅ Installed curl in Docker image for health checks
- ✅ Added consecutive failure tracking for PushGateway
- ✅ Network interface reset on repeated failures
- ✅ Comprehensive error logging with context

---

## Support

If issues persist after these improvements:

1. Check logs: `docker-compose logs -f kasa_exporter`
2. Verify health: `curl http://localhost:8000/health`
3. Check device count: `curl http://localhost:8000/debug`
4. Verify Docker health: `docker-compose ps`
5. Report issues with log output and health check responses
