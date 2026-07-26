from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.mem0_client import Mem0Status, MemoryRecord
from app.schemas import (
    AddRequest,
    AddResponse,
    ChangeConfirmRequest,
    ChangeConfirmResponse,
    ChangePreviewRequest,
    ChangePreviewResponse,
    MemoryResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.change_service import ChangeConflict, ChangeExpired, ChangeForbidden
from app.services.memory_service import OwnershipError

router = APIRouter(prefix="/v1", tags=["memories"])
SECRET_PATTERN = re.compile(
    r"(?ix)(?:\b(?:api[\s_-]*key|access[\s_-]*token|auth(?:entication)?[\s_-]*token|"
    r"password|passwd|secret|client[\s_-]*secret|bearer)\s*[:=]\s*\S+)"
    r"|\b(?:sk-[a-z0-9_-]{16,}|gh[pousr]_[a-z0-9_]{20,}|AKIA[0-9A-Z]{16})\b"
    r"|-----BEGIN\s+(?:RSA|OPENSSH|EC|PRIVATE)\s+KEY-----"
    r"|\beyJ[a-z0-9_-]{20,}\.[a-z0-9_-]{10,}\.[a-z0-9_-]{10,}\b"
    r"|\b(?:\d[ -]?){13,19}\b"
)


def require_subject(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    claims = request.app.state.authenticator.authenticate(authorization)
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")
    operation = "read" if request.url.path.endswith("/search") else "write"
    if not request.app.state.rate_limiter.allow(subject, operation):
        raise HTTPException(
            status_code=429, detail="Too many requests", headers={"Retry-After": "60"}
        )
    request.state.subject = subject
    return subject


def _memory_response(record: MemoryRecord) -> MemoryResponse:
    if len(record.text) > 10_000:
        raise HTTPException(status_code=502, detail="Memory provider returned an oversized result")
    categories = record.metadata.get("categories", [])
    if not isinstance(categories, list):
        categories = []
    memory_type = record.metadata.get("memory_type")
    if isinstance(memory_type, str) and memory_type not in categories:
        categories = [memory_type, *categories]
    return MemoryResponse(
        id=record.id,
        memory=record.text,
        score=record.score,
        categories=[str(value) for value in categories[:10]],
        created_at=_datetime(record.created_at),
        updated_at=_datetime(record.updated_at),
    )


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _memory_service(request: Request) -> Any:
    return request.app.state.memory_service


def _change_service(request: Request) -> Any:
    return request.app.state.change_service


@router.post("/memories/search", response_model=SearchResponse)
async def search_memory(
    payload: SearchRequest,
    service: Any = Depends(_memory_service),
    _subject: str = Depends(require_subject),
) -> SearchResponse:
    try:
        records = await service.search(payload.query)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Shared memory is unavailable") from exc
    return SearchResponse(
        count=len(records), memories=[_memory_response(record) for record in records]
    )


@router.post("/memories", response_model=AddResponse)
async def add_memory(
    payload: AddRequest,
    service: Any = Depends(_memory_service),
    _subject: str = Depends(require_subject),
) -> AddResponse:
    if SECRET_PATTERN.search(payload.fact):
        raise HTTPException(status_code=400, detail="This type of sensitive data cannot be stored")
    metadata = {
        "source": "custom-gpt",
        "memory_type": payload.memory_type,
        "schema_version": "1",
    }
    try:
        result = await service.add_result(payload.fact, metadata)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Shared memory is unavailable") from exc
    completed = result.status in (Mem0Status.SUCCEEDED, Mem0Status.ALREADY_EXISTS)
    accepted = result.status is not Mem0Status.UNKNOWN
    return AddResponse(
        accepted=accepted,
        completed=completed,
        status=result.status,
        search_may_lag=result.status
        in (Mem0Status.SUCCEEDED, Mem0Status.ALREADY_EXISTS, Mem0Status.PENDING),
    )


@router.post("/memory-changes/preview", response_model=ChangePreviewResponse)
async def preview_change(
    payload: ChangePreviewRequest,
    service: Any = Depends(_change_service),
    subject: str = Depends(require_subject),
) -> ChangePreviewResponse:
    try:
        uuid.UUID(payload.memory_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="memory_id must be a UUID") from exc
    if payload.operation == "update" and payload.replacement_fact is None:
        raise HTTPException(status_code=422, detail="replacement_fact is required for update")
    if payload.operation == "delete" and payload.replacement_fact is not None:
        raise HTTPException(status_code=422, detail="replacement_fact is not allowed for delete")
    if payload.replacement_fact and SECRET_PATTERN.search(payload.replacement_fact):
        raise HTTPException(status_code=400, detail="This type of sensitive data cannot be stored")
    try:
        preview = await service.preview(
            payload.operation,
            payload.memory_id,
            payload.replacement_fact,
            subject,
        )
    except (LookupError, OwnershipError) as exc:
        raise HTTPException(status_code=404, detail="Memory not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Shared memory is unavailable") from exc
    expires = max(0, int((preview.expires_at - datetime.now(timezone.utc)).total_seconds()))
    if len(preview.current_text) > 10_000:
        raise HTTPException(status_code=502, detail="Memory provider returned an oversized result")
    return ChangePreviewResponse(
        change_id=preview.change_id,
        operation=preview.operation,
        current_memory=preview.current_text,
        replacement_fact=preview.replacement,
        expires_in_seconds=expires,
    )


@router.post("/memory-changes/confirm", response_model=ChangeConfirmResponse)
async def confirm_change(
    payload: ChangeConfirmRequest,
    service: Any = Depends(_change_service),
    subject: str = Depends(require_subject),
) -> ChangeConfirmResponse:
    try:
        result = await service.confirm(payload.change_id, subject)
    except ChangeExpired as exc:
        raise HTTPException(
            status_code=410, detail="Change request expired or was already used"
        ) from exc
    except ChangeForbidden as exc:
        raise HTTPException(
            status_code=403, detail="Change request belongs to another account"
        ) from exc
    except ChangeConflict as exc:
        raise HTTPException(status_code=409, detail="Memory changed before confirmation") from exc
    except (LookupError, OwnershipError) as exc:
        raise HTTPException(status_code=404, detail="Memory not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Shared memory is unavailable") from exc
    return ChangeConfirmResponse(
        status=result.status,
        memory=_memory_response(result.memory) if result.memory else None,
    )
