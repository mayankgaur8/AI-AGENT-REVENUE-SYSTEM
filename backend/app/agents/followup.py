"""
Follow-up Agent
Schedules and sends follow-up messages at Day 2 and a faster second touch.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.followup import FollowUp, FollowUpStage
from app.models.outreach import OutreachLog, OutreachStatus
from app.models.lead import Lead, LeadStatus

logger = logging.getLogger(__name__)

FOLLOWUP_SCHEDULE = {
    FollowUpStage.DAY_2: 2,
    # Use the existing DAY_5 enum slot for a Day 4 follow-up to match the
    # conversion playbook without forcing a schema change.
    FollowUpStage.DAY_5: 4,
    FollowUpStage.DAY_10: 10,
}


class FollowUpAgent:
    """Manages follow-up scheduling and execution."""

    async def schedule_followups(
        self,
        db: AsyncSession,
        lead_id: int,
        proposal_generator,
        lead: dict,
    ) -> list[FollowUp]:
        """Schedule all 3 follow-up stages for a lead after outreach is sent."""
        scheduled = []
        now = datetime.now(timezone.utc)

        for stage, days in FOLLOWUP_SCHEDULE.items():
            # Check if already scheduled
            existing = await db.execute(
                select(FollowUp).where(
                    FollowUp.lead_id == lead_id,
                    FollowUp.stage == stage,
                )
            )
            if existing.scalar_one_or_none():
                logger.debug(f"FollowUpAgent: Stage {stage} already scheduled for lead {lead_id}")
                continue

            # Generate message
            message = await proposal_generator.generate_followup_message(lead, stage.value)

            followup = FollowUp(
                lead_id=lead_id,
                stage=stage,
                message=message,
                scheduled_at=now + timedelta(days=days),
                is_sent=False,
            )
            db.add(followup)
            scheduled.append(followup)
            logger.info(
                f"FollowUpAgent: Scheduled {stage.value} for lead {lead_id} "
                f"at {followup.scheduled_at.date()}"
            )

        await db.commit()
        for f in scheduled:
            await db.refresh(f)
        return scheduled

    async def run_due_followups(self, db: AsyncSession) -> list[dict[str, Any]]:
        """
        Find all due follow-ups and mark them ready to send.
        Returns list of due follow-ups with lead info.
        """
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(FollowUp)
            .where(FollowUp.is_sent == False)
            .where(FollowUp.scheduled_at <= now)
        )
        due = result.scalars().all()

        triggered = []
        for followup in due:
            # Check lead hasn't already responded
            lead_result = await db.execute(
                select(Lead).where(Lead.id == followup.lead_id)
            )
            lead = lead_result.scalar_one_or_none()
            if lead and lead.status in (LeadStatus.RESPONDED, LeadStatus.CLOSED_WON):
                logger.info(f"FollowUpAgent: Skipping follow-up {followup.id} — lead already responded")
                followup.is_sent = True
                continue

            triggered.append({
                "followup_id": followup.id,
                "lead_id": followup.lead_id,
                "stage": followup.stage.value,
                "message": followup.message,
                "scheduled_at": followup.scheduled_at.isoformat(),
                "lead_title": lead.title if lead else "",
                "lead_company": lead.company if lead else "",
            })

        await db.commit()
        logger.info(f"FollowUpAgent: {len(triggered)} follow-ups due")
        return triggered

    async def mark_sent(self, db: AsyncSession, followup_id: int) -> FollowUp:
        """Mark a follow-up as sent after user approval."""
        result = await db.execute(
            select(FollowUp).where(FollowUp.id == followup_id)
        )
        followup = result.scalar_one_or_none()
        if not followup:
            raise ValueError(f"FollowUp {followup_id} not found")

        followup.is_sent = True
        followup.sent_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(followup)
        logger.info(f"FollowUpAgent: Marked follow-up {followup_id} as sent")
        return followup
