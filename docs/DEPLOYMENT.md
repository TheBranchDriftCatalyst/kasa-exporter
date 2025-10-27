# Kasa Exporter Deployment Guide

## Overview

Kasa Exporter monitors TP-Link Kasa smart home devices and exports their metrics to Prometheus. It automatically adapts to your platform for optimal performance.

## Recommended Deployment

### Development Mode (All Platforms)

The recommended way to run the full stack:

```bash
task dev
```

This will:
- Install dependencies automatically
- Start Prometheus, Grafana, and Pushgateway in Docker
- Run the exporter natively with auto-reload
- Discover devices on your local network

**Access Points:**
- Kasa Exporter: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Pushgateway: http://localhost:9091

**Why native exporter?**
- Docker Desktop on macOS runs in a VM and can't do UDP broadcasts
- Native execution gives direct network access for device discovery
- Backend services (Prometheus, Grafana) don't need special network access

## Development

For active development with the full stack:

```bash
task dev
```

This will:
- Install dependencies automatically
- Start Prometheus, Grafana, and Pushgateway in Docker
- Run the exporter natively with uvicorn's auto-reload feature
- Watch for file changes and restart automatically

**Access Points:**
- Kasa Exporter Dashboard: http://localhost:8000
- Metrics Endpoint: http://localhost:8000/metrics
- Debug API: http://localhost:8000/debug
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Pushgateway: http://localhost:9091

**To stop all services:**
```bash
task dev:stop
# Or manually:
# Ctrl+C to stop the exporter, then:
docker compose down
```

## Manual Deployment

### Native (Any Platform)

```bash
# Install dependencies
poetry install

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Run in development mode (with auto-reload)
task dev

# Or run normally
poetry run python -m kasa_exporter
```

### Docker (Linux Only)

```bash
# Create macvlan network
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  mdsn_net

# Start services
docker compose -f docker-compose.linux.yaml up -d
```

## Environment Variables

Create a `.env` file with:

```bash
# Kasa Cloud Credentials
KASA_USERNAME=your_email@example.com
KASA_PASSWORD=your_password

# Metrics Port
METRICS_PORT=8000

# Push Gateway (optional)
PUSH_GATEWAY_HOST=pushgateway
PUSH_GATEWAY_PORT=9091
PUSH_GATEWAY_DISABLED=false

# Grafana Admin Password
GRAFANA_ADMIN_PASSWORD=your_secure_password

# Network Interface (Linux only)
MDNS_INTERFACE=eth0
```

## Discovered Devices

Currently monitoring:
- **Lab Server** (192.168.1.248) - KP125M
- **Mjolnir** (192.168.1.165) - KP125M
- **Furbo** (192.168.1.29) - KP125M
- **3d printer** (192.168.1.245) - KP125M

## Metrics

The exporter provides Prometheus metrics for:
- Device state (on/off)
- Current power consumption
- Daily/monthly energy consumption
- Signal strength (RSSI)
- Firmware versions
- Auto-off status
- Cloud connection status
- And more...

## Troubleshooting

### No Devices Found

**On macOS:**
- Make sure devices are on the same network (192.168.1.x)
- Check that KASA_USERNAME and KASA_PASSWORD are correct
- Verify devices are accessible via the Kasa app

**On Linux:**
- Ensure macvlan network is created correctly
- Check that the network interface (eth0/eno1) is correct
- Verify subnet and gateway match your network

### Port Already in Use

```bash
# Find and kill the process
lsof -ti:8000 | xargs kill
# Or
pkill -f "python -m kasa_exporter"
```

### Metrics Endpoint Error

Check logs for specific errors:
```bash
# Native
tail -f /tmp/kasa_exporter.log

# Docker
docker compose logs -f kasa_exporter
```

## Architecture

```
┌─────────────┐
│  Kasa Cloud │ ← Credentials
└──────┬──────┘
       │
       ├─────────────┐
       │             │
┌──────▼──────┐  ┌──▼────────┐
│ Lab Server  │  │ Mjolnir   │ ...
│ (KP125M)    │  │ (KP125M)  │
└──────┬──────┘  └──┬────────┘
       │             │
       │ Local Network (UDP Discovery)
       │             │
    ┌──▼─────────────▼───┐
    │  Kasa Exporter     │ ← Native (macOS) or Docker (Linux)
    │  FastAPI + Python  │
    └──────┬─────────────┘
           │
           ├─→ / (Homepage Dashboard)
           ├─→ /metrics (Prometheus)
           └─→ /debug (JSON API)
```

## Links

- [Kasa Exporter Audit](docs/audits/2025-10-27-code-review.md)
- [Python-Kasa Library](https://github.com/python-kasa/python-kasa)
- [Prometheus](https://prometheus.io/)
