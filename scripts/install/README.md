# Kasa Exporter Service Installation

This directory contains scripts for installing kasa-exporter as a system service that runs automatically on boot.

## Quick Start

### Linux (systemd)

```bash
# System-wide installation (recommended)
cd scripts/install
sudo ./install.sh

# Or user-level installation (no sudo required)
./install.sh --user
```

### macOS (launchd)

```bash
cd scripts/install
./install.sh --user
```

## Installation Methods

### Option 1: Interactive Installation (Recommended)

The installer will prompt you for your Kasa credentials:

```bash
sudo ./install.sh
```

### Option 2: Non-Interactive Installation

Set environment variables before running:

```bash
sudo KASA_USERNAME="your@email.com" KASA_PASSWORD="yourpass" ./install.sh
```

### Option 3: User-Level Installation

Install without sudo for the current user only:

```bash
./install.sh --user
```

## What Gets Installed

### System-wide Installation (`sudo ./install.sh`)

**Linux:**
- Application: `/opt/kasa-exporter/`
- Service: `/etc/systemd/system/kasa-exporter.service`
- Config: `/etc/kasa-exporter/env`
- User: `kasa-exporter` (service account)
- Logs: `journalctl -u kasa-exporter`

**macOS:**
- Application: `/opt/kasa-exporter/`
- Service: `~/Library/LaunchAgents/com.kasa-exporter.plist`
- Logs: `/opt/kasa-exporter/logs/`

### User-level Installation (`./install.sh --user`)

**Linux:**
- Application: `~/.local/share/kasa-exporter/`
- Service: `~/.config/systemd/user/kasa-exporter.service`
- Config: `~/.config/kasa-exporter/env`
- Logs: `journalctl --user -u kasa-exporter`

**macOS:**
- Application: `~/.local/share/kasa-exporter/`
- Service: `~/Library/LaunchAgents/com.kasa-exporter.plist`
- Logs: `~/.local/share/kasa-exporter/logs/`

## Updating the Installation

To update an existing installation to the latest version:

```bash
cd scripts/install

# System-wide installation
sudo ./update.sh

# User-level installation
./update.sh --user

# Update without restarting service
sudo ./update.sh --no-restart
```

The update script will:
1. Stop the running service
2. Backup current configuration
3. Copy updated application files
4. Update dependencies with Poetry
5. Restart the service (unless `--no-restart` specified)

**Note:** Your configuration and credentials are preserved during updates.

## Managing the Service

### Using Task Commands (Easiest)

From the repository root:

```bash
# Check status
task service:status

# Start/stop/restart
task service:start
task service:stop
task service:restart

# View logs
task service:logs              # Follow logs
task service:logs:tail         # Last 50 lines

# Enable/disable auto-start
task service:enable
task service:disable

# Health check
task service:health
```

### Using systemd (Linux)

```bash
# System service
sudo systemctl status kasa-exporter
sudo systemctl start kasa-exporter
sudo systemctl stop kasa-exporter
sudo systemctl restart kasa-exporter
sudo systemctl enable kasa-exporter
sudo systemctl disable kasa-exporter
sudo journalctl -u kasa-exporter -f

# User service
systemctl --user status kasa-exporter
systemctl --user start kasa-exporter
systemctl --user stop kasa-exporter
systemctl --user restart kasa-exporter
systemctl --user enable kasa-exporter
systemctl --user disable kasa-exporter
journalctl --user -u kasa-exporter -f
```

### Using launchd (macOS)

```bash
# Check status
launchctl list | grep kasa-exporter

# Start
launchctl load ~/Library/LaunchAgents/com.kasa-exporter.plist

# Stop
launchctl unload ~/Library/LaunchAgents/com.kasa-exporter.plist

# View logs
tail -f ~/.local/share/kasa-exporter/logs/kasa-exporter.log
```

## Configuration

### Environment Variables

Edit the environment file to change settings:

**Linux (system):** `/etc/kasa-exporter/env`
**Linux (user):** `~/.config/kasa-exporter/env`

```bash
# Kasa credentials
KASA_USERNAME=your@email.com
KASA_PASSWORD=yourpassword

# Optional settings
TZ=America/Los_Angeles
LOG_LEVEL=INFO
METRICS_PORT=9200
```

After editing, restart the service:

```bash
task service:restart
# or
sudo systemctl restart kasa-exporter
```

**macOS:** Environment variables are in the plist file. Edit:
```bash
nano ~/Library/LaunchAgents/com.kasa-exporter.plist
```

### Accessing the Dashboard

Once installed, access the exporter at:

- **Dashboard:** http://localhost:9200
- **Metrics:** http://localhost:9200/metrics
- **Health:** http://localhost:9200/health
- **Debug:** http://localhost:9200/debug

## Uninstallation

### Remove Everything

```bash
cd scripts/install
sudo ./uninstall.sh         # System installation
./uninstall.sh --user       # User installation
```

### Keep Data, Remove Service Only

```bash
sudo ./uninstall.sh --keep-data
```

## Troubleshooting

### Service Won't Start

1. Check the logs:
   ```bash
   task service:logs:tail
   # or
   sudo journalctl -u kasa-exporter -n 50
   ```

2. Verify credentials:
   ```bash
   cat /etc/kasa-exporter/env
   ```

3. Test manually:
   ```bash
   cd /opt/kasa-exporter
   .venv/bin/python -m kasa_exporter
   ```

### Permission Issues

If you get permission errors:

```bash
# Fix ownership (system installation)
sudo chown -R kasa-exporter:kasa-exporter /opt/kasa-exporter

# Or use user installation instead
./install.sh --user
```

### Port Already in Use

Change the metrics port:

```bash
# Edit config
sudo nano /etc/kasa-exporter/env

# Add or change:
METRICS_PORT=9000

# Restart
task service:restart
```

### Can't Find Devices

1. Ensure the service can access your network
2. Check that KASA_USERNAME and KASA_PASSWORD are correct
3. Verify devices are on the same network
4. Check logs for discovery errors

## Security Considerations

### System Installation
- Runs as dedicated `kasa-exporter` user (Linux)
- Limited file system access (systemd hardening)
- Credentials stored in root-only readable file

### User Installation
- Runs as your user account
- Credentials in user home directory
- No system-wide access

### Recommendations

1. **Use system installation** for production servers
2. **Use user installation** for development/testing
3. **Secure the environment file:**
   ```bash
   sudo chmod 600 /etc/kasa-exporter/env
   ```
4. **Consider using secrets management** for sensitive deployments

## Integration with Monitoring

### Prometheus

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'kasa-exporter'
    static_configs:
      - targets: ['localhost:9200']
```

### Grafana

1. Import the included dashboard from `etc/grafana/dashboards/`
2. Or access the built-in dashboard at `http://localhost:9200`

## Advanced Configuration

### Resource Limits

The systemd service includes resource limits:

- Memory: 512MB max
- CPU: 50% max
- File descriptors: 65536

Edit `/etc/systemd/system/kasa-exporter.service` to adjust:

```ini
[Service]
MemoryLimit=1G
CPUQuota=100%
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart kasa-exporter
```

### Multiple Instances

To run multiple instances (different ports):

1. Copy the service file:
   ```bash
   sudo cp /etc/systemd/system/kasa-exporter.service \
          /etc/systemd/system/kasa-exporter-2.service
   ```

2. Edit the new service file to use different port
3. Create separate environment file
4. Enable and start

## Files Reference

- `install.sh` - Installation script
- `update.sh` - Update script for existing installations
- `uninstall.sh` - Uninstallation script
- `kasa-exporter.service` - systemd unit file template
- `com.kasa-exporter.plist` - launchd plist template
- `README.md` - This file

## Support

For issues:
1. Check logs: `task service:logs:tail`
2. Check health: `task service:health`
3. Test manually in repo: `poetry run python -m kasa_exporter`
4. Open issue on GitHub
