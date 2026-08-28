from app.core.device_manager import DeviceManager
from app.storage.spec_cache import DeviceSpecCache
from tests.unit.test_device_manager import FakeAdapter


def test_cold_start_displays_devices_before_spec_enrichment(tmp_path):
    adapter = FakeAdapter()
    cache = DeviceSpecCache(tmp_path / "specs")
    manager = DeviceManager(adapter, spec_cache=cache)

    provisional = manager.sync_devices_fast()[0]

    assert provisional.properties == {}
    assert manager.needs_enrichment
    assert not any(call[0] == "get_device_spec" for call in adapter.calls)

    enriched = manager.enrich_devices()[0]
    assert "on" in enriched.properties
    assert not manager.needs_enrichment


def test_warm_start_uses_persistent_spec_without_loader_call(tmp_path):
    cache = DeviceSpecCache(tmp_path / "specs")
    first = DeviceManager(FakeAdapter(), spec_cache=cache)
    first.sync_devices_fast()
    first.enrich_devices()

    adapter = FakeAdapter()
    second = DeviceManager(adapter, spec_cache=cache)
    device = second.sync_devices_fast()[0]

    assert "on" in device.properties
    assert not second.needs_enrichment
    assert not any(call[0] == "get_device_spec" for call in adapter.calls)
