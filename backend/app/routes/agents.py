"""
Agent orchestration routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta

from app.db import get_db
from app.agents.orchestrator import OrchestratorAgent
from app.agents.proposal_generator import ProposalGeneratorAgent
from app.agents.delivery_assistant import DeliveryAssistantAgent
from app.agents.followup import FollowUpAgent
from app.agents.ab_tester import ABTesterAgent
from app.agents.conversion_predictor import ConversionPredictorAgent
from app.models.lead import Lead, LeadStatus
from app.models.outreach import OutreachLog, OutreachStatus
from app.models.proposal import Proposal
from app.models.outcome_event import OutcomeEvent

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


def _lead_to_prediction_input(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "title": lead.title,
        "company": lead.company or "",
        "description": lead.description or "",
        "budget": lead.budget or "",
        "budget_min": lead.budget_min or 0,
        "budget_max": lead.budget_max or 0,
        "source": lead.source or "",
        "tags": lead.tags or "[]",
        "score": lead.score or 0,
        "is_remote": lead.is_remote or 0,
    }


def _budget_value(lead: Lead) -> float:
    budget = max(float(lead.budget_min or 0), float(lead.budget_max or 0))
    if budget == 0:
        budget = ProposalGeneratorAgent._parse_budget_string(lead.budget or "")
    return budget


def _queue_priority_score(lead: Lead, reply_probability: float, deal_probability: float) -> float:
    score = float(lead.score or 0)
    score += min(_budget_value(lead) / 40.0, 35.0)
    score += reply_probability * 40
    score += deal_probability * 60
    text = f"{lead.title or ''} {lead.description or ''}".lower()
    if any(token in text for token in ("java", "spring", "spring boot")):
        score += 15
    if any(token in text for token in ("1 week", "2 week", "2 weeks", "14 days", "asap")):
        score += 10
    return round(score, 3)


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


@router.get("/metrics/daily")
async def get_daily_metrics(db: AsyncSession = Depends(get_db)):
    """
    Key daily metrics:
    proposals/day, replies/day, deals/week, revenue/month.
    """
    from app.models.proposal import Proposal
    from app.models.outreach import OutreachLog, OutreachStatus
    from app.models.lead import Lead, LeadStatus
    from app.models.revenue import Revenue

    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = day_start - timedelta(days=day_start.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Proposals created today
    proposals_today = await db.execute(
        select(func.count()).select_from(Proposal).where(
            Proposal.created_at >= day_start
        )
    )

    # Replies (outreach marked REPLIED) today
    replies_today = await db.execute(
        select(func.count()).select_from(OutreachLog).where(
            OutreachLog.status == OutreachStatus.REPLIED,
            OutreachLog.created_at >= day_start,
        )
    )

    # Deals closed this week
    deals_week = await db.execute(
        select(func.count()).select_from(Lead).where(
            Lead.status == LeadStatus.CLOSED_WON,
            Lead.updated_at >= week_start,
        )
    )

    # Revenue this month
    revenue_month = await db.execute(
        select(func.coalesce(func.sum(Revenue.amount), 0)).where(
            Revenue.created_at >= month_start
        )
    )

    # Auto-sent proposals today
    auto_sent_today = await db.execute(
        select(func.count()).select_from(Proposal).where(
            Proposal.auto_sent.is_(True),
            Proposal.created_at >= day_start,
        )
    )

    return {
        "date": now.date().isoformat(),
        "proposals_today": proposals_today.scalar_one() or 0,
        "auto_sent_today": auto_sent_today.scalar_one() or 0,
        "replies_today": replies_today.scalar_one() or 0,
        "deals_this_week": deals_week.scalar_one() or 0,
        "revenue_this_month_eur": float(revenue_month.scalar_one() or 0),
        "min_20_target_met": (proposals_today.scalar_one() or 0) >= 20,
    }


@router.get("/ab-stats")
async def get_ab_stats(db: AsyncSession = Depends(get_db)):
    """
    A/B variant performance: reply rates, conversion rates, current winner.
    """
    tester = ABTesterAgent()
    return await tester.get_stats(db)


@router.get("/predict/{lead_id}")
async def predict_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """
    Conversion prediction for a specific lead.
    Returns reply_probability, deal_probability, should_reject, active signals.
    """
    from app.models.lead import Lead
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    import json as _json
    lead_dict = {
        "id": lead.id,
        "title": lead.title,
        "company": lead.company or "",
        "description": lead.description or "",
        "budget": lead.budget or "",
        "budget_min": lead.budget_min or 0,
        "budget_max": lead.budget_max or 0,
        "source": lead.source or "",
        "tags": lead.tags or "[]",
        "score": lead.score or 0,
        "is_remote": lead.is_remote or 0,
    }

    predictor = ConversionPredictorAgent()
    prediction = predictor.predict(lead_dict)
    return {"lead_id": lead_id, "title": lead.title, **prediction}


@router.post("/optimize")
async def run_optimization(db: AsyncSession = Depends(get_db)):
    """
    Trigger an optimization pass:
    - Recalculate A/B winner
    - Return low-reply-rate leads for review
    - Return recommended active variant going forward
    """
    from app.models.outreach import OutreachLog, OutreachStatus
    from sqlalchemy import text

    tester = ABTesterAgent()
    ab_stats = await tester.get_stats(db)
    recommended_variant = tester.select_variant(ab_stats)

    # Leads with pending outreach older than 10 days (candidates to close out)
    cutoff = datetime.now(timezone.utc) - timedelta(days=10)
    stale_result = await db.execute(
        select(func.count()).select_from(OutreachLog).where(
            OutreachLog.status == OutreachStatus.PENDING,
            OutreachLog.created_at <= cutoff,
        )
    )
    stale_count = stale_result.scalar_one() or 0

    return {
        "optimized_at": datetime.now(timezone.utc).isoformat(),
        "recommended_variant": recommended_variant,
        "ab_stats": ab_stats,
        "stale_pending_outreach": stale_count,
        "action": (
            f"Switch to variant {recommended_variant} for new proposals. "
            f"{stale_count} stale outreach messages older than 10 days should be reviewed."
        ),
    }


@router.get("/action-queue")
async def get_action_queue(db: AsyncSession = Depends(get_db)):
    """
    Revenue-first approval queue with send policy, top actions, and persistent-learning context.
    """
    tester = ABTesterAgent()
    predictor = ConversionPredictorAgent()
    proposal_gen = ProposalGeneratorAgent()

    ab_stats = await tester.get_stats(db)
    best_variant = ab_stats.get("winner") or tester.select_variant(ab_stats)

    pending_result = await db.execute(
        select(OutreachLog).where(OutreachLog.status == OutreachStatus.PENDING).order_by(OutreachLog.created_at.desc())
    )
    pending_logs = pending_result.scalars().all()

    items = []
    auto_send_ready = 0
    manual_review = 0

    for log in pending_logs:
        lead_result = await db.execute(select(Lead).where(Lead.id == log.lead_id))
        lead = lead_result.scalar_one_or_none()
        if not lead:
            continue

        proposal_result = await db.execute(
            select(Proposal)
            .where(Proposal.lead_id == lead.id, Proposal.variant == log.variant)
            .order_by(Proposal.created_at.desc())
        )
        proposal = proposal_result.scalars().first()

        lead_input = _lead_to_prediction_input(lead)
        prediction = predictor.predict(lead_input)
        reply_probability = proposal.reply_probability if proposal else prediction["reply_probability"]
        deal_probability = proposal.deal_probability if proposal else prediction["deal_probability"]
        send_policy = proposal_gen.get_send_policy(lead_input)
        priority_score = _queue_priority_score(lead, reply_probability, deal_probability)

        if send_policy["auto_send_eligible"] and not send_policy["manual_review_required"]:
            auto_send_ready += 1
        if send_policy["manual_review_required"]:
            manual_review += 1

        items.append(
            {
                "lead_id": lead.id,
                "title": lead.title,
                "company": lead.company or "",
                "platform": log.channel.value,
                "budget_value": _budget_value(lead),
                "budget": lead.budget or "",
                "score": lead.score or 0,
                "reply_probability": round(reply_probability, 3),
                "deal_probability": round(deal_probability, 3),
                "chosen_variant": proposal.variant if proposal else log.variant,
                "proposal_id": proposal.id if proposal else None,
                "outreach_id": log.id,
                "proposal_preview": (proposal.short_pitch or proposal.proposal_text[:180]) if proposal else "",
                "outreach_preview": log.message[:180],
                "auto_send_eligible": send_policy["auto_send_eligible"],
                "manual_review_required": send_policy["manual_review_required"],
                "policy_label": send_policy["policy_label"],
                "priority_score": priority_score,
                "stack": lead.tags or "[]",
                "status": log.status.value,
                "reason_to_act": (
                    "High-value, fast-delivery lead"
                    if priority_score >= 120
                    else "Strong reply/deal probability"
                ),
            }
        )

    items.sort(key=lambda item: item["priority_score"], reverse=True)

    rejected_result = await db.execute(
        select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.REJECTED)
    )
    feedback_result = await db.execute(select(func.count()).select_from(OutcomeEvent))

    return {
        "summary": {
            "auto_send_ready": auto_send_ready,
            "needs_manual_approval": manual_review,
            "rejected_by_predictor": rejected_result.scalar_one() or 0,
            "best_variant_today": best_variant,
            "top_action_count": min(len(items), 5),
            "feedback_events_logged": feedback_result.scalar_one() or 0,
        },
        "policy": {
            "upwork": "Manual review",
            "linkedin": "Manual review",
            "freelancer": "Manual review",
            "email": "Optional auto-send only for trusted templates",
        },
        "ab_stats": ab_stats,
        "items": items,
        "top_action_leads": items[:5],
    }
