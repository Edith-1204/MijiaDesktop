from app.mijia.parser import extract_property_values, parse_action, parse_capability


def test_parse_ranged_capability():
    capability = parse_capability(
        {
            "name": "brightness",
            "description": "Brightness / 亮度",
            "type": "uint",
            "rw": "rw",
            "range": [1, 100, 1],
            "method": {"siid": 2, "piid": 2},
        },
        70,
    )

    assert capability.readable and capability.writable
    assert capability.value == 70
    assert (capability.min_value, capability.max_value, capability.step) == (1, 100, 1)
    assert (capability.siid, capability.piid) == (2, 2)


def test_parse_enum_and_action():
    capability = parse_capability(
        {
            "name": "mode",
            "type": "uint",
            "rw": "rw",
            "value-list": [{"value": 1, "description": "Auto", "desc_zh_cn": "自动"}],
            "method": {"siid": 2, "piid": 3},
        }
    )
    action = parse_action(
        {"name": "toggle", "description": "Toggle", "method": {"siid": 2, "aiid": 1}}
    )

    assert capability.enum_values == {1: "自动"}
    assert (action.name, action.siid, action.aiid) == ("toggle", 2, 1)


def test_extract_embedded_json_property_values():
    assert extract_property_values({"prop": '{"on": true, "color_temperature": 4000}'}) == {
        "on": True,
        "color-temperature": 4000,
    }

