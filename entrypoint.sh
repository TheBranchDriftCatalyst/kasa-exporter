#!/bin/bash

mkdir -p logs
echo "Starting script..." > logs/debug.log
nohup poetry run python -m kasa_exporter.exporter > logs/output.log 2>&1 &
PID=$!
echo $PID > /tmp/kasa_exporter.pid
echo "PID: $PID" >> logs/debug.log
