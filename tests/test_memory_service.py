import pytest

from app.mem0_client import Mem0Result, Mem0Status, MemoryRecord
from app.services.memory_service import MemoryNotFound, MemoryService, OwnershipError


class FakeClient:
    def __init__(self, records=None):
        self.records = records or []
        self.added = []
        self.updated = []
        self.deleted = []

    async def search(self, query):
        return self.records

    async def add(self, text, metadata=None):
        self.added.append((text, metadata))
        return Mem0Result(Mem0Status.SUCCEEDED, MemoryRecord("new", text, "vault", metadata or {}))

    async def get(self, memory_id):
        for r in self.records:
            if r.id == memory_id:
                return r
        raise MemoryNotFound(memory_id)

    async def update(self, memory_id, text, metadata=None):
        self.updated.append((memory_id, text, metadata))
        return Mem0Result(
            Mem0Status.SUCCEEDED, MemoryRecord(memory_id, text, "vault", metadata or {})
        )

    async def delete(self, memory_id):
        self.deleted.append(memory_id)
        return Mem0Result(Mem0Status.SUCCEEDED)


@pytest.mark.asyncio
async def test_add_dedupes_exact_text_before_remote_add():
    existing = MemoryRecord("m1", "same", "vault", {})
    client = FakeClient([existing])
    result = await MemoryService(client, "vault").add("same")
    assert result.id == "m1"
    assert client.added == []


@pytest.mark.asyncio
async def test_get_rejects_wrong_owner_as_not_found():
    client = FakeClient([MemoryRecord("m1", "x", "other", {})])
    with pytest.raises((MemoryNotFound, OwnershipError)):
        await MemoryService(client, "vault").get("m1")


@pytest.mark.asyncio
async def test_add_unknown_status_is_exposed_without_retry():
    class Unknown(FakeClient):
        async def add(self, text, metadata=None):
            return Mem0Result(Mem0Status.UNKNOWN)

    with pytest.raises(RuntimeError):
        await MemoryService(Unknown(), "vault").add("x")


@pytest.mark.asyncio
async def test_update_preserves_existing_metadata_when_replacement_has_none():
    existing = MemoryRecord("m1", "old", "vault", {"memory_type": "preference"})
    client = FakeClient([existing])
    result = await MemoryService(client, "vault").update("m1", "new")
    assert result.metadata["memory_type"] == "preference"
    assert client.updated[0][2]["memory_type"] == "preference"
