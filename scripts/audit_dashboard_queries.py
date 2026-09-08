#!/usr/bin/env python3
"""Query every target in Grafana JSON and report errors, shape and numeric validity.

This validates observed results and explicit contracts, not arbitrary mathematical
correctness. Formula correctness also requires reviewed units and promtool fixtures.
No writes to Grafana, Prometheus or devices. Missing data is never a passing result.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def api(base, path, params=None):
    url = base.rstrip("/") + path + ("?" + urlencode(params) if params else "")
    try:
        with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=45) as response:
            return json.load(response)
    except HTTPError as error:
        return {"status": "error", "error": f"HTTP {error.code}: {error.read().decode()[:1000]}"}


def panels(items):
    for panel in items:
        yield panel
        yield from panels(panel.get("panels", []))


def interpolate(expression, values, start, end, step):
    macros = {
        "__range_s": str(end - start),
        "__range_ms": str((end - start) * 1000),
        "__range": f"{end - start}s",
        "__interval": f"{step}s",
        "__interval_ms": str(step * 1000),
        "__rate_interval": f"{max(120, step * 4)}s",
        "__from": str(start * 1000),
        "__to": str(end * 1000),
    }
    expression = expression.replace("${__from:date:seconds}", str(start)).replace(
        "${__to:date:seconds}", str(end)
    )

    def replace(match):
        name, fmt = (match.group(1) or match.group(3)), match.group(2)
        if name in macros:
            return macros[name]
        if name not in values:
            raise ValueError(f"unresolved dashboard variable {name}")
        value = values[name]
        if isinstance(value, list):
            value = "(" + "|".join(re.escape(str(v)).replace(r"\ ", " ") for v in value) + ")"
            return json.dumps(value)[1:-1]
        if fmt == "regex" and value != ".*":
            return json.dumps(re.escape(str(value)).replace(r"\ ", " "))[1:-1]
        return str(value)

    return re.sub(r"\$\{([A-Za-z_]\w*)(?::([^}]+))?\}|\$([A-Za-z_]\w*)", replace, expression)


def resolve_variables(dashboard, base, overrides, start, end, step):
    values, findings = {}, []
    for var in dashboard.get("templating", {}).get("list", []):
        name = var["name"]
        current = var.get("current", {}).get("value")
        if name in overrides:
            values[name] = overrides[name]
            continue
        if var["type"] == "datasource":
            values[name] = "mimir"
            continue
        if var.get("includeAll") and current in (None, "", "All", "$__all"):
            values[name] = var.get("allValue") or ".*"
        elif current not in (None, "", "All", "$__all", []):
            values[name] = current
        elif var["type"] in ("custom", "textbox", "constant", "interval"):
            values[name] = str(var.get("query", "")).split(",")[0].strip()
        if var["type"] != "query":
            continue
        raw = var.get("query", "")
        if isinstance(raw, dict):
            raw = raw.get("query", "")
        match = re.fullmatch(r"label_values\((.*),\s*(\w+)\)", raw)
        if not match:
            findings.append(
                {
                    "variable": name,
                    "status": "REVIEW",
                    "reason": "unsupported variable query helper",
                }
            )
            continue
        selector, label = match.groups()
        try:
            selector = interpolate(selector, values, start, end, step)
            result = api(
                base, "/api/v1/series", {"match[]": selector, "start": end - 300, "end": end}
            )
            if result.get("status") != "success":
                raise ValueError(result.get("error"))
            options = sorted({item[label] for item in result["data"] if label in item})
            findings.append(
                {"variable": name, "status": "PASS" if options else "EMPTY", "options": options}
            )
            if name not in values:
                values[name] = options[0] if options else "__missing_device__"
        except Exception as error:
            findings.append({"variable": name, "status": "FAIL", "reason": str(error)})
    return values, findings


def check_result(data, *, instant, required_labels=(), minimum=None, maximum=None):  # noqa: PLR0911
    if data.get("status") != "success":
        return {"status": "FAIL", "reason": data.get("error", "backend rejected query")}
    result = data["data"]
    kind = result.get("resultType")
    allowed = ("vector", "scalar") if instant else ("matrix",)
    if kind not in allowed:
        return {"status": "FAIL", "reason": f"expected {allowed}, received {kind}"}
    rows = result.get("result", [])
    if not rows:
        return {"status": "EMPTY", "reason": "no observed data", "series": 0}
    if kind == "scalar":
        rows = [{"metric": {}, "value": rows}]
    numbers, labels, points = [], set(), 0
    for row in rows:
        missing = set(required_labels) - set(row.get("metric", {}))
        if missing:
            return {"status": "FAIL", "reason": f"missing required labels: {sorted(missing)}"}
        identity = tuple(sorted(row.get("metric", {}).items()))
        if identity in labels:
            return {"status": "FAIL", "reason": "duplicate label set"}
        labels.add(identity)
        samples = row.get("values", [row.get("value")])
        for sample in samples:
            if not sample or len(sample) != 2:
                return {"status": "FAIL", "reason": "invalid sample shape"}
            value = float(sample[1])
            points += 1
            if not math.isfinite(value):
                return {"status": "FAIL", "reason": "NaN or infinity in result"}
            if minimum is not None and value < minimum - 1e-6:
                return {"status": "FAIL", "reason": f"value {value} below {minimum}"}
            if maximum is not None and value > maximum + 1e-6:
                return {"status": "FAIL", "reason": f"value {value} above {maximum}"}
            numbers.append(value)
    return {
        "status": "PASS",
        "series": len(rows),
        "samples": points,
        "labels": sorted({k for row in rows for k in row.get("metric", {})}),
        "min": min(numbers),
        "max": max(numbers),
        "result_type": kind,
    }


def audit_target(item):
    panel, target, values, options = item
    output = {
        "panel_id": panel["id"],
        "title": panel.get("title"),
        "ref": target.get("refId"),
        "panel_type": panel["type"],
        "hidden": bool(target.get("hide")),
    }
    try:
        raw = target.get("expr", "")
        if not raw.strip():
            raise ValueError("empty target expression")
        expr = interpolate(raw, values, options.start, options.end, options.step)
        output["query"] = expr
        if re.search(r"\b(?:increase|rate)\(consumption_(?:cost|today|this_month)", expr):
            raise ValueError("counter function applied to an exporter gauge")
        instant = bool(target.get("instant"))
        path = "/api/v1/query" if instant else "/api/v1/query_range"
        params = (
            {"query": expr, "time": options.end}
            if instant
            else {"query": expr, "start": options.start, "end": options.end, "step": options.step}
        )
        result = api(options.prometheus_url, path, params)
        contract = target.get("audit", {})
        output.update(
            check_result(
                result,
                instant=instant,
                required_labels=contract.get("required_labels", []),
                minimum=contract.get("min"),
                maximum=contract.get("max"),
            )
        )
        output["contract"] = contract
        output["unit"] = panel.get("fieldConfig", {}).get("defaults", {}).get("unit")
        if result.get("warnings"):
            output["warnings"] = result["warnings"]
    except Exception as error:
        output.update(status="FAIL", reason=str(error))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dashboards", type=Path, default=ROOT / "etc/grafana/provisioning/dashboards/dashboards"
    )
    parser.add_argument(
        "--prometheus-url", default="http://grafana.talos00/api/datasources/proxy/uid/mimir"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hours", type=int, default=6)
    parser.add_argument("--step", type=int, default=60)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--var", action="append", default=[])
    args = parser.parse_args()
    args.end = int(time.time())
    args.start = args.end - args.hours * 3600
    if args.hours <= 0 or args.step <= 0 or args.workers not in range(1, 9):
        parser.error("positive duration/step and 1..8 workers required")
    overrides = dict(v.split("=", 1) for v in args.var)
    results = []
    for file in sorted(args.dashboards.glob("*.json")):
        dashboard = json.loads(file.read_text())
        variables, variable_checks = resolve_variables(
            dashboard, args.prometheus_url, overrides, args.start, args.end, args.step
        )
        all_panels = list(panels(dashboard.get("panels", [])))
        jobs = [
            (p, t, variables, args)
            for p in all_panels
            for t in p.get("targets", [])
            if p["type"] not in ("row", "text")
        ]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            checks = list(pool.map(audit_target, jobs))
        item = {
            "file": str(file),
            "uid": dashboard.get("uid"),
            "title": dashboard.get("title"),
            "variables": variables,
            "variable_checks": variable_checks,
            "panels": len(all_panels),
            "query_checks": checks,
            "non_query_panels": [
                {"id": p["id"], "type": p["type"]}
                for p in all_panels
                if p["type"] in ("text", "row")
            ],
        }
        results.append(item)
        print(
            dashboard.get("uid"),
            {
                state: sum(c["status"] == state for c in checks)
                for state in ("PASS", "EMPTY", "FAIL")
            },
            flush=True,
        )
    rules = api(args.prometheus_url, "/api/v1/rules")
    groups = [
        g for g in rules.get("data", {}).get("groups", []) if "kasa" in g.get("name", "").lower()
    ]
    rule_checks = [
        {
            "name": r.get("name"),
            "health": r.get("health"),
            "lastError": r.get("lastError"),
            "type": r.get("type"),
            "state": r.get("state"),
        }
        for g in groups
        for r in g.get("rules", [])
    ]
    scrape = api(args.prometheus_url, "/api/v1/query", {"query": 'up{job="kasa-exporter"}'})
    fresh = api(
        args.prometheus_url, "/api/v1/query", {"query": 'kasa_fresh_devices{job="kasa-exporter"}'}
    )
    age = api(
        args.prometheus_url,
        "/api/v1/query",
        {"query": 'time() - kasa_last_measurement_timestamp_seconds{job="kasa-exporter"}'},
    )
    unsupported = api(
        args.prometheus_url,
        "/api/v1/query",
        {"query": 'kasa_discovery_unsupported_devices{job="kasa-exporter"}'},
    )
    health_checks = {
        "scrape": check_result(scrape, instant=True, minimum=1, maximum=1),
        "freshness": check_result(fresh, instant=True, minimum=1),
        "measurement_age": check_result(age, instant=True, minimum=0, maximum=90),
        "unsupported_devices": check_result(unsupported, instant=True, minimum=0, maximum=0),
    }
    report = {
        "generated_at": args.end,
        "window_seconds": args.end - args.start,
        "dashboards": results,
        "rules": rule_checks,
        "scrape": scrape,
        "freshness": fresh,
        "health_checks": health_checks,
        "limitations": [
            "Query success does not prove units or semantics; use formula review and rule fixtures.",
            "Empty histories are reported, never silently counted as passing.",
            "Grafana transformations and visual rendering require the browser audit.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    failed = (
        any(c["status"] != "PASS" for d in results for c in d["query_checks"])
        or not results
        or any(c["status"] != "PASS" for d in results for c in d["variable_checks"])
        or any(c["status"] != "PASS" for c in health_checks.values())
        or not rule_checks
        or any(r["health"] != "ok" or r["state"] == "firing" for r in rule_checks)
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
