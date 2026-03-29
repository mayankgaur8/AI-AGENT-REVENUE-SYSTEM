"""
Lead management routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from app.db import get_db
from app.models.lead import Lead, LeadStatus

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadUpdate(BaseModel):
    status: Optional[LeadStatus] = None
    score: Optional[int] = None


@router.get("")
async def list_leads(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = None,
    min_score: Optional[int] = Query(default=None, ge=0),
    source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all leads with pagination and filtering."""
    query = select(Lead).order_by(Lead.score.desc(), Lead.created_at.desc())

    if status:
        query = query.where(Lead.status == status)
    if min_score is not None:
        query = query.where(Lead.score >= min_score)
    if source:
        query = query.where(Lead.source == source)

    total_q = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_q.scalar() or 0

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    leads = result.scalars().all()

    return {
        "leads": [_lead_to_dict(l) for l in leads],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{lead_id}")
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single lead with its proposals and outreach."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Lead)
        .options(
            selectinload(Lead.proposals),
            selectinload(Lead.outreach_logs),
            selectinload(Lead.followups),
        )
        .where(Lead.id == lead_id)
    )
    lead = result.scalar_one()
    return _lead_detail_to_dict(lead)


@router.patch("/{lead_id}")
async def update_lead(
    lead_id: int,
    body: LeadUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update lead status or score."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if body.status is not None:
        lead.status = body.status
    if body.score is not None:
        lead.score = body.score

    await db.commit()
    await db.refresh(lead)
    return _lead_to_dict(lead)


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a lead and all related data."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    await db.delete(lead)
    await db.commit()
    return {"message": f"Lead {lead_id} deleted"}


def _lead_to_dict(lead: Lead) -> dict:
    import json
    return {
        "id": lead.id,
        "title": lead.title,
        "company": lead.company,
        "budget": lead.budget,
        "budget_min": lead.budget_min,
        "budget_max": lead.budget_max,
        "url": lead.url,
        "source": lead.source,
        "lead_type": lead.lead_type,
        "score": lead.score,
        "score_reasons": json.loads(lead.score_reasons or "[]"),
        "status": lead.status,
        "is_remote": lead.is_remote,
        "tags": json.loads(lead.tags or "[]"),
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }


def _lead_detail_to_dict(lead: Lead) -> dict:
    base = _lead_to_dict(lead)
    base["description"] = lead.description
    base["proposals"] = [
        {
            "id": p.id,
            "proposal_text": p.proposal_text,
            "short_pitch": p.short_pitch,
            "technical_approach": p.technical_approach,
            "is_approved": p.is_approved,
            "is_sent": p.is_sent,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in lead.proposals
    ]
    base["outreach_logs"] = [
        {
            "id": o.id,
            "channel": o.channel,
            "status": o.status,
            "message": o.message,
            "sent_at": o.sent_at.isoformat() if o.sent_at else None,
        }
        for o in lead.outreach_logs
    ]
    base["followups"] = [
        {
            "id": f.id,
            "stage": f.stage,
            "scheduled_at": f.scheduled_at.isoformat() if f.scheduled_at else None,
            "is_sent": f.is_sent,
        }
        for f in lead.followups
    ]
    return base
