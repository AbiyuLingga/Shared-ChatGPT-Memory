from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MemoryResponse(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    memory: str
    score: float | None = None
    categories: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SearchResponse(BaseModel):
    count: int
    memories: list[MemoryResponse]


class SearchRequest(BaseModel):
    model_config = {"extra": "forbid"}

    query: str = Field(min_length=1, max_length=1000)


class AddRequest(BaseModel):
    model_config = {"extra": "forbid"}

    fact: str = Field(min_length=1, max_length=1500)
    memory_type: Literal[
        "preference", "project", "decision", "workflow", "personal_context", "other"
    ]


class AddResponse(BaseModel):
    accepted: bool
    completed: bool
    status: Literal["SUCCEEDED", "PENDING", "FAILED", "UNKNOWN", "ALREADY_EXISTS"]
    search_may_lag: bool


class ChangePreviewRequest(BaseModel):
    model_config = {"extra": "forbid"}

    operation: Literal["update", "delete"]
    memory_id: str
    replacement_fact: str | None = Field(default=None, min_length=1, max_length=1500)


class ChangeConfirmRequest(BaseModel):
    model_config = {"extra": "forbid"}

    change_id: str = Field(min_length=32, max_length=256)


class ChangePreviewResponse(BaseModel):
    change_id: str
    operation: Literal["update", "delete"]
    current_memory: str
    replacement_fact: str | None = None
    confirmation_required: bool = True
    expires_in_seconds: int


class ChangeConfirmResponse(BaseModel):
    status: str
    memory: MemoryResponse | None = None
