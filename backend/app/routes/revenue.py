"""
Revenue management routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from app.db import get_db
from app.agents.outcome_memory import record_outcome_event
from app.models.revenue import Revenue, DealStatus
from app.models.lead import Lead

router = APIRouter(prefix="/revenue", tags=["revenue"])


class DealCreate(BaseModel):
    lead_id: int
    amount: float
    status: DealStatus = DealStatus.PENDING
    notes: Optional[str] = ""


class DealUpdate(BaseModel):
    amount: Optional[float] = None
    status: Optional[DealStatus] = None
    notes: Optional[str] = None


@router.get("/stats")
async def revenue_stats(db: AsyncSession = Depends(get_db)):
    """Full revenue pipeline statistics."""
    from app.agents.revenue_tracker import RevenueTrackerAgent
    tracker = RevenueTrackerAgent()
    return await tracker.get_stats(db)


@router.get("")
async def list_deals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all revenue deals."""
    query = select(Revenue).order_by(Revenue.created_at.desc())
    if status:
        query = query.where(Revenue.status == status)

    total_q = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_q.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    deals = result.scalars().all()

    enriched = []
    for deal in deals:
        lead_result = await db.execute(select(Lead).where(Lead.id == deal.lead_id))
        lead = lead_result.scalar_one_or_none()
        enriched.append({
            "id": deal.id,
            "lead_id": deal.lead_id,
            "lead_title": lead.title if lead else "",
            "lead_company": lead.company if lead else "",
            "amount": deal.amount,
            "currency": deal.currency,
            "status": deal.status,
            "notes": deal.notes,
            "closed_at": deal.closed_at.isoformat() if deal.closed_at else None,
            "created_at": deal.created_at.isoformat() if deal.created_at else None,
        })

    return {"deals": enriched, "total": total, "page": page, "page_size": page_size}


@router.post("")
async def create_deal(body: DealCreate, db: AsyncSession = Depends(get_db)):
    """Record a new deal."""
    from app.agents.revenue_tracker import RevenueTrackerAgent
    tracker = RevenueTrackerAgent()
    deal = await tracker.record_deal(
        db,
        lead_id=body.lead_id,
        amount=body.amount,
        status=body.status,
        notes=body.notes or "",
    )
    lead_result = await db.execute(select(Lead).where(Lead.id == deal.lead_id))
    lead = lead_result.scalar_one_or_none()
    if lead:
        await record_outcome_event(
            db,
            lead=lead,
            revenue=deal,
            event_type="deal_recorded",
            deal_status=deal.status.value if hasattr(deal.status, "value") else str(deal.status),
            deal_value=deal.amount,
        )
    return {
        "id": deal.id,
        "lead_id": deal.lead_id,
        "amount": deal.amount,
        "status": deal.status,
        "created_at": deal.created_at.isoformat() if deal.created_at else None,
    }


@router.patch("/{deal_id}")
async def update_deal(
    deal_id: int,
    body: DealUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a deal (e.g., mark as won/lost)."""
    result = await db.execute(select(Revenue).where(Revenue.id == deal_id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    if body.amount is not None:
        deal.amount = body.amount
    if body.status is not None:
        deal.status = body.status
        if body.status == DealStatus.WON:
            from datetime import datetime, timezone
            deal.closed_at = datetime.now(timezone.utc)
            # Update lead
            lead_result = await db.execute(select(Lead).where(Lead.id == deal.lead_id))
            lead = lead_result.scalar_one_or_none()
            if lead:
                from app.models.lead import LeadStatus
                lead.status = LeadStatus.CLOSED_WON
    if body.notes is not None:
        deal.notes = body.notes

    lead_result = await db.execute(select(Lead).where(Lead.id == deal.lead_id))
    lead = lead_result.scalar_one_or_none()
    if lead:
        await record_outcome_event(
            db,
            lead=lead,
            revenue=deal,
            event_type="deal_updated",
            deal_status=deal.status.value if hasattr(deal.status, "value") else str(deal.status),
            deal_value=deal.amount,
            notes=deal.notes,
        )

    await db.commit()
    await db.refresh(deal)
    return {"id": deal.id, "amount": deal.amount, "status": deal.status}
