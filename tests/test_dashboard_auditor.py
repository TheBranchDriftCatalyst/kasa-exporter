import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "dashboard_auditor", Path(__file__).parents[1] / "scripts/audit_dashboard_queries.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def vector(value="12", labels=None):
    return {
        "status": "success",
        "data": {"resultType": "vector", "result": [{"metric": labels or {}, "value": [1, value]}]},
    }


@pytest.mark.parametrize("value", ["NaN", "+Inf", "-Inf"])
def test_nonfinite_values_fail(value):
    assert audit.check_result(vector(value), instant=True)["status"] == "FAIL"


def test_empty_is_not_a_pass():
    assert (
        audit.check_result(
            {"status": "success", "data": {"resultType": "vector", "result": []}}, instant=True
        )["status"]
        == "EMPTY"
    )


def test_missing_identity_and_wrong_result_shape_fail():
    assert (
        audit.check_result(vector(), instant=True, required_labels=["device_id"])["status"]
        == "FAIL"
    )
    assert audit.check_result(vector(), instant=False)["status"] == "FAIL"
    assert (
        audit.check_result(
            vector("50", {"device_id": "a"}),
            instant=True,
            required_labels=["device_id"],
            minimum=0,
            maximum=100,
        )["status"]
        == "PASS"
    )
    assert audit.check_result(vector("101"), instant=True, maximum=100)["status"] == "FAIL"


def test_duplicate_label_sets_fail():
    data = vector()
    data["data"]["result"] *= 2
    assert audit.check_result(data, instant=True)["status"] == "FAIL"


def test_nested_collapsed_rows_are_included():
    assert [p["id"] for p in audit.panels([{"id": 1, "panels": [{"id": 2}]}])] == [1, 2]


def test_variables_are_explicit_and_regex_escaped():
    assert (
        audit.interpolate('x{alias=~"${device}"}', {"device": "plug.a"}, 0, 3600, 30, {"device"})
        == r'x{alias=~"plug\\.a"}'
    )
    assert audit.interpolate("${__from:date:seconds}+$__range_s", {}, 100, 3700, 30) == "100+3600"
    with pytest.raises(ValueError, match="unresolved"):
        audit.interpolate("$missing", {}, 0, 3600, 30)


def test_generic_regex_formatter_differs_from_prometheus_default():
    assert (
        audit.interpolate('x{version=~"${version:regex}"}', {"version": "1.0.0"}, 0, 3600, 30)
        == r'x{version=~"1\.0\.0"}'
    )
    assert (
        audit.interpolate(
            'x{alias="${baseline_device}"}', {"baseline_device": 'plug "one"'}, 0, 3600, 30
        )
        == r'x{alias="plug \"one\""}'
    )
