"""
Outreach Agent
Sends proposals via Upwork (simulated), LinkedIn, and Email.
Requires user approval before sending (IMPORTANT: no fully automated sending).
"""
import logging
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.outreach import OutreachLog, OutreachChannel, OutreachStatus
from app.models.lead import Lead, LeadStatus

logger = logging.getLogger(__name__)


class OutreachAgent:
    """Manages outreach: logs messages and marks them for review before sending."""

    async def prepare_outreach(
        self,
        db: AsyncSession,
        lead_id: int,
        message: str,
        channel: OutreachChannel,
    ) -> OutreachLog:
        """
        Prepare an outreach message (status=PENDING).
        Does NOT send until approved by user.
        """
        log = OutreachLog(
            lead_id=lead_id,
            message=message,
            channel=channel,
            status=OutreachStatus.PENDING,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        logger.info(
            f"OutreachAgent: Prepared {channel} outreach for lead {lead_id} "
            f"(log_id={log.id})"
        )
        return log

    async def approve_and_send(
        self,
        db: AsyncSession,
        outreach_id: int,
    ) -> OutreachLog:
        """
        User approves sending. Simulates the send action.
        In production: integrate actual send logic here.
        """
        result = await db.execute(
            select(OutreachLog).where(OutreachLog.id == outreach_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            raise ValueError(f"OutreachLog {outreach_id} not found")

        # Simulate channel-specific send
        success = await self._simulate_send(log)

        if success:
            log.status = OutreachStatus.SENT
            log.sent_at = datetime.now(timezone.utc)
            logger.info(f"OutreachAgent: Sent outreach {outreach_id} via {log.channel}")

            # Update lead status
            lead_result = await db.execute(
                select(Lead).where(Lead.id == log.lead_id)
            )
            lead = lead_result.scalar_one_or_none()
            if lead and lead.status == LeadStatus.NEW:
                lead.status = LeadStatus.PROPOSAL_SENT
        else:
            log.status = OutreachStatus.FAILED
            log.error_message = "Simulated send failure"
            logger.error(f"OutreachAgent: Failed to send outreach {outreach_id}")

        await db.commit()
        await db.refresh(log)
        return log

    async def _simulate_send(self, log: OutreachLog) -> bool:
        """
        Simulate sending. Replace with real integration:
        - Upwork: Upwork API or manual
        - LinkedIn: LinkedIn API / manual DM
        - Email: SMTP via smtplib or SendGrid
        """
        logger.info(
            f"[SIMULATE] Sending via {log.channel}: "
            f"'{log.message[:80]}...'"
        )
        # Always succeeds in simulation
        return True

    async def get_pending_outreach(self, db: AsyncSession) -> list[OutreachLog]:
        """Return all pending (unreviewed) outreach messages."""
        result = await db.execute(
            select(OutreachLog).where(OutreachLog.status == OutreachStatus.PENDING)
        )
        return result.scalars().all()

    async def get_stats(self, db: AsyncSession) -> dict[str, int]:
        """Return outreach statistics."""
        from sqlalchemy import func

        total_q = await db.execute(select(func.count(OutreachLog.id)))
        sent_q = await db.execute(
            select(func.count(OutreachLog.id)).where(
                OutreachLog.status == OutreachStatus.SENT
            )
        )
        replied_q = await db.execute(
            select(func.count(OutreachLog.id)).where(
                OutreachLog.status == OutreachStatus.REPLIED
            )
        )
        pending_q = await db.execute(
            select(func.count(OutreachLog.id)).where(
                OutreachLog.status == OutreachStatus.PENDING
            )
        )

        return {
            "total": total_q.scalar() or 0,
            "sent": sent_q.scalar() or 0,
            "replied": replied_q.scalar() or 0,
            "pending": pending_q.scalar() or 0,
        }
