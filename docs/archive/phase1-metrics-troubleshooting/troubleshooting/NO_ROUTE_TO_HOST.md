# Troubleshooting: "No route to host" (errno 65)

## Problem

You're seeing errors like:
```
Got error: [Errno 65] No route to host
```

## What This Means

Errno 65 (`EHOSTUNREACH`) means your Mac cannot establish a network route to the Kasa device IP addresses. This is different from a timeout - the OS is actively saying "I can't get there from here."

## Root Cause

**Fixed in this commit**: The exporter was not reading the `MDNS_INTERFACE` environment variable, so it wasn't using the correct network interface (`en0`) for device discovery.

## Why This Happens

1. **Wrong Network Interface** ✅ **FIXED**
   - The exporter now properly reads `MDNS_INTERFACE=en0`
   - Discovery will use the correct interface

2. **Cached Device IPs** (Likely current issue)
   - python-kasa library caches device IPs between runs
   - If devices changed networks/IPs, old cached IPs are unreachable
   - **Solution**: Clear the cache (see below)

3. **Device Actually Offline**
   - Devices might be powered off or disconnected from WiFi
   - **Solution**: Check device status in Kasa app

4. **Network Segmentation**
   - Your Mac on guest WiFi, devices on main network (or vice versa)
   - VLANs preventing communication
   - **Solution**: Ensure Mac and devices are on same network segment

5. **macOS Firewall**
   - Blocking mDNS/UDP packets needed for discovery
   - **Solution**: Check System Preferences → Security & Privacy → Firewall

## Diagnostic Steps

### 1. Check Device Discovery
```bash
# Test discovery manually with python-kasa CLI
poetry run kasa --username $KASA_USERNAME --password $KASA_PASSWORD discover
```

Expected output: Should list all your Kasa devices

### 2. Clear python-kasa Cache
```bash
# Remove cached device information
rm -rf ~/.local/share/python-kasa/
```

Then restart the exporter.

### 3. Verify Network Connectivity
```bash
# Check your network interface
ifconfig en0

# Should show:
# - status: active
# - inet 192.168.x.x (your IP)

# Try to ping a device (if you know its IP)
ping 192.168.1.XXX
```

### 4. Check Environment Variables
```bash
echo "KASA_USERNAME: $KASA_USERNAME"
echo "KASA_PASSWORD: ${KASA_PASSWORD:+SET}"
echo "MDNS_INTERFACE: $MDNS_INTERFACE"
```

Expected:
- `KASA_USERNAME`: Should show your email
- `KASA_PASSWORD`: Should show "SET"
- `MDNS_INTERFACE`: Should show "en0"

### 5. Run Exporter with Verbose Logging
```bash
LOG_LEVEL=DEBUG poetry run uvicorn kasa_exporter.__main__:app --reload --host 0.0.0.0 --port 9201
```

Look for:
- `Using mDNS interface: en0` (confirming interface is set)
- `Discovered and scraping device` (successful discovery)
- `Device X.X.X.X (DeviceName) unreachable` (specific device unreachable)

## Expected Behavior After Fix

### Good Case (Devices Reachable):
```
INFO: Using mDNS interface: en0
INFO: Discovered and scraping device, alias=Lab Server, model=KP125M, address=192.168.1.100
INFO: Discovered and scraping device, alias=Office Plug, model=KP125M, address=192.168.1.101
```

### Partial Failure (Some Devices Offline):
```
INFO: Using mDNS interface: en0
INFO: Discovered and scraping device, alias=Lab Server, model=KP125M, address=192.168.1.100
WARNING: Device 192.168.1.101 (Office Plug) unreachable (No route to host). Check network connectivity or device may be offline.
```

## Quick Fixes

### Fix 1: Clear Cache and Restart
```bash
rm -rf ~/.local/share/python-kasa/
task dev
```

### Fix 2: Verify Devices in Kasa App
Open the Kasa mobile app and verify all devices show as "Online"

### Fix 3: Restart Devices
If devices show offline in app, unplug and replug them

### Fix 4: Use Correct WiFi Network
Ensure your Mac is on the same WiFi network as your smart plugs (not guest network)

## Changes Made

**File**: `kasa_exporter/routines/exporter.py`

### Change 1: Read MDNS_INTERFACE Environment Variable
```python
# Before:
interface = {}

# After:
interface = {}
mdns_interface = os.getenv("MDNS_INTERFACE")
if mdns_interface:
    interface = {"interface": mdns_interface}
    logger.info(f"Using mDNS interface: {mdns_interface}")
else:
    logger.info("Using auto-detect for mDNS interface")
```

### Change 2: Better Error Logging
```python
# Added specific handling for errno 65:
except OSError as e:
    if e.errno == 65:  # EHOSTUNREACH - No route to host
        logger.warning(
            f"Device {addr} ({device.alias}) unreachable (No route to host). "
            f"Check network connectivity or device may be offline."
        )
```

## Still Having Issues?

If the errors persist after:
1. ✅ Clearing cache
2. ✅ Verifying devices are online in Kasa app
3. ✅ Confirming Mac and devices on same network

Then check:

### Advanced: Verify mDNS/Multicast Works
```bash
# Check if mDNS is responding on your network
dns-sd -B _kasa._tcp

# Or use avahi (if installed)
avahi-browse -a
```

### Advanced: Check Firewall Rules
```bash
# See if pf (packet filter) is blocking anything
sudo pfctl -s all
```

### Network Topology Issues
- Using VPN? Might be routing traffic away from local network
- Using Docker Desktop networking? Might isolate containers
- Multiple network interfaces active? Might have conflicting routes

## Testing the Fix

After restarting with the fix:

1. Check logs show: `Using mDNS interface: en0`
2. Verify metrics endpoint works: `curl http://localhost:9201/metrics`
3. Look for device metrics like: `current_consumption{alias="Lab Server"}`
4. Check dashboard: `http://localhost:9201/`

If you see devices listed on the dashboard, the fix worked! 🎉
