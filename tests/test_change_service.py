import pytest

from app.mem0_client import Mem0Result, Mem0Status, MemoryRecord
from app.services.change_service import (
    ChangeConflict,
    ChangeExpired,
    ChangeForbidden,
    ChangeService,
)
from app.services.memory_service import MemoryService


class FakeClient:
    def __init__(self):
        self.record = MemoryRecord("m1", "old", "vault", {})
        self.updated = 0
        self.deleted = 0

    async def get(self, memory_id):
        return self.record

    async def update(self, memory_id, text, metadata=None):
        self.updated += 1
        self.record = MemoryRecord(memory_id, text, "vault", metadata or {})
        return Mem0Result(Mem0Status.SUCCEEDED, self.record)

    async def delete(self, memory_id):
        self.deleted += 1
        return Mem0Result(Mem0Status.SUCCEEDED)


@pytest.mark.asyncio
async def test_preview_confirm_binds_actor_and_is_one_use():
    client = FakeClient()
    service = ChangeService(MemoryService(client, "vault"))
    preview = await service.preview("update", "m1", "new", "alice")
    result = await service.confirm(preview.change_id, "alice")
    assert result.memory.text == "new"
    with pytest.raises(ChangeExpired):
        await service.confirm(preview.change_id, "alice")


@pytest.mark.asyncio
async def test_confirm_rejects_actor_and_stale_hash():
    client = FakeClient()
    service = ChangeService(MemoryService(client, "vault"))
    preview = await service.preview("update", "m1", "new", "alice")
    with pytest.raises(ChangeForbidden):
        await service.confirm(preview.change_id, "bob")
    client.record = MemoryRecord("m1", "changed", "vault", {})
    with pytest.raises(ChangeConflict):
        await service.confirm(preview.change_id, "alice")
