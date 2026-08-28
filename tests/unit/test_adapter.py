from pathlib import Path

import pytest

from app.core.exceptions import DeviceOfflineError, PropertyWriteError
from app.mijia.adapter import MijiaAdapter


class FakeAPI:
    auth_data_path = Path("test-auth.json")
    available = True

    def __init__(self):
        self.calls = []

    def login(self):
        self.calls.append(("login",))
        return {"serviceToken": "must-not-leak"}

    def _get_qr_login_data(self):
        self.calls.append(("get_qr_login_data",))
        return {"qr": "https://example.test/qr.png", "lp": "poll-url"}

    def _complete_qr_login(self, login_data):
        self.calls.append(("complete_qr_login", login_data))
        return {"serviceToken": "must-not-leak"}

    def get_devices_list(self):
        self.calls.append(("get_devices_list",))
        return [{"did": "device-1", "name": "台灯", "model": "test.light.v1"}]

    def get_devices_prop(self, data):
        self.calls.append(("get_devices_prop", data))
        return {**data, "code": 0, "value": False}

    def set_devices_prop(self, data):
        self.calls.append(("set_devices_prop", data))
        return {**data, "code": 0}

    def run_action(self, data):
        self.calls.append(("run_action", data))
        return {**data, "code": 0}


def test_adapter_exposes_complete_poc_chain(tmp_path):
    api = FakeAPI()
    adapter = MijiaAdapter(
        api_client=api,
        qr_fetcher=lambda _url: b"\x89PNG\r\n\x1a\nqr-data",
        qr_directory=tmp_path,
    )

    seen_paths = []
    adapter.login(seen_paths.append)
    assert seen_paths == [tmp_path / "mijia-login-qr.png"]
    assert seen_paths[0].read_bytes().endswith(b"qr-data")
    assert adapter.is_authenticated()
    assert adapter.get_devices()[0]["model"] == "test.light.v1"
    assert adapter.get_properties({"did": "device-1", "siid": 2, "piid": 1})["value"] is False
    assert adapter.set_property("device-1", 2, 1, True)["code"] == 0
    assert adapter.run_action("device-1", 2, 1, [1])["code"] == 0

    assert [call[0] for call in api.calls] == [
        "get_qr_login_data",
        "complete_qr_login",
        "get_devices_list",
        "get_devices_prop",
        "set_devices_prop",
        "run_action",
    ]
    adapter.close()
    assert not seen_paths[0].exists()


def test_existing_session_skips_qr_download(tmp_path):
    api = FakeAPI()
    api._get_qr_login_data = lambda: {"refreshed": True}
    fetched = []
    adapter = MijiaAdapter(
        api_client=api,
        qr_fetcher=lambda url: fetched.append(url),
        qr_directory=tmp_path,
    )

    adapter.login()

    assert fetched == []
    assert not (tmp_path / "mijia-login-qr.png").exists()


def test_invalid_qr_response_is_rejected(tmp_path):
    adapter = MijiaAdapter(
        api_client=FakeAPI(),
        qr_fetcher=lambda _url: b"not-an-image",
        qr_directory=tmp_path,
    )

    with pytest.raises(Exception, match="无法生成米家登录二维码"):
        adapter.begin_login()


def test_adapter_loads_device_spec_through_boundary():
    adapter = MijiaAdapter(
        api_client=FakeAPI(),
        spec_loader=lambda model, cache: {"model": model, "cache": str(cache)},
    )

    result = adapter.get_device_spec("test.light.v1")

    assert result == {"model": "test.light.v1", "cache": "."}


def test_nonzero_property_result_becomes_application_error():
    api = FakeAPI()
    api.set_devices_prop = lambda data: {**data, "code": -704030023}
    adapter = MijiaAdapter(api_client=api)

    with pytest.raises(PropertyWriteError, match="错误码 -704030023"):
        adapter.set_property("device-1", 2, 1, True)


def test_offline_result_becomes_device_offline_error():
    api = FakeAPI()
    api.get_devices_prop = lambda data: {**data, "code": -704042011}
    adapter = MijiaAdapter(api_client=api)

    with pytest.raises(DeviceOfflineError):
        adapter.get_properties({"did": "device-1", "siid": 2, "piid": 1})
