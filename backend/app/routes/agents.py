"""
Agent orchestration routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.db import get_db
from app.agents.orchestrator import OrchestratorAgent
from app.agents.proposal_generator import ProposalGeneratorAgent
from app.agents.delivery_assistant import DeliveryAssistantAgent
from app.agents.followup import FollowUpAgent

router = APIRouter(prefix="/agents", tags=["agents"])


class RunDailyRequest(BaseModel):
    use_mock: bool = True
    max_leads: int = 20


class DeliveryRequest(BaseModel):
    task_type: str = "code"  # code | bugfix | api_design | documentation | general
    request: str
    context: Optional[str] = ""


class ProposalRequest(BaseModel):
    title: str
    company: Optional[str] = ""
    description: str
    budget: Optional[str] = ""
    source: Optional[str] = ""
    lead_type: Optional[str] = "freelance"
    is_remote: Optional[int] = 1


@router.post("/run-daily")
async def run_daily_pipeline(
    body: RunDailyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute the full daily agent pipeline:
    fetch → score → filter → propose → outreach → followups → stats
    """
    orchestrator = OrchestratorAgent()
    report = await orchestrator.run_daily(
        db=db,
        use_mock=body.use_mock,
        max_leads=body.max_leads,
    )
    return report


@router.post("/leads/fetch")
async def fetch_leads(
    use_mock: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """Fetch leads from all sources (without scoring or saving)."""
    from app.agents.lead_hunter import LeadHunterAgent
    agent = LeadHunterAgent()
    leads = await agent.fetch_all(use_mock=use_mock)
    await agent.close()
    return {"leads": leads, "count": len(leads)}


@router.post("/leads/score")
async def score_leads(
    leads: list[dict],
    db: AsyncSession = Depends(get_db),
):
    """Score a list of leads."""
    from app.agents.scorer import ScorerAgent
    scorer = ScorerAgent()
    scored = scorer.score_leads(leads)
    return {"scored_leads": scored, "qualified_count": len(scored)}


@router.post("/proposal/generate")
async def generate_proposal(body: ProposalRequest):
    """Generate a proposal for a given job description."""
    generator = ProposalGeneratorAgent()
    lead_dict = body.model_dump()
    result = await generator.generate_proposal(lead_dict)
    return result


@router.post("/outreach/send")
async def send_outreach(
    outreach_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Approve and send a pending outreach message."""
    from app.agents.outreach import OutreachAgent
    agent = OutreachAgent()
    log = await agent.approve_and_send(db, outreach_id)
    return {
        "id": log.id,
        "status": log.status,
        "sent_at": log.sent_at,
        "channel": log.channel,
    }


@router.post("/followup/run")
async def run_followups(db: AsyncSession = Depends(get_db)):
    """Check and return all due follow-ups."""
    agent = FollowUpAgent()
    due = await agent.run_due_followups(db)
    return {"due_followups": due, "count": len(due)}


@router.post("/followup/{followup_id}/send")
async def send_followup(followup_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a follow-up as sent (after user approval)."""
    agent = FollowUpAgent()
    followup = await agent.mark_sent(db, followup_id)
    return {"id": followup.id, "stage": followup.stage, "sent_at": followup.sent_at}


@router.post("/delivery/generate")
async def generate_delivery(body: DeliveryRequest):
    """Use AI to help deliver a gig faster."""
    agent = DeliveryAssistantAgent()
    result = await agent.generate(
        task_type=body.task_type,
        request=body.request,
        context=body.context or "",
    )
    return result


@router.get("/revenue/stats")
async def get_revenue_stats(db: AsyncSession = Depends(get_db)):
    """Get full revenue pipeline stats."""
    from app.agents.revenue_tracker import RevenueTrackerAgent
    tracker = RevenueTrackerAgent()
    return await tracker.get_stats(db)
