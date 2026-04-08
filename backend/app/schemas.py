from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, field_validator


# ── Section ───────────────────────────────────────────────────────────────────

class Section(BaseModel):
    type: str
    title: Optional[str] = None
    content: Any = None

    model_config = {"extra": "allow"}


# ── Request bodies ────────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    agent: str
    title: str
    subtitle: Optional[str] = None
    timestamp: datetime
    tags: Optional[list[str]] = []
    sections: list[Section]

    model_config = {"extra": "allow"}


class ReportUpdate(BaseModel):
    """All fields optional; agent and receivedAt are immutable on the server side."""
    title: Optional[str] = None
    subtitle: Optional[str] = None
    timestamp: Optional[datetime] = None
    tags: Optional[list[str]] = None
    sections: Optional[list[Section]] = None

    model_config = {"extra": "allow"}


# ── Responses ─────────────────────────────────────────────────────────────────

class ReportCreateResponse(BaseModel):
    id: str
    url: str


class ReportUpdateResponse(BaseModel):
    id: str
    url: str
    updated: bool = True


class ReportDeleteResponse(BaseModel):
    ok: bool = True
    id: str


class ReportSummary(BaseModel):
    """Matches the legacy index.json entry shape (camelCase to match legacy API)."""
    id: str
    agent: str
    title: str
    subtitle: Optional[str]
    timestamp: datetime
    receivedAt: datetime
    updatedAt: Optional[datetime] = None
    tags: list[str]


class ReportFull(BaseModel):
    """Full report object returned by GET /api/reports/{id}."""
    id: str
    agent: str
    title: str
    subtitle: Optional[str]
    timestamp: datetime
    receivedAt: datetime
    updatedAt: Optional[datetime] = None
    tags: list[Any]
    sections: list[Any]
