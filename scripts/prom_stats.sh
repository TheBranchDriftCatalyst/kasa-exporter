#!/usr/bin/env bash
# Query Prometheus database statistics
# Shows time range, database size, retention, and metric counts

set -e

# Configuration
PROM_URL="${PROM_URL:-http://localhost:9090}"
API_URL="${PROM_URL}/api/v1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper function to format bytes
format_bytes() {
    local bytes=$1
    if (( bytes < 1024 )); then
        echo "${bytes}B"
    elif (( bytes < 1048576 )); then
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1024}")KB"
    elif (( bytes < 1073741824 )); then
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1048576}")MB"
    else
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1073741824}")GB"
    fi
}

# Helper function to format duration
format_duration() {
    local seconds=$1
    local days=$((seconds / 86400))
    local hours=$(((seconds % 86400) / 3600))
    local mins=$(((seconds % 3600) / 60))

    if (( days > 0 )); then
        echo "${days}d ${hours}h ${mins}m"
    elif (( hours > 0 )); then
        echo "${hours}h ${mins}m"
    else
        echo "${mins}m"
    fi
}

# Helper function to query Prometheus
prom_query() {
    local query=$1
    local result=$(curl -sG --data-urlencode "query=${query}" "${API_URL}/query" 2>/dev/null | jq -r '.data.result[0].value[1]' 2>/dev/null)
    if [ -z "$result" ] || [ "$result" == "null" ]; then
        echo "N/A"
    else
        echo "$result"
    fi
}

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}        ${BLUE}Prometheus Database Statistics${NC}                  ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Prometheus is reachable
if ! curl -sf "${PROM_URL}/-/healthy" > /dev/null 2>&1; then
    echo -e "${RED}❌ Prometheus not reachable at ${PROM_URL}${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prometheus is reachable${NC}"
echo ""

# Get build info
echo -e "${YELLOW}📦 Build Information${NC}"
echo "───────────────────────────────────────────────────────────"
BUILD_INFO=$(curl -sG "${API_URL}/query?query=prometheus_build_info" 2>/dev/null | jq -r '.data.result[0].metric' 2>/dev/null)
if [ -n "$BUILD_INFO" ] && [ "$BUILD_INFO" != "null" ]; then
    VERSION=$(echo "$BUILD_INFO" | jq -r '.version' 2>/dev/null)
    BRANCH=$(echo "$BUILD_INFO" | jq -r '.branch' 2>/dev/null)
    REVISION=$(echo "$BUILD_INFO" | jq -r '.revision' 2>/dev/null | cut -c1-8)
    echo -e "   Version:  ${GREEN}${VERSION}${NC}"
    [ -n "$BRANCH" ] && [ "$BRANCH" != "null" ] && echo -e "   Branch:   $BRANCH"
    [ -n "$REVISION" ] && [ "$REVISION" != "null" ] && echo -e "   Revision: $REVISION"
else
    echo -e "   ${YELLOW}Build info not available${NC}"
fi
echo ""

# Storage information
echo -e "${YELLOW}💾 Storage Information${NC}"
echo "───────────────────────────────────────────────────────────"

# TSDB head stats
HEAD_SAMPLES=$(prom_query 'prometheus_tsdb_head_samples')
HEAD_SERIES=$(prom_query 'prometheus_tsdb_head_series')
HEAD_CHUNKS=$(prom_query 'prometheus_tsdb_head_chunks')

STORAGE_AVAILABLE=false
[ "$HEAD_SAMPLES" != "N/A" ] && echo -e "   Head Samples:     ${GREEN}${HEAD_SAMPLES}${NC}" && STORAGE_AVAILABLE=true
[ "$HEAD_SERIES" != "N/A" ] && echo -e "   Head Series:      ${GREEN}${HEAD_SERIES}${NC}" && STORAGE_AVAILABLE=true
[ "$HEAD_CHUNKS" != "N/A" ] && echo -e "   Head Chunks:      ${GREEN}${HEAD_CHUNKS}${NC}" && STORAGE_AVAILABLE=true

# Storage size (if available via node_exporter or custom metrics)
STORAGE_SIZE=$(prom_query 'prometheus_tsdb_storage_blocks_bytes')
if [ "$STORAGE_SIZE" != "N/A" ]; then
    STORAGE_SIZE_FMT=$(format_bytes "$STORAGE_SIZE")
    echo -e "   Storage Size:     ${GREEN}${STORAGE_SIZE_FMT}${NC}"
    STORAGE_AVAILABLE=true
fi

# WAL size
WAL_SIZE=$(prom_query 'prometheus_tsdb_wal_storage_size_bytes')
if [ "$WAL_SIZE" != "N/A" ]; then
    WAL_SIZE_FMT=$(format_bytes "$WAL_SIZE")
    echo -e "   WAL Size:         ${GREEN}${WAL_SIZE_FMT}${NC}"
    STORAGE_AVAILABLE=true
fi

if [ "$STORAGE_AVAILABLE" = false ]; then
    echo -e "   ${YELLOW}Storage metrics not exposed by Prometheus${NC}"
fi

echo ""

# Time range information
echo -e "${YELLOW}📅 Time Range Information${NC}"
echo "───────────────────────────────────────────────────────────"

# Oldest timestamp
OLDEST=$(prom_query 'prometheus_tsdb_lowest_timestamp / 1000')
NEWEST=$(prom_query 'prometheus_tsdb_head_max_time / 1000')

if [ "$OLDEST" != "N/A" ] && [ "$NEWEST" != "N/A" ]; then
    OLDEST_DATE=$(date -r "${OLDEST%.*}" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "N/A")
    NEWEST_DATE=$(date -r "${NEWEST%.*}" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "N/A")
    DURATION=$((${NEWEST%.*} - ${OLDEST%.*}))
    DURATION_FMT=$(format_duration "$DURATION")

    echo -e "   Oldest Data:      ${GREEN}${OLDEST_DATE}${NC}"
    echo -e "   Newest Data:      ${GREEN}${NEWEST_DATE}${NC}"
    echo -e "   Total Duration:   ${GREEN}${DURATION_FMT}${NC}"
else
    echo -e "   ${RED}Unable to fetch time range${NC}"
fi

echo ""

# Block information
echo -e "${YELLOW}📦 Block Information${NC}"
echo "───────────────────────────────────────────────────────────"

BLOCKS=$(prom_query 'prometheus_tsdb_blocks_loaded')
COMPACTIONS=$(prom_query 'prometheus_tsdb_compactions_total')

BLOCKS_AVAILABLE=false
[ "$BLOCKS" != "N/A" ] && echo -e "   Blocks Loaded:    ${GREEN}${BLOCKS}${NC}" && BLOCKS_AVAILABLE=true
[ "$COMPACTIONS" != "N/A" ] && echo -e "   Compactions:      ${GREEN}${COMPACTIONS}${NC}" && BLOCKS_AVAILABLE=true

if [ "$BLOCKS_AVAILABLE" = false ]; then
    echo -e "   ${YELLOW}Block metrics not exposed by Prometheus${NC}"
fi

echo ""

# Ingestion stats
echo -e "${YELLOW}📊 Ingestion Statistics${NC}"
echo "───────────────────────────────────────────────────────────"

# Samples appended rate (over last 5 minutes)
SAMPLE_RATE=$(prom_query 'rate(prometheus_tsdb_head_samples_appended_total[5m])')
OOO_SAMPLES=$(prom_query 'prometheus_tsdb_out_of_order_samples_total')
SAMPLES_APPENDED=$(prom_query 'prometheus_tsdb_head_samples_appended_total')

INGEST_AVAILABLE=false
if [ "$SAMPLE_RATE" != "N/A" ]; then
    SAMPLE_RATE_FMT=$(awk "BEGIN {printf \"%.2f\", $SAMPLE_RATE}")
    echo -e "   Sample Rate:      ${GREEN}${SAMPLE_RATE_FMT} samples/sec${NC}"
    INGEST_AVAILABLE=true
fi

[ "$OOO_SAMPLES" != "N/A" ] && echo -e "   Out-of-Order:     ${GREEN}${OOO_SAMPLES}${NC}" && INGEST_AVAILABLE=true
[ "$SAMPLES_APPENDED" != "N/A" ] && echo -e "   Samples Appended: ${GREEN}${SAMPLES_APPENDED}${NC}" && INGEST_AVAILABLE=true

if [ "$INGEST_AVAILABLE" = false ]; then
    echo -e "   ${YELLOW}Ingestion metrics not exposed by Prometheus${NC}"
fi

echo ""

# Kasa-specific metrics
echo -e "${YELLOW}⚡ Kasa Exporter Metrics${NC}"
echo "───────────────────────────────────────────────────────────"

# Count unique kasa metrics
KASA_METRICS=$(curl -sG --data-urlencode "query=count({__name__=~\".*consumption.*|state|rssi|on_since|.*update.*|.*connection.*|.*energy_rate.*\"})" "${API_URL}/query" | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")
echo -e "   Kasa Time Series: ${GREEN}${KASA_METRICS}${NC}"

# Get device count
DEVICE_COUNT=$(curl -sG --data-urlencode "query=count(count by (alias) (current_consumption))" "${API_URL}/query" | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")
echo -e "   Devices Tracked:  ${GREEN}${DEVICE_COUNT}${NC}"

# Current total power consumption
TOTAL_POWER=$(prom_query 'sum(current_consumption)')
if [ "$TOTAL_POWER" != "N/A" ]; then
    TOTAL_POWER_FMT=$(awk "BEGIN {printf \"%.2f\", $TOTAL_POWER}")
    echo -e "   Current Power:    ${GREEN}${TOTAL_POWER_FMT}W${NC}"
fi

# Current total cost rate
TOTAL_COST=$(prom_query 'sum(consumption_cost)')
if [ "$TOTAL_COST" != "N/A" ]; then
    TOTAL_COST_FMT=$(awk "BEGIN {printf \"%.4f\", $TOTAL_COST}")
    echo -e "   Current Cost:     ${GREEN}\$${TOTAL_COST_FMT}/hour${NC}"
fi

echo ""

# Scrape information
echo -e "${YELLOW}🔄 Scrape Information${NC}"
echo "───────────────────────────────────────────────────────────"

# Get scrape duration and sample count for kasa-exporter
SCRAPE_DURATION=$(prom_query 'scrape_duration_seconds{job="kasa-exporter"}')
SCRAPE_SAMPLES=$(prom_query 'scrape_samples_scraped{job="kasa-exporter"}')
UP=$(prom_query 'up{job="kasa-exporter"}')

if [ "$SCRAPE_DURATION" != "N/A" ]; then
    SCRAPE_DURATION_MS=$(awk "BEGIN {printf \"%.2f\", $SCRAPE_DURATION * 1000}")
    echo -e "   Scrape Duration:  ${GREEN}${SCRAPE_DURATION_MS}ms${NC}"
fi

[ "$SCRAPE_SAMPLES" != "N/A" ] && echo -e "   Samples/Scrape:   ${GREEN}${SCRAPE_SAMPLES}${NC}"

# Last scrape success
if [ "$UP" == "1" ]; then
    echo -e "   Status:           ${GREEN}✅ UP${NC}"
elif [ "$UP" == "0" ]; then
    echo -e "   Status:           ${RED}❌ DOWN${NC}"
else
    echo -e "   Status:           ${YELLOW}⚠️  UNKNOWN (no scrape data)${NC}"
fi

echo ""
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
