import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
DASHBOARDS = ROOT / "etc/grafana/provisioning/dashboards/dashboards"


def test_local_and_cluster_recording_rules_are_identical():
    local = yaml.safe_load((ROOT / "etc/prometheus/rules/kasa_rules.yml").read_text())
    cluster = yaml.safe_load((ROOT / "k8s/prometheusrule.yaml").read_text())
    assert local["groups"] == cluster["spec"]["groups"]
    assert all(g["interval"] == "30s" for g in local["groups"])


def test_every_visualization_has_reviewed_query_contracts():
    count = 0
    for path in DASHBOARDS.glob("*.json"):
        dashboard = json.loads(path.read_text())
        ids = []
        for panel in dashboard["panels"]:
            ids.append(panel["id"])
            if panel["type"] in ("text", "row"):
                continue
            count += 1
            assert panel["targets"], (path, panel["id"])
            for target in panel["targets"]:
                assert target["expr"].strip(), (path, panel["id"])
                if panel["id"] != 9901:
                    assert "audit" in target, (path, panel["id"])
                assert not re.search(
                    r"\b(?:increase|rate)\(consumption_(?:cost|today|this_month)", target["expr"]
                )
            for mapping in panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", []):
                assert not (
                    mapping["type"] == "special" and mapping["options"].get("match") == "null"
                ), "Missing data must not map to healthy"
        assert len(ids) == len(set(ids))
    assert count == 151  # 145 original query panels plus six freshness panels
