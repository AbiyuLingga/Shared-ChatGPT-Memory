import json

import httpx
import pytest

from app.mem0_client import Mem0Client, Mem0Status, MemoryNotFound


@pytest.mark.asyncio
async def test_search_injects_vault_and_fixed_defaults():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.update({"url": str(request.url), "json": json.loads(request.content)})
        return httpx.Response(200, json=[{"id": "m1", "memory": "hello", "user_id": "vault"}])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = Mem0Client("secret", "vault", http_client=http)
        result = await client.search("hello")

    assert result[0].id == "m1"
    assert seen["json"] == {
        "query": "hello",
        "filters": {"user_id": "vault"},
        "top_k": 5,
        "threshold": 0.1,
        "rerank": False,
    }
    assert "/v3/" in seen["url"]


@pytest.mark.asyncio
async def test_add_polls_event_without_retrying_post():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "POST":
            return httpx.Response(202, json={"event_id": "e1"})
        return httpx.Response(200, json={"status": "SUCCEEDED"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = Mem0Client("secret", "vault", http_client=http, poll_interval=0)
        result = await client.add("hello", {"source": "server"})

    assert result.status is Mem0Status.SUCCEEDED
    assert calls == ["POST", "GET"]


@pytest.mark.asyncio
async def test_add_uses_explicit_messages_and_disables_inference():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"id": "m1", "memory": "hello", "user_id": "vault"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = Mem0Client("secret", "vault", http_client=http)
        await client.add("hello", {"memory_type": "preference"})

    assert seen["user_id"] == "vault"
    assert seen["infer"] is False
    assert seen["messages"] == [{"role": "user", "content": "hello"}]


@pytest.mark.asyncio
async def test_search_retries_transient_rate_limit():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429)
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = Mem0Client("secret", "vault", http_client=http)
        await client.search("hello")

    assert calls == 2


@pytest.mark.asyncio
async def test_add_timeout_returns_unknown_and_does_not_retry():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(202, json={"event_id": "e1"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = Mem0Client("secret", "vault", http_client=http, poll_interval=0, poll_timeout=0)
        result = await client.add("hello")

    assert result.status is Mem0Status.UNKNOWN
    assert calls == 1


@pytest.mark.asyncio
async def test_update_and_delete_use_v1_and_fixed_user():
    seen = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, json.loads(request.content or b"{}")))
        return httpx.Response(200, json={"id": "m1", "user_id": "vault", "memory": "x"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = Mem0Client("secret", "vault", http_client=http)
        await client.update("m1", "x", {"a": 1})
        await client.delete("m1")

    assert seen[0][1].startswith("/v1/")
    assert seen[0][2]["user_id"] == "vault"
    assert seen[1][1].startswith("/v1/")


@pytest.mark.asyncio
async def test_get_rejects_provider_record_with_wrong_id():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "another", "user_id": "vault", "memory": "x"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = Mem0Client("secret", "vault", http_client=http)
        with pytest.raises(MemoryNotFound):
            await client.get("m1")
