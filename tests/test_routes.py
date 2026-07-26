from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.mem0_client import Mem0Result, Mem0Status, MemoryRecord

VAULT = "vault_opaque"
MEMORY_ID = "123e4567-e89b-12d3-a456-426614174000"


def settings(environment: str = "test") -> Settings:
    return Settings(
        mem0_api_key="not-a-real-key",
        memory_vault_id=VAULT,
        auth0_domain="tenant.example.com",
        auth0_audience="https://api.example.com",
        auth0_allowed_subjects={"auth0|alice"},
        change_token_secret="x" * 32,
        environment=environment,
    )


class FakeAuth:
    def authenticate(self, authorization=None):
        if authorization != "Bearer good":
            raise HTTPException(
                401, "Invalid or missing bearer token", {"WWW-Authenticate": "Bearer"}
            )
        return {"sub": "auth0|alice"}


class FakeClient:
    def __init__(self):
        self.record = MemoryRecord(
            MEMORY_ID,
            "Pengguna suka jawaban langsung.",
            VAULT,
            {"memory_type": "preference"},
            0.82,
            datetime(2026, 7, 26, tzinfo=timezone.utc),
            datetime(2026, 7, 26, tzinfo=timezone.utc),
        )
        self.searched = None
        self.added = []

    async def search(self, query):
        self.searched = query
        return [self.record]

    async def add_result(self, text, metadata=None):
        self.added.append((text, metadata))
        return Mem0Result(Mem0Status.SUCCEEDED, self.record)

    async def add(self, text, metadata=None):
        return await self.add_result(text, metadata)

    async def get(self, memory_id):
        if memory_id != self.record.id:
            raise LookupError(memory_id)
        return self.record

    async def update(self, memory_id, text, metadata=None):
        self.record = MemoryRecord(memory_id, text, VAULT, metadata or self.record.metadata)
        return Mem0Result(Mem0Status.SUCCEEDED, self.record)

    async def delete(self, memory_id):
        self.record = None
        return Mem0Result(Mem0Status.SUCCEEDED)


@pytest.fixture
def client_and_fake():
    fake = FakeClient()
    app = create_app(settings(), mem0_client=fake, authenticator=FakeAuth())
    return TestClient(app), fake


def test_public_endpoints_and_production_docs():
    app = create_app(settings("production"), mem0_client=FakeClient(), authenticator=FakeAuth())
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/privacy").status_code == 200
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_search_is_safe_and_does_not_accept_vault_selector(client_and_fake):
    client, fake = client_and_fake
    response = client.post(
        "/v1/memories/search",
        json={"query": "gaya jawaban"},
        headers={"Authorization": "Bearer good"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["memories"][0]["memory"] == "Pengguna suka jawaban langsung."
    assert "user_id" not in body["memories"][0]
    assert fake.searched == "gaya jawaban"

    rejected = client.post(
        "/v1/memories/search",
        json={"query": "x", "user_id": "attacker"},
        headers={"Authorization": "Bearer good"},
    )
    assert rejected.status_code == 422


def test_add_requires_explicit_safe_fields(client_and_fake):
    client, fake = client_and_fake
    response = client.post(
        "/v1/memories",
        json={"fact": "Jawaban harus kritis.", "memory_type": "preference"},
        headers={"Authorization": "Bearer good"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCEEDED"
    assert fake.added[0][1]["source"] == "custom-gpt"
    assert fake.added[0][1]["memory_type"] == "preference"

    rejected = client.post(
        "/v1/memories",
        json={"fact": "api_key=sk-proj-1234567890123456", "memory_type": "other"},
        headers={"Authorization": "Bearer good"},
    )
    assert rejected.status_code == 400


def test_change_requires_preview_then_confirm(client_and_fake):
    client, _ = client_and_fake
    preview = client.post(
        "/v1/memory-changes/preview",
        json={"operation": "update", "memory_id": MEMORY_ID, "replacement_fact": "Singkat."},
        headers={"Authorization": "Bearer good"},
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["confirmation_required"] is True
    assert preview_body["current_memory"]

    confirmed = client.post(
        "/v1/memory-changes/confirm",
        json={"change_id": preview_body["change_id"]},
        headers={"Authorization": "Bearer good"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "SUCCEEDED"
