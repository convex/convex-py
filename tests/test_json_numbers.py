import json
from typing import Any, Dict

import pytest
import requests

from convex import ConvexInt64, json_to_convex
from convex.http_client import ConvexHttpClient


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, 0.0),
        (1, 1.0),
        (-1, -1.0),
        (2**53, float(2**53)),
        (2**60, float(2**60)),
        ({"count": 2, "nested": [3, True]}, {"count": 2.0, "nested": [3.0, True]}),
    ],
)
def test_json_whole_numbers_become_float64(value: Any, expected: Any) -> None:
    decoded = json_to_convex(value)
    assert decoded == expected
    if isinstance(decoded, dict):
        assert type(decoded["count"]) is float
        nested = decoded["nested"]
        assert isinstance(nested, list)
        assert type(nested[0]) is float
        assert nested[1] is True
    else:
        assert type(decoded) is float


@pytest.mark.parametrize("method", ["query", "mutation", "action"])
@pytest.mark.parametrize("value", [1, {"count": 2, "nested": [3, True]}])
def test_http_client_decodes_whole_numbers(
    monkeypatch: pytest.MonkeyPatch, method: str, value: Any
) -> None:
    seen = []

    def send(
        session: requests.Session, request: requests.PreparedRequest, **kwargs: Any
    ) -> requests.Response:
        seen.append(request)
        response = requests.Response()
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        response._content = json.dumps({"status": "success", "value": value}).encode()
        response.request = request
        return response

    monkeypatch.setattr(requests.Session, "send", send)
    client = ConvexHttpClient("https://example.convex.cloud")
    decoded = getattr(client, method)("numbers:read", {})
    assert len(seen) == 1
    assert seen[0].url == "https://example.convex.cloud/api/" + method
    body = seen[0].body
    assert isinstance(body, (str, bytes))
    payload: Dict[str, Any] = json.loads(body)
    assert payload["format"] == "convex_encoded_json"
    assert decoded == value
    if isinstance(decoded, dict):
        assert type(decoded["count"]) is float
        nested = decoded["nested"]
        assert isinstance(nested, list)
        assert type(nested[0]) is float
        assert nested[1] is True
    else:
        assert type(decoded) is float


@pytest.mark.parametrize("value", [True, False, None, "text", 1.5])
def test_other_json_primitives_are_unchanged(value: Any) -> None:
    decoded = json_to_convex(value)
    assert decoded == value
    assert type(decoded) is type(value)


def test_tagged_int64_remains_an_int64() -> None:
    original = ConvexInt64(2**60)
    decoded = json_to_convex(original.to_json())
    assert type(decoded) is ConvexInt64
    assert decoded.value == original.value
