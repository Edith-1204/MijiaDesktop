from argparse import Namespace

import pytest

from scripts.mijia_poc import json_value, require_confirmation


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [("true", True), ("42", 42), ('"text"', "text"), ("plain-text", "plain-text")],
)
def test_json_value(raw_value, expected):
    assert json_value(raw_value) == expected


def test_real_device_mutation_requires_explicit_confirmation():
    with pytest.raises(ValueError, match="--yes"):
        require_confirmation(Namespace(yes=False), "设置 Property")

