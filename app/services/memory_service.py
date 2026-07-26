from __future__ import annotations

import asyncio
from typing import Any

from app.mem0_client import (
    Mem0Client,
    Mem0Result,
    Mem0Status,
    MemoryRecord,
)
from app.mem0_client import (
    MemoryNotFound as _MemoryNotFound,
)

MemoryNotFound = _MemoryNotFound


class OwnershipError(PermissionError):
    pass


class MemoryService:
    def __init__(self, client: Mem0Client, vault_user_id: str) -> None:
        self.client = client
        self.vault_user_id = vault_user_id
        # ponytail: one replica and a small user count make a single lock safer
        # than a distributed idempotency store; move this to Redis before scaling.
        self._add_lock = asyncio.Lock()

    async def search(self, query: str) -> list[MemoryRecord]:
        return [r for r in await self.client.search(query) if r.user_id == self.vault_user_id]

    async def add(self, text: str, metadata: dict[str, Any] | None = None) -> MemoryRecord:
        result = await self.add_result(text, metadata)
        if result.status is Mem0Status.ALREADY_EXISTS and result.memory:
            return result.memory
        if result.status is not Mem0Status.SUCCEEDED or result.memory is None:
            raise RuntimeError(f"memory add status: {result.status}")
        return result.memory

    async def add_result(self, text: str, metadata: dict[str, Any] | None = None) -> Mem0Result:
        """Return Mem0's terminal/uncertain status for routes that need to expose it."""
        async with self._add_lock:
            for record in await self.search(text):
                if record.text == text:
                    return Mem0Result(Mem0Status.ALREADY_EXISTS, record)
            return await self.client.add(text, metadata)

    async def get(self, memory_id: str) -> MemoryRecord:
        record = await self.client.get(memory_id)
        if record.id != memory_id or record.user_id != self.vault_user_id:
            raise OwnershipError(memory_id)
        return record

    async def update(
        self, memory_id: str, text: str, metadata: dict[str, Any] | None = None
    ) -> MemoryRecord:
        current = await self.get(memory_id)
        merged_metadata = {**current.metadata, **(metadata or {})}
        result = await self.client.update(memory_id, text, merged_metadata)
        if result.status is not Mem0Status.SUCCEEDED or result.memory is None:
            raise RuntimeError(f"memory update status: {result.status}")
        if result.memory.user_id != self.vault_user_id:
            raise OwnershipError(memory_id)
        return result.memory

    async def delete(self, memory_id: str) -> Mem0Result:
        await self.get(memory_id)
        result = await self.client.delete(memory_id)
        if result.status is not Mem0Status.SUCCEEDED:
            raise RuntimeError(f"memory delete status: {result.status}")
        return result
