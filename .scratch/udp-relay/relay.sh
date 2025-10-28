#!/bin/sh

# Get the host's gateway IP (Docker host)
HOST_IP=${HOST_IP:-host.docker.internal}

echo "Starting UDP relay to host at ${HOST_IP}"
echo "Relaying Kasa discovery ports 9999 and 20002"

# Relay port 9999 (Kasa protocol v1)
socat -d -d UDP4-RECVFROM:9999,broadcast,fork UDP4-SENDTO:${HOST_IP}:9999 &

# Relay port 20002 (Kasa protocol v2)
socat -d -d UDP4-RECVFROM:20002,broadcast,fork UDP4-SENDTO:${HOST_IP}:20002 &

# Keep container running
wait
