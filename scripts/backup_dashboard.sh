#!/usr/bin/env bash
# Backup power-analytics.json with modified internal dashboard name for parallel provisioning

set -e

DASHBOARD_FILE="etc/grafana/dashboards/power-analytics.json"
BACKUP_FILE="etc/grafana/dashboards/power-analytics.backup.json"

if [[ ! -f "$DASHBOARD_FILE" ]]; then
    echo "⚠️  Dashboard file not found: $DASHBOARD_FILE"
    exit 1
fi

echo "📊 Detected changes to power-analytics.json"
echo "📝 Creating backup..."

# Read current title and UID
CURRENT_TITLE=$(jq -r '.title' "$DASHBOARD_FILE")
CURRENT_UID=$(jq -r '.uid' "$DASHBOARD_FILE")

# Generate new title and UID for backup
BACKUP_TITLE="${CURRENT_TITLE} (Backup)"
BACKUP_UID="${CURRENT_UID}_backup"

echo "   Original: $CURRENT_TITLE [$CURRENT_UID]"
echo "   Backup:   $BACKUP_TITLE [$BACKUP_UID]"

# Create backup with modified title and UID
jq --arg title "$BACKUP_TITLE" --arg uid "$BACKUP_UID" \
   '.title = $title | .uid = $uid' \
   "$DASHBOARD_FILE" > "$BACKUP_FILE"

echo "✅ Backup created: $BACKUP_FILE"
echo "   Both dashboards can now be provisioned without conflict"
