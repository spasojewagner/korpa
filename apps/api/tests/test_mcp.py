from collections.abc import Awaitable, Callable
from datetime import timedelta

import httpx2
import pytest
import test_rest
from fastapi.testclient import TestClient
from korpa_api.ai.limits import RateLimiter
from korpa_api.main import app
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from test_rest import AS_OF, B1, B2
from test_rest import engine as engine

rest_client = test_rest.client


@pytest.fixture()
def client(rest_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("korpa_api.main.mcp_limits", RateLimiter(per_minute=60, per_day=None))
    monkeypatch.setattr("korpa_api.mcp_server.belgrade_today", lambda: AS_OF)
    return rest_client


def with_mcp(client: TestClient, check: Callable[[Client], Awaitable[None]]) -> None:
    async def run() -> None:
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app)) as http:
            transport = streamable_http_client("http://localhost/mcp/", http_client=http)
            # Force the initialize handshake as well as testing the current SDK client.
            async with Client(transport, mode="legacy") as mcp:
                assert mcp.server_info.name == "Korpa"
                await check(mcp)

    assert client.portal is not None
    client.portal.call(run)


def test_initialize_and_exactly_three_read_only_tools(client: TestClient) -> None:
    async def check(mcp: Client) -> None:
        tools = (await mcp.list_tools()).tools
        assert {tool.name for tool in tools} == {
            "search_products",
            "compare_prices",
            "cheapest_basket",
        }
        for tool in tools:
            assert tool.annotations is not None
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.destructive_hint is False
            assert tool.description is not None
            for text in ("data.gov.rs", "para (1/100 RSD)", "not a state service"):
                assert text in tool.description

    with_mcp(client, check)


def test_search_matches_rest(client: TestClient) -> None:
    expected = client.get("/api/search", params={"q": "mleko", "category": 1, "limit": 10}).json()

    async def check(mcp: Client) -> None:
        result = await mcp.call_tool("search_products", {"query": "mleko", "category": 1})
        assert not result.is_error
        assert result.structured_content == expected

    with_mcp(client, check)


def test_compare_prices_matches_product_page(client: TestClient) -> None:
    async def check(mcp: Client) -> None:
        result = await mcp.call_tool("compare_prices", {"barcode": B1})
        assert not result.is_error
        data = result.structured_content
        assert data is not None
        assert data["as_of"] == AS_OF.isoformat()
        prices = data["prices"]
        assert [p["format_id"] for p in prices] == [1, 2, 3]
        assert [p["format_name"] for p in prices] == ["Market A", "Market B", "Delimični market"]
        assert [p["regular_para"] for p in prices] == [100, 105, 10]
        assert [p["discounted_para"] for p in prices] == [80, None, None]
        assert [p["effective_para"] for p in prices] == [80, 105, 10]
        assert [p["retailer_slug"] for p in prices] == ["r1", "r1", "r2"]
        for i, price in enumerate(prices, 1):
            assert price["list_date"] == (AS_OF - timedelta(days=i)).isoformat()
            assert price["as_of"] == AS_OF.isoformat()
        assert prices[0]["discount_from"] == prices[0]["discount_to"] == AS_OF.isoformat()

    with_mcp(client, check)


def test_basket_matches_rest_with_ranking_duplicates_and_missing(client: TestClient) -> None:
    body = {
        "items": [{"barcode": B1, "qty": 2}, {"barcode": B1, "qty": 3}, {"barcode": B2, "qty": 1}]
    }
    expected = client.post("/api/basket", json=body).json()

    async def check(mcp: Client) -> None:
        result = await mcp.call_tool("cheapest_basket", body)
        assert not result.is_error
        assert result.structured_content == expected

    with_mcp(client, check)


def test_unknown_barcode_returns_empty_prices(client: TestClient) -> None:
    async def check(mcp: Client) -> None:
        result = await mcp.call_tool("compare_prices", {"barcode": "0000000000099"})
        assert not result.is_error
        assert result.structured_content == {"prices": [], "as_of": AS_OF.isoformat()}

    with_mcp(client, check)


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("cheapest_basket", {"items": [{"barcode": B1, "qty": 1}] * 51}),
        ("cheapest_basket", {"items": []}),
        ("cheapest_basket", {"items": [{"barcode": B1, "qty": 0}]}),
        ("cheapest_basket", {"items": [{"barcode": B1, "qty": 100}]}),
        ("cheapest_basket", {"items": [{"barcode": B1, "qty": True}]}),
        ("cheapest_basket", {"items": [{"barcode": B1, "qty": 99}] * 2}),
        ("compare_prices", {"barcode": "123"}),
        ("search_products", {"query": "a"}),
        ("search_products", {"query": " " * 3}),
        ("search_products", {"query": "a" * 101}),
        ("search_products", {"query": "mleko", "category": 26}),
        ("search_products", {"query": "mleko", "category": 0}),
        ("search_products", {"query": "mleko", "limit": 21}),
        ("search_products", {"query": "mleko", "limit": 0}),
    ],
)
def test_validation_is_a_tool_error(
    client: TestClient, tool: str, arguments: dict[str, object]
) -> None:
    async def check(mcp: Client) -> None:
        result = await mcp.call_tool(tool, arguments)
        assert result.is_error
        # The session remains usable after an invalid tool call.
        assert len((await mcp.list_tools()).tools) == 3

    with_mcp(client, check)


def test_transport_json_stateless_and_host_origin_checks(client: TestClient) -> None:
    headers = {"Accept": "application/json, text/event-stream"}
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }
    for host in ("localhost", "127.0.0.1:8000", "korpa-api.onrender.com"):
        response = client.post("/mcp/", json=body, headers={**headers, "Host": host})
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("application/json")
        assert "mcp-session-id" not in response.headers
    assert (
        client.post("/mcp/", json=body, headers={**headers, "Host": "evil.example"}).status_code
        == 421
    )
    assert (
        client.post(
            "/mcp/",
            json=body,
            headers={**headers, "Host": "localhost", "Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/mcp/",
            json=body,
            headers={
                **headers,
                "Host": "korpa-api.onrender.com",
                "Origin": "https://ai-korpa.vercel.app",
            },
        ).status_code
        == 200
    )


def test_mcp_stays_out_of_openapi() -> None:
    assert not any(path.startswith("/mcp") for path in app.openapi()["paths"])
