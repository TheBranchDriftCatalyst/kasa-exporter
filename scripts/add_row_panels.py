#!/usr/bin/env python3
"""Add collapsible row panels to organize the Grafana dashboard."""

import json
from pathlib import Path

dashboard_path = Path("etc/grafana/dashboards/power-analytics.json")

with dashboard_path.open() as f:
    dashboard = json.load(f)

# Define sections with their Y positions and which panels belong to them
sections = [
    {
        "id": 100,
        "title": "📊 Overview & Real-time Monitoring",
        "y": 0,
        "collapsed": False,
        "panel_ids": [13, 10, 2, 6, 8, 9, 7, 12, 11],  # All panels from y=0 to y=28
    },
    {
        "id": 101,
        "title": "📈 Analytics & Trends",
        "y": 37,
        "collapsed": True,
        "panel_ids": [14, 16, 17, 15],  # Panels from y=36 to y=44
    },
    {
        "id": 102,
        "title": "🔧 Device Health & Status",
        "y": 55,
        "collapsed": True,
        "panel_ids": [18, 19, 20],  # Panels from y=54 to y=62
    },
    {
        "id": 103,
        "title": "🔋 Battery Runtime Analysis",
        "y": 64,
        "collapsed": True,
        "panel_ids": [21, 22, 23, 24],  # Battery panels from y=62 onwards
    },
]


# Create row panel template
def create_row_panel(section):
    return {
        "collapsed": section["collapsed"],
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": section["y"]},
        "id": section["id"],
        "panels": [],
        "title": section["title"],
        "type": "row",
    }


# Adjust Y positions for panels within each section
def adjust_panel_positions(panels, sections):
    """Adjust panel Y positions to account for row headers."""
    new_panels = []

    for section in sections:
        # Add row panel
        row_panel = create_row_panel(section)
        new_panels.append(row_panel)

        # Get panels for this section
        section_panels = [p for p in panels if p["id"] in section["panel_ids"]]

        # Sort by original Y position
        section_panels.sort(key=lambda p: p["gridPos"]["y"])

        # Adjust Y positions relative to row
        y_offset = section["y"] + 1  # Start 1 row below the section header
        min_y = min(p["gridPos"]["y"] for p in section_panels) if section_panels else 0

        for panel in section_panels:
            # Adjust Y position relative to section start
            panel["gridPos"]["y"] = panel["gridPos"]["y"] - min_y + y_offset
            new_panels.append(panel)

    return new_panels


# Get all existing panels (excluding any existing row panels)
panels = [p for p in dashboard["panels"] if p.get("type") != "row"]

# Adjust positions and add row panels
dashboard["panels"] = adjust_panel_positions(panels, sections)

# Write back to file
with dashboard_path.open("w") as f:
    json.dump(dashboard, f, indent=2)

print("✅ Added collapsible row panels to dashboard")
print(f"   - {len(sections)} sections created")
print(f"   - {len(panels)} panels organized")
