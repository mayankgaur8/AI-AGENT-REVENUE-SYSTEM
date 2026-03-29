"""
Outreach management routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.db import get_db
from app.agents.outcome_memory import record_outcome_event
from app.models.outreach import OutreachLog, OutreachStatus, OutreachChannel
from app.models.lead import Lead

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.get("")
async def list_outreach(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = None,
    channel: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List outreach logs with lead info."""
    query = select(OutreachLog).order_by(OutreachLog.created_at.desc())

    if status:
        query = query.where(OutreachLog.status == status)
    if channel:
        query = query.where(OutreachLog.channel == channel)

    total_q = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_q.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    logs = result.scalars().all()

    enriched = []
    for log in logs:
        lead_result = await db.execute(select(Lead).where(Lead.id == log.lead_id))
        lead = lead_result.scalar_one_or_none()
        enriched.append({
            "id": log.id,
            "lead_id": log.lead_id,
            "lead_title": lead.title if lead else "",
            "lead_company": lead.company if lead else "",
            "message": log.message,
            "channel": log.channel,
            "status": log.status,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {
        "outreach_logs": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# IMPORTANT: /stats must be registered BEFORE /{outreach_id}/... routes so
# FastAPI matches the literal path "stats" before the wildcard parameter.
@router.get("/stats")
async def outreach_stats(db: AsyncSession = Depends(get_db)):
    """Get outreach channel and status statistics."""
    from app.agents.outreach import OutreachAgent
    agent = OutreachAgent()
    return await agent.get_stats(db)


@router.post("/{outreach_id}/approve")
async def approve_and_send(outreach_id: int, db: AsyncSession = Depends(get_db)):
    """User approves and sends a pending outreach message."""
    from app.agents.outreach import OutreachAgent
    agent = OutreachAgent()
    log = await agent.approve_and_send(db, outreach_id)
    return {
        "id": log.id,
        "status": log.status,
        "channel": log.channel,
        "sent_at": log.sent_at.isoformat() if log.sent_at else None,
    }


@router.patch("/{outreach_id}/replied")
async def mark_replied(outreach_id: int, db: AsyncSession = Depends(get_db)):
    """Mark an outreach as replied (update lead status too)."""
    result = await db.execute(select(OutreachLog).where(OutreachLog.id == outreach_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Outreach log not found")

    log.status = OutreachStatus.REPLIED

    from app.models.lead import LeadStatus
    lead_result = await db.execute(select(Lead).where(Lead.id == log.lead_id))
    lead = lead_result.scalar_one_or_none()
    if lead:
        lead.status = LeadStatus.RESPONDED
        await record_outcome_event(
            db,
            lead=lead,
            outreach=log,
            event_type="reply_received",
            reply_received=True,
        )

    await db.commit()
    return {"id": log.id, "status": "replied", "lead_id": log.lead_id}


@router.post("/{outreach_id}/reject")
async def reject_outreach(outreach_id: int, db: AsyncSession = Depends(get_db)):
    """Reject a queued outreach item without sending it."""
    result = await db.execute(select(OutreachLog).where(OutreachLog.id == outreach_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Outreach log not found")

    log.status = OutreachStatus.FAILED
    log.error_message = "Rejected during approval review"

    lead_result = await db.execute(select(Lead).where(Lead.id == log.lead_id))
    lead = lead_result.scalar_one_or_none()
    if lead:
        await record_outcome_event(
            db,
            lead=lead,
            outreach=log,
            event_type="outreach_rejected",
            proposal_outcome="rejected",
            notes="Rejected before external send",
        )

    await db.commit()
    return {"id": log.id, "status": "failed", "message": "Outreach rejected"}
