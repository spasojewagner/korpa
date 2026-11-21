import json
from pathlib import Path

import httpx
from korpa_ingest.portal import PortalClient, RetailerSource

FIXTURES = Path(__file__).parent / "fixtures"


def test_verified_portal_shape_and_pagination() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.params.get("page") == "2":
            return httpx.Response(200, json={"data": [], "next_page": None})
        page = json.loads((FIXTURES / "portal.json").read_text(encoding="utf-8"))
        return httpx.Response(200, json=page)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        sources = PortalClient(client).discover()
    assert len(sources) == 1
    assert sources[0].slug == "demo-retailer"
    assert sources[0].license == "sodl"
    assert len(requests) == 6


def test_conditional_request_and_304() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["if-none-match"] == '"abc"'
        assert "if-modified-since" not in request.headers
        return httpx.Response(304)

    source = RetailerSource("demo", "Demo", "id", "https://example.org/prices.csv", "sodl")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = PortalClient(client).download(source, '"abc"', "yesterday")
    assert result.status == 304
    assert not result.content


def test_ambiguous_resources_are_reported() -> None:
    page = json.loads((FIXTURES / "portal.json").read_text(encoding="utf-8"))
    page["next_page"] = None
    page["data"][0]["resources"].append(
        {
            "id": "second",
            "format": "csv",
            "url": "https://example.org/cene_proizvoda_other.csv",
        }
    )
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=page))) as c:
        portal = PortalClient(c)
        assert not portal.discover()
        assert portal.issues == {"demo-retailer": "ambiguous_resources"}


def test_pagination_cannot_escape_origin() -> None:
    page = {"data": [], "next_page": "https://other.example/api/1/datasets/"}
    import pytest

    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=page))) as c:
        with pytest.raises(ValueError, match="pagination"):
            PortalClient(c).discover()
