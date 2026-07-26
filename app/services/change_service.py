from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from app.mem0_client import MemoryRecord
from app.services.memory_service import MemoryService


class ChangeExpired(RuntimeError):
    pass


class ChangeForbidden(PermissionError):
    pass


class ChangeConflict(RuntimeError):
    pass


@dataclass(slots=True)
class ChangePreview:
    change_id: str
    operation: Literal["update", "delete"]
    memory_id: str
    old_hash: str
    expires_at: datetime
    current_text: str
    replacement: str | None


@dataclass(slots=True)
class ChangeConfirm:
    status: str
    memory: MemoryRecord | None = None


@dataclass(slots=True)
class _Pending:
    operation: Literal["update", "delete"]
    memory_id: str
    actor: str
    old_hash: str
    text: str | None
    metadata: dict[str, Any] | None
    expires: float


class ChangeService:
    def __init__(
        self,
        memory_service: MemoryService,
        *,
        ttl_seconds: int = 600,
        max_pending: int = 1024,
        token_secret: str = "",
    ) -> None:
        self.memory = memory_service
        self.ttl_seconds = ttl_seconds
        self.max_pending = max_pending
        self._token_secret = token_secret.encode()
        self._pending: dict[str, _Pending] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _hash(record: MemoryRecord) -> str:
        return hashlib.sha256(record.text.encode()).hexdigest()

    async def preview(
        self,
        operation: Literal["update", "delete"],
        memory_id: str,
        text: str | None = None,
        actor: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ChangePreview:
        if operation not in ("update", "delete"):
            raise ValueError("unsupported operation")
        if operation == "update" and text is None:
            raise ValueError("update requires replacement text")
        if operation == "delete" and text is not None:
            raise ValueError("delete does not accept replacement text")
        record = await self.memory.get(memory_id)
        async with self._lock:
            now = time.time()
            for key, pending in list(self._pending.items()):
                if pending.expires <= now:
                    self._pending.pop(key, None)
            while len(self._pending) >= self.max_pending:
                self._pending.pop(next(iter(self._pending)))
            nonce = secrets.token_urlsafe(32)
            tag = hmac.new(self._token_secret, nonce.encode(), hashlib.sha256).hexdigest()[:32]
            change_id = f"{nonce}.{tag}"
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)
            self._pending[change_id] = _Pending(
                operation,
                memory_id,
                actor,
                self._hash(record),
                text,
                metadata,
                expires_at.timestamp(),
            )
        return ChangePreview(
            change_id, operation, memory_id, self._hash(record), expires_at, record.text, text
        )

    async def confirm(self, change_id: str, actor: str) -> ChangeConfirm:
        async with self._lock:
            return await self._confirm(change_id, actor)

    async def _confirm(self, change_id: str, actor: str) -> ChangeConfirm:
        pending = self._pending.get(change_id)
        if pending is None or pending.expires <= time.time():
            raise ChangeExpired(change_id)
        if pending.actor != actor:
            raise ChangeForbidden(change_id)
        current = await self.memory.get(pending.memory_id)
        if self._hash(current) != pending.old_hash:
            raise ChangeConflict(pending.memory_id)
        # Consume immediately before the internal mutation: retries cannot replay a valid change.
        self._pending.pop(change_id, None)
        if pending.operation == "update":
            record = await self.memory.update(
                pending.memory_id, pending.text or "", pending.metadata
            )
            return ChangeConfirm("SUCCEEDED", record)
        await self.memory.delete(pending.memory_id)
        return ChangeConfirm("SUCCEEDED")
