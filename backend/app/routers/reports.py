import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Report
from ..schemas import (
    ReportCreate,
    ReportUpdate,
    ReportCreateResponse,
    ReportUpdateResponse,
    ReportDeleteResponse,
)

router = APIRouter()
logger = logging.getLogger("dash.reports")

VALID_AGENTS = [
    "fiona", "reel", "dilan", "lilani", "homer", "sydney", "cody", "vita", "wellbeing",
    "clawdette", "sage", "clawmaster",
]


def _build_id(agent: str) -> str:
    now = datetime.now()
    return f"{agent}-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"


def _report_to_summary(report: Report) -> dict:
    """Return an index-entry dict matching the legacy API shape."""
    d = {
        "id":         report.id,
        "agent":      report.agent,
        "title":      report.title,
        "subtitle":   report.subtitle,
        "timestamp":  report.timestamp.isoformat() if report.timestamp else None,
        "receivedAt": report.received_at.isoformat() if report.received_at else None,
        "tags":       json.loads(report.tags or "[]"),
    }
    if report.updated_at:
        d["updatedAt"] = report.updated_at.isoformat()
    return d


def _report_to_full(report: Report) -> dict:
    """Return a full report dict matching the legacy API shape."""
    d = {
        "id":         report.id,
        "agent":      report.agent,
        "title":      report.title,
        "subtitle":   report.subtitle,
        "timestamp":  report.timestamp.isoformat() if report.timestamp else None,
        "receivedAt": report.received_at.isoformat() if report.received_at else None,
        "tags":       json.loads(report.tags or "[]"),
        "sections":   json.loads(report.sections or "[]"),
    }
    if report.updated_at:
        d["updatedAt"] = report.updated_at.isoformat()
    return d


# ── POST /api/report ──────────────────────────────────────────────────────────

@router.post("/api/report", status_code=201)
def create_report(payload: ReportCreate, db: Session = Depends(get_db)):
    agent_key = payload.agent.lower()
    if agent_key not in VALID_AGENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent. Must be one of: {', '.join(VALID_AGENTS)}",
        )

    report_id = _build_id(agent_key)
    now = datetime.now(timezone.utc)

    # Sections may carry extra fields — serialise the full model dump
    sections_data = [s.model_dump() for s in payload.sections]

    report = Report(
        id=report_id,
        agent=agent_key,
        title=payload.title,
        subtitle=payload.subtitle,
        timestamp=payload.timestamp,
        tags=json.dumps(payload.tags or []),
        sections=json.dumps(sections_data),
        received_at=now,
        bumped_at=now,
    )
    db.add(report)
    db.commit()

    url = f"{settings.DASH_URL}/reports/{report_id}"
    logger.info("New report: %s — %s", report_id, payload.title)
    return {"id": report_id, "url": url}


# ── PUT /api/reports/{id} ─────────────────────────────────────────────────────

@router.put("/api/reports/{report_id}")
def update_report(report_id: str, payload: ReportUpdate, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    now = datetime.now(timezone.utc)

    if payload.title is not None:
        report.title = payload.title
    if payload.subtitle is not None:
        report.subtitle = payload.subtitle
    if payload.timestamp is not None:
        report.timestamp = payload.timestamp
    if payload.tags is not None:
        report.tags = json.dumps(payload.tags)
    if payload.sections is not None:
        report.sections = json.dumps([s.model_dump() for s in payload.sections])

    report.updated_at = now
    report.bumped_at = now  # bump to top of feed
    db.commit()

    url = f"{settings.DASH_URL}/reports/{report_id}"
    logger.info("Updated report: %s — %s", report_id, report.title)
    return {"id": report_id, "url": url, "updated": True}


# ── DELETE /api/reports/{id} ──────────────────────────────────────────────────

@router.delete("/api/reports/{report_id}")
def delete_report(report_id: str, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()

    logger.info("Deleted report: %s", report_id)
    return {"ok": True, "id": report_id}


# ── GET /api/reports ──────────────────────────────────────────────────────────

@router.get("/api/reports")
def list_reports(
    agent: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(Report).order_by(Report.bumped_at.desc())

    if agent:
        query = query.filter(Report.agent == agent.lower())

    results = query.all()

    # Tag filtering is done in Python because tags are stored as a JSON string
    if tag:
        results = [r for r in results if tag in json.loads(r.tags or "[]")]

    if limit:
        results = results[:limit]

    return [_report_to_summary(r) for r in results]


# ── GET /api/reports/{id} ─────────────────────────────────────────────────────

@router.get("/api/reports/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_to_full(report)
