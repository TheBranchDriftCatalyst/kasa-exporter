from unittest.mock import AsyncMock, patch

import pytest
from kasa.deviceconfig import DeviceEncryptionType
from prometheus_client import CollectorRegistry

from kasa_exporter.routines.device_registry import DeviceRegistry


@pytest.mark.asyncio
async def test_unsupported_responses_are_visible_without_faking_readiness(monkeypatch):
    registry = CollectorRegistry()
    devices = DeviceRegistry(registry)
    monkeypatch.setenv("KASA_DISCOVERY_TARGET", "192.168.1.255")

    async def discover(**kwargs):
        assert kwargs["target"] == "192.168.1.255"
        await kwargs["on_unsupported"](RuntimeError("unsupported protocol"))
        return {}

    with patch("kasa_exporter.routines.device_registry.Discover.discover", side_effect=discover):
        assert await devices.discover_devices(None, {}) == {}
    assert registry.get_sample_value("kasa_discovery_unsupported_devices") == 1
    assert registry.get_sample_value("device_registry_total_devices") == 0
    assert registry.get_sample_value("kasa_discovery_last_success_timestamp_seconds") > 0

    with patch(
        "kasa_exporter.routines.device_registry.Discover.discover", new=AsyncMock(return_value={})
    ):
        await devices.discover_devices(None, {})
    assert registry.get_sample_value("kasa_discovery_unsupported_devices") == 0


def test_dependency_supports_tpap():
    assert DeviceEncryptionType("TPAP").value == "TPAP"
