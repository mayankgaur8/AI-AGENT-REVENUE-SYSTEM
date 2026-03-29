"""
Proposal management routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from app.db import get_db
from app.agents.outcome_memory import record_outcome_event
from app.models.proposal import Proposal
from app.models.lead import Lead

router = APIRouter(prefix="/proposals", tags=["proposals"])


class ProposalUpdate(BaseModel):
    proposal_text: Optional[str] = None
    short_pitch: Optional[str] = None
    technical_approach: Optional[str] = None
    is_approved: Optional[bool] = None
    is_sent: Optional[bool] = None


@router.get("")
async def list_proposals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_approved: Optional[bool] = None,
    is_sent: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all proposals."""
    query = select(Proposal).order_by(Proposal.created_at.desc())
    if is_approved is not None:
        query = query.where(Proposal.is_approved == is_approved)
    if is_sent is not None:
        query = query.where(Proposal.is_sent == is_sent)

    total_q = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_q.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    proposals = result.scalars().all()

    # Attach lead info
    enriched = []
    for p in proposals:
        lead_result = await db.execute(select(Lead).where(Lead.id == p.lead_id))
        lead = lead_result.scalar_one_or_none()
        enriched.append({
            "id": p.id,
            "lead_id": p.lead_id,
            "lead_title": lead.title if lead else "",
            "lead_company": lead.company if lead else "",
            "lead_score": lead.score if lead else 0,
            "proposal_text": p.proposal_text,
            "short_pitch": p.short_pitch,
            "technical_approach": p.technical_approach,
            "word_count": p.word_count,
            "is_approved": p.is_approved,
            "is_sent": p.is_sent,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {
        "proposals": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{proposal_id}")
async def get_proposal(proposal_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single proposal."""
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return {
        "id": p.id,
        "lead_id": p.lead_id,
        "proposal_text": p.proposal_text,
        "short_pitch": p.short_pitch,
        "technical_approach": p.technical_approach,
        "word_count": p.word_count,
        "is_approved": p.is_approved,
        "is_sent": p.is_sent,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.patch("/{proposal_id}")
async def update_proposal(
    proposal_id: int,
    body: ProposalUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a proposal (edit, approve, mark sent)."""
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if body.proposal_text is not None:
        p.proposal_text = body.proposal_text
        p.word_count = len(body.proposal_text.split())
    if body.short_pitch is not None:
        p.short_pitch = body.short_pitch
    if body.technical_approach is not None:
        p.technical_approach = body.technical_approach
    if body.is_approved is not None:
        p.is_approved = body.is_approved
    if body.is_sent is not None:
        p.is_sent = body.is_sent

    await db.commit()
    await db.refresh(p)
    return {"id": p.id, "is_approved": p.is_approved, "is_sent": p.is_sent}


@router.post("/{proposal_id}/approve")
async def approve_proposal(proposal_id: int, db: AsyncSession = Depends(get_db)):
    """Approve a proposal for sending."""
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    p.is_approved = True
    lead_result = await db.execute(select(Lead).where(Lead.id == p.lead_id))
    lead = lead_result.scalar_one_or_none()
    if lead:
        await record_outcome_event(
            db,
            lead=lead,
            proposal=p,
            event_type="proposal_approved",
            proposal_outcome="approved",
        )
    await db.commit()
    return {"id": p.id, "is_approved": True, "message": "Proposal approved"}


@router.post("/{proposal_id}/reject")
async def reject_proposal(proposal_id: int, db: AsyncSession = Depends(get_db)):
    """Reject a proposal and persist that outcome for later optimization."""
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")

    p.is_approved = False
    p.is_sent = False
    lead_result = await db.execute(select(Lead).where(Lead.id == p.lead_id))
    lead = lead_result.scalar_one_or_none()
    if lead:
        await record_outcome_event(
            db,
            lead=lead,
            proposal=p,
            event_type="proposal_rejected",
            proposal_outcome="rejected",
        )

    await db.commit()
    return {"id": p.id, "is_approved": False, "message": "Proposal rejected"}
