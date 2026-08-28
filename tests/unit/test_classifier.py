import pytest

from app.mijia.classifier import DeviceClassifier
from app.models.device import DeviceType


@pytest.mark.parametrize(
    ("model", "properties", "expected"),
    [
        ("unknown.device.v1", ["on", "brightness"], DeviceType.LIGHT),
        ("unknown.device.v1", ["on", "target-temperature", "fan-level"], DeviceType.AIR_CONDITIONER),
        ("unknown.device.v1", ["on", "horizontal-swing"], DeviceType.FAN),
        ("cuco.plug.v3", ["on"], DeviceType.PLUG),
        ("miaomiaoce.sensor_ht.t9", ["temperature", "humidity"], DeviceType.SENSOR),
        ("xiaomi.vacuum.d110ch", ["filter-life-level"], DeviceType.VACUUM),
        ("xiaomi.humidifier.p3", ["filter-life-level"], DeviceType.HUMIDIFIER),
        ("xiaomi.oven.p1", ["target-temperature", "fan-level"], DeviceType.OTHER),
        ("xiaomi.wifispeaker.lx06", ["temperature"], DeviceType.OTHER),
        ("unknown.device.v1", ["on"], DeviceType.OTHER),
    ],
)
def test_capability_and_model_classification(model, properties, expected):
    assert DeviceClassifier().classify(model, properties) is expected
