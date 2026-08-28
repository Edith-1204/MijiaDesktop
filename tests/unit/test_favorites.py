from app.core.device_manager import DeviceManager
from app.storage.repository import FavoritesRepository
from tests.unit.test_device_manager import FakeAdapter


def test_favorites_repository_persists_changes(tmp_path):
    path = tmp_path / "state.db"
    repository = FavoritesRepository(path)
    repository.set_favorite("device-1", True)
    repository.close()

    reopened = FavoritesRepository(path)
    assert reopened.list_dids() == {"device-1"}
    reopened.set_favorite("device-1", False)
    assert reopened.list_dids() == set()
    reopened.close()


def test_device_manager_applies_and_updates_persisted_favorite(tmp_path):
    repository = FavoritesRepository(tmp_path / "state.db")
    repository.set_favorite("light-1", True)
    manager = DeviceManager(FakeAdapter(), favorites_repository=repository)

    device = manager.sync_devices()[0]
    assert device.favorite is True

    manager.set_favorite(device.did, False)
    assert device.favorite is False
    assert repository.list_dids() == set()
    repository.close()
