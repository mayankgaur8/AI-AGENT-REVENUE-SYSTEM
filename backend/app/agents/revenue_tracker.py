"""
Revenue Tracker Agent
Tracks proposals, responses, deals, and overall revenue performance.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.lead import Lead, LeadStatus
from app.models.proposal import Proposal
from app.models.outreach import OutreachLog, OutreachStatus
from app.models.followup import FollowUp
from app.models.revenue import Revenue, DealStatus

logger = logging.getLogger(__name__)

MONTHLY_TARGET_EUR = 2000.0


class RevenueTrackerAgent:
    """Tracks and reports on revenue pipeline performance."""

    async def get_stats(self, db: AsyncSession) -> dict[str, Any]:
        """Comprehensive pipeline stats."""

        # Lead counts
        total_leads = await db.execute(select(func.count(Lead.id)))
        scored_leads = await db.execute(
            select(func.count(Lead.id)).where(Lead.score >= 70)
        )

        # Proposals
        total_proposals = await db.execute(select(func.count(Proposal.id)))
        sent_proposals = await db.execute(
            select(func.count(Proposal.id)).where(Proposal.is_sent == True)
        )

        # Outreach
        outreach_sent = await db.execute(
            select(func.count(OutreachLog.id)).where(
                OutreachLog.status == OutreachStatus.SENT
            )
        )
        outreach_replied = await db.execute(
            select(func.count(OutreachLog.id)).where(
                OutreachLog.status == OutreachStatus.REPLIED
            )
        )

        # Deals
        deals_won = await db.execute(
            select(func.count(Revenue.id)).where(Revenue.status == DealStatus.WON)
        )
        deals_pending = await db.execute(
            select(func.count(Revenue.id)).where(Revenue.status == DealStatus.PENDING)
        )
        deals_lost = await db.execute(
            select(func.count(Revenue.id)).where(Revenue.status == DealStatus.LOST)
        )

        # Revenue totals
        total_revenue = await db.execute(
            select(func.sum(Revenue.amount)).where(Revenue.status == DealStatus.WON)
        )
        pipeline_value = await db.execute(
            select(func.sum(Revenue.amount)).where(Revenue.status == DealStatus.PENDING)
        )

        # Leads by status
        responded_leads = await db.execute(
            select(func.count(Lead.id)).where(Lead.status == LeadStatus.RESPONDED)
        )

        t_leads = total_leads.scalar() or 0
        s_leads = scored_leads.scalar() or 0
        t_proposals = total_proposals.scalar() or 0
        s_proposals = sent_proposals.scalar() or 0
        o_sent = outreach_sent.scalar() or 0
        o_replied = outreach_replied.scalar() or 0
        d_won = deals_won.scalar() or 0
        d_pending = deals_pending.scalar() or 0
        d_lost = deals_lost.scalar() or 0
        rev_total = float(total_revenue.scalar() or 0)
        rev_pipeline = float(pipeline_value.scalar() or 0)
        responded = responded_leads.scalar() or 0

        # Rates
        response_rate = round((o_replied / o_sent * 100), 1) if o_sent > 0 else 0
        conversion_rate = round((d_won / s_proposals * 100), 1) if s_proposals > 0 else 0
        target_progress = round((rev_total / MONTHLY_TARGET_EUR * 100), 1)

        return {
            "summary": {
                "total_leads": t_leads,
                "qualified_leads": s_leads,
                "proposals_generated": t_proposals,
                "proposals_sent": s_proposals,
                "outreach_sent": o_sent,
                "responses_received": o_replied + responded,
                "deals_won": d_won,
                "deals_pending": d_pending,
                "deals_lost": d_lost,
            },
            "revenue": {
                "total_earned_eur": rev_total,
                "pipeline_value_eur": rev_pipeline,
                "monthly_target_eur": MONTHLY_TARGET_EUR,
                "target_progress_pct": target_progress,
                "remaining_to_target_eur": max(0, MONTHLY_TARGET_EUR - rev_total),
            },
            "rates": {
                "response_rate_pct": response_rate,
                "conversion_rate_pct": conversion_rate,
            },
            "health": self._compute_health(
                t_leads, o_sent, o_replied + responded, d_won, rev_total
            ),
        }

    async def record_deal(
        self,
        db: AsyncSession,
        lead_id: int,
        amount: float,
        status: DealStatus = DealStatus.WON,
        notes: str = "",
    ) -> Revenue:
        """Record a deal outcome."""
        revenue = Revenue(
            lead_id=lead_id,
            amount=amount,
            currency="EUR",
            status=status,
            notes=notes,
            closed_at=datetime.now(timezone.utc) if status != DealStatus.PENDING else None,
        )
        db.add(revenue)

        # Update lead status
        lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = lead_result.scalar_one_or_none()
        if lead:
            lead.status = LeadStatus.CLOSED_WON if status == DealStatus.WON else LeadStatus.CLOSED_LOST

        await db.commit()
        await db.refresh(revenue)
        logger.info(f"RevenueTrackerAgent: Recorded {status} deal for lead {lead_id}: €{amount}")
        return revenue

    def _compute_health(
        self,
        leads: int,
        sent: int,
        responses: int,
        won: int,
        revenue: float,
    ) -> str:
        """Simple pipeline health indicator."""
        if revenue >= MONTHLY_TARGET_EUR:
            return "excellent"
        if revenue >= MONTHLY_TARGET_EUR * 0.5:
            return "good"
        if sent >= 10 and responses >= 1:
            return "building"
        if leads >= 5:
            return "starting"
        return "needs_leads"
