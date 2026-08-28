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

