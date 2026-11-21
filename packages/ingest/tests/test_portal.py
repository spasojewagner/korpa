import json
from pathlib import Path

import httpx
import pytest
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


SOURCE = RetailerSource("demo", "Demo", "id", "https://example.org/prices.csv", "sodl")


@pytest.mark.parametrize("failure", [httpx.ConnectTimeout, httpx.ReadTimeout, 500, 503, 599])
@pytest.mark.parametrize("recover_after", [1, 2, 3])
def test_transient_download_retries_are_bounded_and_reported(
    monkeypatch: pytest.MonkeyPatch, failure: type[httpx.TimeoutException] | int, recover_after: int
) -> None:
    delays: list[int] = []
    requests: list[httpx.Request] = []
    monkeypatch.setattr("korpa_ingest.portal.time.sleep", delays.append)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["if-none-match"] == '"abc"'
        if len(requests) <= recover_after:
            if isinstance(failure, int):
                return httpx.Response(failure)
            raise failure("temporary", request=request)
        return httpx.Response(200, content=b"complete", headers={"etag": '"new"'})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        portal = PortalClient(client)
        if recover_after == 3:
            with pytest.raises(httpx.HTTPError):
                portal.download(SOURCE, '"abc"')
        else:
            result = portal.download(SOURCE, '"abc"')
            assert result.content == b"complete"
            assert result.etag == '"new"'
        assert portal.download_retries == min(recover_after, 2)
    assert delays == [5, 15][: min(recover_after, 2)]
    assert len(requests) == min(recover_after + 1, 3)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 408, 429, 499])
def test_client_errors_are_never_retried(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    delays: list[int] = []
    monkeypatch.setattr("korpa_ingest.portal.time.sleep", delays.append)
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status))) as client:
        portal = PortalClient(client)
        with pytest.raises(httpx.HTTPStatusError):
            portal.download(SOURCE)
        assert portal.download_retries == 0
    assert not delays


def test_read_timeout_discards_partial_body_and_resets_next_retailer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delays: list[int] = []
    monkeypatch.setattr("korpa_ingest.portal.time.sleep", delays.append)

    class BrokenStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b"partial"
            raise httpx.ReadTimeout("interrupted stream")

    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(200, stream=BrokenStream())
        assert request.headers["if-modified-since"] == "yesterday"
        return httpx.Response(200, content=b"whole")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        portal = PortalClient(client)
        assert portal.download(SOURCE, modified="yesterday").content == b"whole"
        assert portal.download_retries == 1
        portal.download(SOURCE, modified="yesterday")
        assert portal.download_retries == 0
    assert delays == [5]


@pytest.mark.parametrize("failure", [httpx.ConnectError, httpx.WriteTimeout, httpx.PoolTimeout])
def test_other_transport_errors_are_not_retried(
    monkeypatch: pytest.MonkeyPatch, failure: type[httpx.TransportError]
) -> None:
    delays: list[int] = []
    monkeypatch.setattr("korpa_ingest.portal.time.sleep", delays.append)

    def handler(request: httpx.Request) -> httpx.Response:
        raise failure("failure", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        portal = PortalClient(client)
        with pytest.raises(failure):
            portal.download(SOURCE)
        assert portal.download_retries == 0
    assert not delays
