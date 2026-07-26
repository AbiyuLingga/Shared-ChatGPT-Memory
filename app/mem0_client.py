from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx


class Mem0Status(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    PENDING = "PENDING"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    ALREADY_EXISTS = "ALREADY_EXISTS"


@dataclass(slots=True)
class MemoryRecord:
    id: str
    text: str
    user_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None
    created_at: Any = None
    updated_at: Any = None

    @property
    def memory(self) -> str:
        return self.text


@dataclass(slots=True)
class Mem0Result:
    status: Mem0Status
    memory: MemoryRecord | None = None


class MemoryNotFound(LookupError):
    pass


class Mem0Error(RuntimeError):
    pass


class Mem0Client:
    """Small async Mem0 REST adapter; the vault user is never caller-controlled."""

    def __init__(
        self,
        api_key: str,
        vault_user_id: str,
        *,
        base_url: str = "https://api.mem0.ai",
        http_client: httpx.AsyncClient | None = None,
        server_metadata: dict[str, Any] | None = None,
        poll_timeout: float = 5.0,
        poll_interval: float = 0.1,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.vault_user_id = vault_user_id
        self._http = http_client
        self._owns_http = http_client is None
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
        self._server_metadata = dict(server_metadata or {})
        self._poll_timeout = poll_timeout
        self._poll_interval = poll_interval
        self._timeout_seconds = timeout_seconds

    async def __aenter__(self) -> "Mem0Client":
        await self._client()
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_http and self._http:
            await self._http.aclose()

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self._base_url, headers=self._headers, timeout=self._timeout_seconds
            )
        return self._http

    async def _request(
        self, method: str, path: str, *, read: bool = False, **kwargs: Any
    ) -> httpx.Response:
        client = await self._client()
        kwargs.setdefault("headers", self._headers)
        attempts = 3 if method.upper() == "GET" or read else 1
        for attempt in range(attempts):
            try:
                response = await client.request(method, self._base_url + path, **kwargs)
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt + 1 == attempts:
                    raise
                await asyncio.sleep(0.05)
                continue
            if response.status_code == 404:
                raise MemoryNotFound(path)
            if response.status_code in (429, 500, 502, 503, 504) and attempt + 1 < attempts:
                await asyncio.sleep(0.05)
                continue
            response.raise_for_status()
            return response
        raise Mem0Error("request failed")

    @staticmethod
    def _records(payload: Any) -> list[MemoryRecord]:
        if isinstance(payload, dict):
            items = payload.get("results", payload.get("memories"))
            if items is None and payload.get("id"):
                items = [payload]
            if items is None and isinstance(payload.get("memory"), dict):
                items = [payload["memory"]]
        else:
            items = payload
        if isinstance(items, dict):
            items = [items]
        return [
            MemoryRecord(
                str(item.get("id", "")),
                str(item.get("memory", item.get("text", ""))),
                str(item.get("user_id", "")),
                dict(item.get("metadata") or {}),
                item.get("score"),
                item.get("created_at"),
                item.get("updated_at"),
            )
            for item in items or []
        ]

    async def search(self, query: str) -> list[MemoryRecord]:
        response = await self._request(
            "POST",
            "/v3/memories/search/",
            read=True,
            json={
                "query": query,
                "filters": {"user_id": self.vault_user_id},
                "top_k": 5,
                "threshold": 0.1,
                "rerank": False,
            },
        )
        return self._records(response.json())

    async def get(self, memory_id: str) -> MemoryRecord:
        response = await self._request("GET", f"/v1/memories/{memory_id}/")
        records = self._records(response.json())
        if (
            not records
            or records[0].id != str(memory_id)
            or records[0].user_id != self.vault_user_id
        ):
            raise MemoryNotFound(memory_id)
        return records[0]

    async def add(self, text: str, metadata: dict[str, Any] | None = None) -> Mem0Result:
        body = {
            "messages": [{"role": "user", "content": text}],
            "user_id": self.vault_user_id,
            "infer": False,
            "metadata": {**(metadata or {}), **self._server_metadata},
        }
        try:
            response = await self._request("POST", "/v3/memories/", json=body)
        except (httpx.TimeoutException, httpx.TransportError):
            return Mem0Result(Mem0Status.UNKNOWN)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                return Mem0Result(Mem0Status.ALREADY_EXISTS)
            return Mem0Result(
                Mem0Status.UNKNOWN if exc.response.status_code >= 500 else Mem0Status.FAILED
            )
        payload = response.json()
        records = self._records(payload)
        if isinstance(payload, dict) and payload.get("status"):
            status = self._status(payload.get("status"))
            return Mem0Result(status, records[0] if records else None)
        event_id = payload.get("event_id") if isinstance(payload, dict) else None
        if event_id:
            return await self._poll(str(event_id))
        if response.status_code == 202:
            return Mem0Result(Mem0Status.PENDING, records[0] if records else None)
        return Mem0Result(Mem0Status.SUCCEEDED, records[0] if records else None)

    async def _poll(self, event_id: str) -> Mem0Result:
        if self._poll_timeout <= 0:
            return Mem0Result(Mem0Status.UNKNOWN)
        deadline = time.monotonic() + self._poll_timeout
        while time.monotonic() < deadline:
            try:
                response = await self._request("GET", f"/v1/events/{event_id}/")
            except (httpx.TimeoutException, httpx.TransportError):
                return Mem0Result(Mem0Status.UNKNOWN)
            payload = response.json()
            status = self._status(payload.get("status") if isinstance(payload, dict) else None)
            if status in (Mem0Status.SUCCEEDED, Mem0Status.FAILED, Mem0Status.ALREADY_EXISTS):
                records = self._records(payload)
                return Mem0Result(status, records[0] if records else None)
            await asyncio.sleep(self._poll_interval)
        return Mem0Result(Mem0Status.UNKNOWN)

    @staticmethod
    def _status(value: Any) -> Mem0Status:
        try:
            return Mem0Status(str(value).upper())
        except ValueError:
            return Mem0Status.PENDING

    async def update(
        self, memory_id: str, text: str, metadata: dict[str, Any] | None = None
    ) -> Mem0Result:
        response = await self._request(
            "PUT",
            f"/v1/memories/{memory_id}/",
            json={
                "memory": text,
                "user_id": self.vault_user_id,
                "metadata": metadata or {},
            },
        )
        records = self._records(response.json())
        return Mem0Result(Mem0Status.SUCCEEDED, records[0] if records else None)

    async def delete(self, memory_id: str) -> Mem0Result:
        await self._request("DELETE", f"/v1/memories/{memory_id}/?user_id={self.vault_user_id}")
        return Mem0Result(Mem0Status.SUCCEEDED)
