"""
A/B Testing Engine
Tracks response rates per variant (A = technical, B = business-focused),
auto-selects the winning variant for new proposals, and exposes stats.
"""
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.proposal import Proposal
from app.models.outreach import OutreachLog, OutreachStatus

logger = logging.getLogger(__name__)

# Minimum samples required before declaring a winner
MIN_SAMPLES_FOR_WINNER = 5


class ABTesterAgent:
    """
    Tracks A/B variant performance from the proposals and outreach_logs tables.
    Variant A = technical focus, Variant B = business/ROI focus.
    """

    async def get_stats(self, db: AsyncSession) -> dict[str, Any]:
        """
        Return per-variant stats: sent, replied, reply_rate, conversion_rate, winner.
        """
        stats: dict[str, Any] = {"A": {}, "B": {}, "winner": None, "reason": ""}

        for variant in ("A", "B"):
            sent = await self._count_sent(db, variant)
            replied = await self._count_replied(db, variant)
            deals = await self._count_deals(db, variant)

            reply_rate = (replied / sent) if sent > 0 else 0.0
            conversion_rate = (deals / sent) if sent > 0 else 0.0

            stats[variant] = {
                "sent": sent,
                "replied": replied,
                "deals": deals,
                "reply_rate": round(reply_rate, 3),
                "conversion_rate": round(conversion_rate, 3),
            }

        winner, reason = self._determine_winner(stats)
        stats["winner"] = winner
        stats["reason"] = reason
        return stats

    def select_variant(self, ab_stats: dict[str, Any]) -> str:
        """
        Return 'A' or 'B' based on current performance data.
        Falls back to 'A' when insufficient data.
        """
        return ab_stats.get("winner") or "A"

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _count_sent(self, db: AsyncSession, variant: str) -> int:
        result = await db.execute(
            select(func.count()).select_from(OutreachLog).where(
                OutreachLog.variant == variant,
                OutreachLog.status == OutreachStatus.SENT,
            )
        )
        return result.scalar_one() or 0

    async def _count_replied(self, db: AsyncSession, variant: str) -> int:
        result = await db.execute(
            select(func.count()).select_from(OutreachLog).where(
                OutreachLog.variant == variant,
                OutreachLog.status == OutreachStatus.REPLIED,
            )
        )
        return result.scalar_one() or 0

    async def _count_deals(self, db: AsyncSession, variant: str) -> int:
        """Count proposals of this variant that were sent AND the lead closed won."""
        from app.models.lead import Lead, LeadStatus
        result = await db.execute(
            select(func.count())
            .select_from(Proposal)
            .join(Lead, Lead.id == Proposal.lead_id)
            .where(
                Proposal.variant == variant,
                Proposal.is_sent.is_(True),
                Lead.status == LeadStatus.CLOSED_WON,
            )
        )
        return result.scalar_one() or 0

    @staticmethod
    def _determine_winner(stats: dict[str, Any]) -> tuple[str | None, str]:
        a = stats["A"]
        b = stats["B"]

        a_sent = a.get("sent", 0)
        b_sent = b.get("sent", 0)

        # Not enough data
        if a_sent < MIN_SAMPLES_FOR_WINNER and b_sent < MIN_SAMPLES_FOR_WINNER:
            return None, f"Insufficient data (need ≥{MIN_SAMPLES_FOR_WINNER} sent per variant)"

        # Only one variant has enough data
        if a_sent < MIN_SAMPLES_FOR_WINNER:
            return "B", "A has insufficient data"
        if b_sent < MIN_SAMPLES_FOR_WINNER:
            return "A", "B has insufficient data"

        # Both have data — use conversion rate, fall back to reply rate
        a_conv = a.get("conversion_rate", 0)
        b_conv = b.get("conversion_rate", 0)

        if a_conv != b_conv:
            winner = "A" if a_conv > b_conv else "B"
            return winner, f"Higher conversion rate ({winner}: {max(a_conv, b_conv):.1%})"

        a_reply = a.get("reply_rate", 0)
        b_reply = b.get("reply_rate", 0)

        if a_reply != b_reply:
            winner = "A" if a_reply > b_reply else "B"
            return winner, f"Higher reply rate ({winner}: {max(a_reply, b_reply):.1%})"

        return "A", "Equal performance — defaulting to A (technical)"
