#!/usr/bin/env python3
"""
Generate cyberpunk-styled Grafana dashboards for Kasa Exporter.
Creates 5 specialized dashboards with synthwave color scheme.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

# Synthwave Cyberpunk Color Scheme
COLORS = {
    "cyan": "#00E5FF",
    "magenta": "#FF00FF",
    "purple": "#9D00FF",
    "pink": "#FF007F",
    "green": "#00FF41",
    "orange": "#FF9500",
    "yellow": "#FFD600",
    "blue": "#0080FF",
}

THRESHOLDS = {
    "cost_low": {"value": 0, "color": COLORS["green"]},
    "cost_medium": {"value": 0.35, "color": COLORS["yellow"]},
    "cost_high": {"value": 0.5, "color": COLORS["orange"]},
    "cost_extreme": {"value": 0.7, "color": COLORS["pink"]},
}


def create_base_dashboard(
    title: str, uid: str, description: str, tags: List[str]
) -> Dict[str, Any]:
    """Create base dashboard structure."""
    return {
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                    "enable": True,
                    "hide": True,
                    "iconColor": COLORS["cyan"],
                    "name": "Annotations & Alerts",
                    "type": "dashboard",
                }
            ]
        },
        "description": description,
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 2,
        "id": None,
        "links": [],
        "panels": [],
        "refresh": "10s",
        "schemaVersion": 39,
        "tags": tags,
        "templating": {
            "list": [
                {
                    "allValue": ".*",
                    "current": {"selected": False, "text": "All", "value": "$__all"},
                    "datasource": {"type": "prometheus", "uid": "PBFA97CFB590B2093"},
                    "definition": 'label_values(current_consumption, version)',
                    "hide": 0,
                    "includeAll": True,
                    "label": "Version",
                    "multi": False,
                    "name": "version",
                    "options": [],
                    "query": {
                        "qryType": 1,
                        "query": "label_values(current_consumption, version)",
                        "refId": "PrometheusVariableQueryEditor-VariableQuery",
                    },
                    "refresh": 1,
                    "regex": "",
                    "skipUrlSync": False,
                    "sort": 0,
                    "type": "query",
                }
            ]
        },
        "time": {"from": "now-6h", "to": "now"},
        "timepicker": {},
        "timezone": "America/Denver",
        "title": title,
        "uid": uid,
        "version": 1,
        "weekStart": "",
    }


def create_stat_panel(
    title: str,
    expr: str,
    x: int,
    y: int,
    w: int,
    h: int,
    unit: str = "short",
    color_mode: str = "background",
    thresholds: List[Dict] = None,
) -> Dict[str, Any]:
    """Create a stat panel with cyberpunk styling."""
    if thresholds is None:
        thresholds = [
            {"color": COLORS["green"], "value": None},
            {"color": COLORS["cyan"], "value": 0},
        ]

    return {
        "datasource": {"type": "prometheus", "uid": "PBFA97CFB590B2093"},
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": {"mode": "absolute", "steps": thresholds},
                "unit": unit,
            },
            "overrides": [],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": None,  # Will be assigned incrementally
        "options": {
            "colorMode": color_mode,
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "horizontal",
            "percentChangeColorMode": "standard",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "showPercentChange": False,
            "textMode": "value_and_name",
            "wideLayout": True,
        },
        "pluginVersion": "12.2.1",
        "targets": [
            {
                "datasource": {"type": "prometheus", "uid": "PBFA97CFB590B2093"},
                "expr": expr,
                "refId": "A",
            }
        ],
        "title": title,
        "type": "stat",
    }


def create_timeseries_panel(
    title: str,
    expr: str,
    x: int,
    y: int,
    w: int,
    h: int,
    legend_format: str = "{{alias}}",
    stacking: bool = False,
    fill_opacity: int = 10,
) -> Dict[str, Any]:
    """Create a timeseries panel with cyberpunk gradient."""
    return {
        "datasource": {"type": "prometheus", "uid": "PBFA97CFB590B2093"},
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisBorderShow": False,
                    "axisCenteredZero": False,
                    "axisColorMode": "text",
                    "axisLabel": "",
                    "axisPlacement": "auto",
                    "barAlignment": 0,
                    "barWidthFactor": 0.6,
                    "drawStyle": "line",
                    "fillOpacity": fill_opacity,
                    "gradientMode": "opacity",
                    "hideFrom": {"tooltip": False, "viz": False, "legend": False},
                    "insertNulls": False,
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "pointSize": 5,
                    "scaleDistribution": {"type": "linear"},
                    "showPoints": "never",
                    "spanNulls": False,
                    "stacking": {"group": "A", "mode": "normal" if stacking else "none"},
                    "thresholdsStyle": {"mode": "off"},
                },
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": COLORS["green"], "value": None},
                        {"color": COLORS["cyan"], "value": 0},
                    ],
                },
                "unit": "watt",
            },
            "overrides": [],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": None,
        "options": {
            "legend": {
                "calcs": ["mean", "max"],
                "displayMode": "table",
                "placement": "right",
                "showLegend": True,
            },
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        "pluginVersion": "12.2.1",
        "targets": [
            {
                "datasource": {"type": "prometheus", "uid": "PBFA97CFB590B2093"},
                "expr": expr,
                "legendFormat": legend_format,
                "refId": "A",
            }
        ],
        "title": title,
        "type": "timeseries",
    }


def generate_real_time_monitoring():
    """Generate the Real-Time Monitoring dashboard."""
    dashboard = create_base_dashboard(
        title="🌊 Real-Time Monitoring",
        uid="kasa-realtime",
        description="Live power consumption and cost monitoring with synthwave cyberpunk styling",
        tags=["kasa", "real-time", "monitoring", "cyberpunk"],
    )

    panels = []
    panel_id = 1

    # Row: Overview
    panels.append({
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0},
        "id": panel_id,
        "panels": [],
        "title": "⚡ SYSTEM OVERVIEW",
        "type": "row",
    })
    panel_id += 1

    # Total Power
    panel = create_stat_panel(
        title="⚡ Total Power Draw",
        expr="current_consumption:total",
        x=0, y=1, w=6, h=4,
        unit="watt",
        color_mode="background",
        thresholds=[
            {"color": COLORS["green"], "value": None},
            {"color": COLORS["cyan"], "value": 100},
            {"color": COLORS["yellow"], "value": 300},
            {"color": COLORS["orange"], "value": 500},
            {"color": COLORS["pink"], "value": 700},
        ],
    )
    panel["id"] = panel_id
    panels.append(panel)
    panel_id += 1

    # Total Cost Rate
    panel = create_stat_panel(
        title="💰 Current Cost Rate",
        expr="consumption_cost:total",
        x=6, y=1, w=6, h=4,
        unit="currencyUSD",
        color_mode="background",
        thresholds=[
            {"color": COLORS["green"], "value": None},
            {"color": COLORS["cyan"], "value": 0.2},
            {"color": COLORS["yellow"], "value": 0.4},
            {"color": COLORS["pink"], "value": 0.6},
        ],
    )
    panel["id"] = panel_id
    panels.append(panel)
    panel_id += 1

    # Current Energy Rate
    panel = create_stat_panel(
        title="⚡ Energy Rate ($/kWh)",
        expr='max(current_energy_rate) by (season, rate_class)',
        x=12, y=1, w=6, h=4,
        unit="currencyUSD",
        color_mode="value",
    )
    panel["targets"][0]["legendFormat"] = "{{season}} - {{rate_class}}"
    panel["id"] = panel_id
    panels.append(panel)
    panel_id += 1

    # Projected Daily Cost
    panel = create_stat_panel(
        title="📊 Projected Daily Cost",
        expr="consumption_cost:projected_day",
        x=18, y=1, w=6, h=4,
        unit="currencyUSD",
        color_mode="background",
        thresholds=[
            {"color": COLORS["green"], "value": None},
            {"color": COLORS["cyan"], "value": 5},
            {"color": COLORS["yellow"], "value": 10},
            {"color": COLORS["pink"], "value": 15},
        ],
    )
    panel["id"] = panel_id
    panels.append(panel)
    panel_id += 1

    # Row: Power Consumption
    panels.append({
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": 5},
        "id": panel_id,
        "panels": [],
        "title": "⚡ POWER CONSUMPTION",
        "type": "row",
    })
    panel_id += 1

    # Stacked Power Consumption
    panel = create_timeseries_panel(
        title="🌊 Power Consumption Over Time (Stacked)",
        expr='current_consumption:by_device{version=~"$version"}',
        x=0, y=6, w=24, h=8,
        stacking=True,
        fill_opacity=40,
    )
    panel["id"] = panel_id
    panels.append(panel)
    panel_id += 1

    dashboard["panels"] = panels
    return dashboard


# Generate all dashboards
def main():
    output_dir = Path("etc/grafana/dashboards")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate Real-Time Monitoring dashboard
    dashboard = generate_real_time_monitoring()
    output_file = output_dir / "real-time-monitoring.json"
    with open(output_file, "w") as f:
        json.dump(dashboard, f, indent=2)
    print(f"✅ Created: {output_file}")


if __name__ == "__main__":
    main()
