import json
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.outcome_event import OutcomeEvent
from app.models.outreach import OutreachLog
from app.models.proposal import Proposal
from app.models.revenue import Revenue


def _derive_niche(lead: Lead) -> str:
    text = " ".join(
        filter(
            None,
            [
                lead.title or "",
                lead.description or "",
                lead.source or "",
            ],
        )
    ).lower()

    if "fintech" in text or "payment" in text or "bank" in text:
        return "fintech"
    if "health" in text or "med" in text:
        return "healthtech"
    if "e-commerce" in text or "ecommerce" in text:
        return "ecommerce"
    if "saas" in text:
        return "saas"
    return "general"


def _derive_stack_snapshot(lead: Lead) -> str:
    if lead.tags:
        return lead.tags

    text = f"{lead.title or ''} {lead.description or ''}".lower()
    stack = []
    for keyword in ("java", "spring", "spring boot", "kafka", "react", "aws", "azure", "postgresql"):
        if keyword in text:
            stack.append(keyword)
    return json.dumps(stack)


async def record_outcome_event(
    db: AsyncSession,
    *,
    lead: Lead,
    event_type: str,
    proposal: Optional[Proposal] = None,
    outreach: Optional[OutreachLog] = None,
    revenue: Optional[Revenue] = None,
    reply_received: Optional[bool] = None,
    proposal_outcome: Optional[str] = None,
    deal_status: Optional[str] = None,
    deal_value: Optional[float] = None,
    notes: Optional[str] = None,
) -> OutcomeEvent:
    event = OutcomeEvent(
        lead_id=lead.id,
        proposal_id=proposal.id if proposal else None,
        outreach_id=outreach.id if outreach else None,
        revenue_id=revenue.id if revenue else None,
        event_type=event_type,
        platform=(lead.source or outreach.channel.value if outreach else "") if lead else "",
        variant=(proposal.variant if proposal else outreach.variant if outreach else "") or "",
        niche=_derive_niche(lead),
        stack_snapshot=_derive_stack_snapshot(lead),
        reply_received=reply_received,
        proposal_outcome=proposal_outcome,
        deal_status=deal_status,
        deal_value=deal_value,
        notes=notes,
    )
    db.add(event)
    await db.flush()
    return event
