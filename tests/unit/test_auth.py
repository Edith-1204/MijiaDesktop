import json
import os

import pytest

from app.mijia.auth import WindowsCredentialStore


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI is required")
def test_credentials_round_trip_through_dpapi(tmp_path):
    protected_path = tmp_path / "auth.dat"
    original = {"serviceToken": "test-secret", "userId": "test-user"}

    first_store = WindowsCredentialStore(protected_path)
    first_store.prepare().write_text(json.dumps(original), encoding="utf-8")
    first_store.persist()
    first_store.close()

    assert protected_path.read_bytes() != json.dumps(original).encode()

    second_store = WindowsCredentialStore(protected_path)
    restored = json.loads(second_store.prepare().read_text(encoding="utf-8"))
    second_store.close()

    assert restored == original


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI is required")
def test_clear_recreates_private_working_directory(tmp_path):
    store = WindowsCredentialStore(tmp_path / "auth.dat")
    first_path = store.prepare()
    first_path.write_text("temporary", encoding="utf-8")

    store.clear()
    second_path = store.prepare()

    assert second_path != first_path
    assert not first_path.exists()
    assert second_path.parent.is_dir()
    store.close()
