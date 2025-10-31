#!/usr/bin/env python3
"""
Convert Grafana v2beta1 dashboard format to classic JSON format for provisioning.
"""
import json
import sys
from pathlib import Path


def convert_panel_query(v2_query):
    """Convert v2beta1 query spec to classic format."""
    query_spec = v2_query.get("spec", {})
    query_inner = query_spec.get("query", {})
    query_data = query_inner.get("spec", {})

    classic_query = {
        "refId": query_spec.get("refId", "A"),
        "expr": query_data.get("expr", ""),
        "legendFormat": query_data.get("legendFormat", ""),
        "range": query_data.get("range", True),
        "instant": query_data.get("instant", False),
        "editorMode": query_data.get("editorMode", "code"),
    }

    # Add datasource
    if "datasource" in query_inner:
        datasource = query_inner["datasource"]
        if isinstance(datasource, dict):
            classic_query["datasource"] = {
                "type": "prometheus",
                "uid": datasource.get("name", "")
            }

    # Clean up None/empty values
    return {k: v for k, v in classic_query.items() if v not in [None, "", {}]}


def convert_panel(panel_id, v2_panel):
    """Convert v2beta1 panel to classic format."""
    spec = v2_panel.get("spec", {})
    viz_config = spec.get("vizConfig", {})
    viz_spec = viz_config.get("spec", {})
    field_config = viz_spec.get("fieldConfig", {})
    options = viz_spec.get("options", {})

    # Get queries
    data_spec = spec.get("data", {}).get("spec", {})
    queries = data_spec.get("queries", [])
    targets = [convert_panel_query(q) for q in queries]
    transformations = data_spec.get("transformations", [])

    # Build classic panel
    classic_panel = {
        "id": spec.get("id", panel_id),
        "title": spec.get("title", ""),
        "type": viz_config.get("group", "timeseries"),
        "targets": targets,
        "description": spec.get("description", ""),
        "fieldConfig": field_config,
        "options": options,
        "links": spec.get("links", []),
        "transformations": transformations,
    }

    # Add gridPos if layout exists
    if "layout" in spec:
        layout = spec["layout"]
        classic_panel["gridPos"] = {
            "x": layout.get("x", 0),
            "y": layout.get("y", 0),
            "w": layout.get("w", 24),
            "h": layout.get("h", 9),
        }

    # Clean up
    return {k: v for k, v in classic_panel.items() if v not in [None, "", [], {}]}


def convert_row(row_id, v2_row):
    """Convert v2beta1 row to classic format."""
    spec = v2_row.get("spec", {})

    classic_row = {
        "id": spec.get("id", row_id),
        "title": spec.get("title", ""),
        "type": "row",
        "collapsed": spec.get("collapsed", False),
        "panels": [],
    }

    # Add gridPos if layout exists
    if "layout" in spec:
        layout = spec["layout"]
        classic_row["gridPos"] = {
            "x": layout.get("x", 0),
            "y": layout.get("y", 0),
            "w": layout.get("w", 24),
            "h": layout.get("h", 1),
        }

    return {k: v for k, v in classic_row.items() if v not in [None, "", [], {}]}


def convert_variable(v2_var):
    """Convert v2beta1 variable to classic templating format."""
    spec = v2_var.get("spec", {})
    query_spec = spec.get("query", {}).get("spec", {}) if spec.get("query") else {}

    var_type = v2_var.get("kind", "").replace("Variable", "").lower()
    if not var_type:
        var_type = "query"

    classic_var = {
        "name": spec.get("name", ""),
        "type": var_type,
        "label": spec.get("label", ""),
        "hide": 2 if spec.get("hide") == "HIDE_VARIABLE" else 0,
        "multi": spec.get("multi", False),
        "includeAll": spec.get("includeAll", False),
        "allValue": spec.get("allValue", ""),
        "current": spec.get("current", {}),
        "options": spec.get("options", []),
    }

    # Add query-specific fields
    if var_type == "query":
        classic_var.update({
            "query": query_spec.get("query", ""),
            "regex": query_spec.get("regex", ""),
            "refresh": query_spec.get("refresh", 1),
        })
        if "datasource" in spec.get("query", {}):
            ds = spec["query"]["datasource"]
            classic_var["datasource"] = {
                "type": "prometheus",
                "uid": ds.get("name", "") if isinstance(ds, dict) else ds
            }

    return {k: v for k, v in classic_var.items() if v not in [None, "", [], {}]}


def convert_dashboard(v2_dashboard):
    """Convert v2beta1 dashboard to classic JSON format."""
    metadata = v2_dashboard.get("metadata", {})
    spec = v2_dashboard.get("spec", {})

    # Build panels list from elements
    panels = []
    elements = spec.get("elements", {})

    # Sort by ID to maintain order
    for elem_key in sorted(elements.keys(), key=lambda x: int(x.split("-")[-1]) if x.split("-")[-1].isdigit() else 0):
        elem = elements[elem_key]
        elem_kind = elem.get("kind", "")

        if elem_kind == "Panel":
            panel_id = int(elem_key.split("-")[-1]) if elem_key.split("-")[-1].isdigit() else len(panels)
            panels.append(convert_panel(panel_id, elem))
        elif elem_kind == "Row":
            row_id = int(elem_key.split("-")[-1]) if elem_key.split("-")[-1].isdigit() else len(panels)
            panels.append(convert_row(row_id, elem))

    # Convert variables
    variables = []
    for var in spec.get("variables", []):
        variables.append(convert_variable(var))

    # Build classic dashboard
    classic = {
        "uid": metadata.get("uid", ""),
        "title": spec.get("title", "Power Analytics Dashboard"),
        "description": spec.get("description", ""),
        "tags": spec.get("tags", []),
        "timezone": "browser",
        "editable": spec.get("editable", True),
        "graphTooltip": 1 if spec.get("cursorSync") == "Tooltip" else 0,
        "panels": panels,
        "schemaVersion": 39,
        "version": 1,
        "refresh": spec.get("refresh", ""),
        "time": {
            "from": spec.get("timeSettings", {}).get("from", "now-6h"),
            "to": spec.get("timeSettings", {}).get("to", "now")
        },
        "timepicker": {
            "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"],
            "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
        },
        "templating": {
            "list": variables
        },
        "annotations": {
            "list": []
        },
        "links": spec.get("links", []),
    }

    # Clean up
    return {k: v for k, v in classic.items() if v not in [None, "", [], {}]}


def main():
    if len(sys.argv) < 2:
        print("Usage: convert_dashboard_v2_to_classic.py <input.json> [output.json]")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else input_file.with_suffix(".classic.json")

    print(f"Reading v2beta1 dashboard from {input_file}...")
    with open(input_file) as f:
        v2_dashboard = json.load(f)

    if v2_dashboard.get("apiVersion") != "dashboard.grafana.app/v2beta1":
        print(f"Warning: Input file is not v2beta1 format (found: {v2_dashboard.get('apiVersion')})")
        if v2_dashboard.get("apiVersion") is None and "panels" in v2_dashboard:
            print("This already appears to be classic format!")
            sys.exit(0)

    print("Converting to classic format...")
    classic_dashboard = convert_dashboard(v2_dashboard)

    print(f"Writing classic dashboard to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(classic_dashboard, f, indent=2)

    print(f"✓ Conversion complete!")
    print(f"  - Panels: {len(classic_dashboard.get('panels', []))}")
    print(f"  - Variables: {len(classic_dashboard.get('templating', {}).get('list', []))}")
    print(f"  - Title: {classic_dashboard.get('title', 'N/A')}")


if __name__ == "__main__":
    main()
