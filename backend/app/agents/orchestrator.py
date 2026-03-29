"""
Orchestrator Agent
Coordinates the full daily pipeline:
1. Fetch leads → 2. Score → 3. Filter top N → 4. Predict conversion
→ 5. Generate A/B proposals (auto-send if eligible) → 6. Prepare outreach
→ 7. Schedule follow-ups → 8. Update revenue stats
Enforces minimum 20 proposals/day.
"""
import logging
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.lead import Lead, LeadStatus
from app.models.proposal import Proposal
from app.models.outreach import OutreachLog, OutreachChannel, OutreachStatus
from app.agents.lead_hunter import LeadHunterAgent
from app.agents.scorer import ScorerAgent
from app.agents.proposal_generator import ProposalGeneratorAgent
from app.agents.ab_tester import ABTesterAgent
from app.agents.conversion_predictor import ConversionPredictorAgent
from app.agents.outreach import OutreachAgent
from app.agents.followup import FollowUpAgent
from app.agents.revenue_tracker import RevenueTrackerAgent

logger = logging.getLogger(__name__)

TOP_LEADS_LIMIT = 20
MIN_PROPOSALS_PER_DAY = 20


class OrchestratorAgent:
    """Coordinates all agents for the daily revenue pipeline run."""

    def __init__(self):
        self.lead_hunter = LeadHunterAgent()
        self.scorer = ScorerAgent()
        self.proposal_gen = ProposalGeneratorAgent()
        self.ab_tester = ABTesterAgent()
        self.predictor = ConversionPredictorAgent()
        self.outreach = OutreachAgent()
        self.followup = FollowUpAgent()
        self.revenue = RevenueTrackerAgent()

    async def run_daily(
        self,
        db: AsyncSession,
        use_mock: bool = True,
        max_leads: int = TOP_LEADS_LIMIT,
    ) -> dict[str, Any]:
        """
        Execute the full daily pipeline.
        Returns a detailed run report.
        """
        run_start = datetime.now(timezone.utc)
        report: dict[str, Any] = {
            "run_at": run_start.isoformat(),
            "steps": {},
            "summary": {},
            "errors": [],
        }

        logger.info("=" * 60)
        logger.info("OrchestratorAgent: Starting daily pipeline run")
        logger.info("=" * 60)

        # ── Step 1: Fetch Leads ──────────────────────────────────────
        try:
            raw_leads = await self.lead_hunter.fetch_all(use_mock=use_mock)
            report["steps"]["fetch"] = {
                "status": "ok",
                "leads_fetched": len(raw_leads),
            }
            logger.info(f"Step 1 — Fetched {len(raw_leads)} raw leads")
        except Exception as e:
            logger.error(f"Step 1 FAILED: {e}")
            report["steps"]["fetch"] = {"status": "error", "error": str(e)}
            report["errors"].append(f"Fetch: {e}")
            raw_leads = []

        # ── Step 2: Score Leads ──────────────────────────────────────
        try:
            scored_leads = self.scorer.score_leads(raw_leads)
            report["steps"]["score"] = {
                "status": "ok",
                "qualified_leads": len(scored_leads),
            }
            logger.info(f"Step 2 — {len(scored_leads)} leads qualified (score ≥ 70)")
        except Exception as e:
            logger.error(f"Step 2 FAILED: {e}")
            report["steps"]["score"] = {"status": "error", "error": str(e)}
            report["errors"].append(f"Score: {e}")
            scored_leads = []

        # ── Step 3: Filter Top Leads (enforce min 20) ────────────────
        target = max(max_leads, MIN_PROPOSALS_PER_DAY)
        top_leads = scored_leads[:target]
        report["steps"]["filter"] = {
            "status": "ok",
            "top_leads": len(top_leads),
            "target": target,
        }
        logger.info(f"Step 3 — Top {len(top_leads)} leads selected (target ≥ {target})")

        # ── Step 4: Load A/B stats for variant selection ─────────────
        try:
            ab_stats = await self.ab_tester.get_stats(db)
            active_variant = self.ab_tester.select_variant(ab_stats)
            report["steps"]["ab_variant"] = {
                "status": "ok",
                "active_variant": active_variant,
                "winner": ab_stats.get("winner"),
                "reason": ab_stats.get("reason"),
            }
            logger.info(f"Step 4 — A/B active variant: {active_variant} ({ab_stats.get('reason')})")
        except Exception as e:
            logger.error(f"Step 4 (A/B) FAILED: {e}")
            ab_stats = {}
            active_variant = "A"
            report["errors"].append(f"AB tester: {e}")

        # ── Step 5 & 6: Save leads, Generate A/B Proposals, Prepare Outreach ──
        proposals_created = 0
        auto_sent_count = 0
        outreach_prepared = 0
        skipped_duplicates = 0
        rejected_count = 0
        new_lead_ids = []

        for lead_data in top_leads:
            try:
                # Conversion prediction — skip auto-reject leads
                prediction = self.predictor.predict(lead_data)
                if prediction["should_reject"]:
                    rejected_count += 1
                    logger.debug(f"Auto-rejected: '{lead_data.get('title', '')[:50]}' (score too low)")
                    continue

                # Check for duplicate (same URL)
                url = lead_data.get("url", "")
                if url:
                    existing = await db.execute(
                        select(Lead).where(Lead.url == url)
                    )
                    if existing.scalar_one_or_none():
                        skipped_duplicates += 1
                        continue

                # Save lead to DB
                lead = Lead(
                    title=lead_data.get("title", "")[:500],
                    company=lead_data.get("company", "")[:200],
                    description=lead_data.get("description", ""),
                    budget=lead_data.get("budget", ""),
                    budget_min=lead_data.get("budget_min", 0),
                    budget_max=lead_data.get("budget_max", 0),
                    url=url[:1000],
                    source=lead_data.get("source", ""),
                    lead_type=lead_data.get("lead_type", "freelance"),
                    tags=lead_data.get("tags", "[]"),
                    score=lead_data.get("score", 0),
                    score_reasons=lead_data.get("score_reasons", "[]"),
                    is_remote=lead_data.get("is_remote", 0),
                    status=LeadStatus.SCORED,
                )
                db.add(lead)
                await db.flush()
                new_lead_ids.append(lead.id)

                # Generate both A/B variants
                ab_proposals = await self.proposal_gen.generate_ab_proposals(lead_data)

                # Generate cold email
                cold_email = await self.proposal_gen.generate_cold_email(lead_data)

                # Determine if auto-send eligible
                is_auto_eligible = self.proposal_gen.is_auto_send_eligible(lead_data)

                for variant_key, proposal_data in ab_proposals.items():
                    proposal_text = proposal_data.get("proposal", "")
                    proposal = Proposal(
                        lead_id=lead.id,
                        proposal_text=proposal_text,
                        short_pitch=proposal_data.get("short_pitch", ""),
                        technical_approach=proposal_data.get("technical_approach", ""),
                        email_subject=cold_email.get("subject", "") if variant_key == active_variant else "",
                        email_body=cold_email.get("body", "") if variant_key == active_variant else "",
                        variant=variant_key,
                        word_count=len(proposal_text.split()),
                        reply_probability=prediction["reply_probability"],
                        deal_probability=prediction["deal_probability"],
                        auto_sent=is_auto_eligible and variant_key == active_variant,
                        is_approved=is_auto_eligible and variant_key == active_variant,
                        is_sent=False,
                    )
                    db.add(proposal)

                proposals_created += 1
                if is_auto_eligible:
                    auto_sent_count += 1
                    lead.status = LeadStatus.PROPOSAL_SENT

                # Prepare outreach (active variant only)
                channel = self._determine_channel(lead_data)
                outreach_msg = await self.proposal_gen.generate_outreach_message(lead_data)
                outreach_log = OutreachLog(
                    lead_id=lead.id,
                    message=outreach_msg,
                    channel=channel,
                    variant=active_variant,
                    status=OutreachStatus.PENDING,
                    auto_sent=1 if is_auto_eligible else 0,
                )
                db.add(outreach_log)
                outreach_prepared += 1

            except Exception as e:
                logger.error(f"Failed processing lead '{lead_data.get('title', '')[:50]}': {e}")
                report["errors"].append(f"Lead processing: {e}")

        await db.commit()

        report["steps"]["proposals"] = {
            "status": "ok",
            "proposals_created": proposals_created,
            "auto_sent": auto_sent_count,
            "skipped_duplicates": skipped_duplicates,
            "auto_rejected": rejected_count,
            "min_target_met": proposals_created >= MIN_PROPOSALS_PER_DAY,
        }
        report["steps"]["outreach"] = {
            "status": "ok",
            "outreach_prepared": outreach_prepared,
            "auto_sent": auto_sent_count,
            "note": "Outreach with auto_sent=1 was sent automatically; others require approval",
        }
        logger.info(
            f"Step 5 — {proposals_created} proposals created "
            f"({auto_sent_count} auto-sent, {rejected_count} rejected)"
        )
        logger.info(f"Step 6 — {outreach_prepared} outreach messages prepared")

        # ── Step 7: Schedule Follow-ups for Already-Sent Outreach ────
        try:
            followup_scheduled = await self._schedule_pending_followups(db)
            report["steps"]["followups"] = {
                "status": "ok",
                "followups_scheduled": followup_scheduled,
            }
            logger.info(f"Step 7 — Scheduled {followup_scheduled} follow-ups")
        except Exception as e:
            logger.error(f"Step 7 FAILED: {e}")
            report["steps"]["followups"] = {"status": "error", "error": str(e)}
            report["errors"].append(f"Followups: {e}")

        # ── Step 8: Revenue Stats ────────────────────────────────────
        try:
            stats = await self.revenue.get_stats(db)
            report["steps"]["revenue"] = {"status": "ok"}
            report["revenue_stats"] = stats
            logger.info(f"Step 8 — Revenue stats: €{stats['revenue']['total_earned_eur']:.0f} earned")
        except Exception as e:
            logger.error(f"Step 8 FAILED: {e}")
            report["steps"]["revenue"] = {"status": "error", "error": str(e)}
            report["errors"].append(f"Revenue: {e}")

        run_end = datetime.now(timezone.utc)
        duration_sec = (run_end - run_start).total_seconds()

        report["summary"] = {
            "new_leads_added": len(new_lead_ids),
            "proposals_created": proposals_created,
            "proposals_auto_sent": auto_sent_count,
            "outreach_pending_approval": outreach_prepared - auto_sent_count,
            "auto_rejected_leads": rejected_count,
            "active_variant": active_variant,
            "min_20_target_met": proposals_created >= MIN_PROPOSALS_PER_DAY,
            "duration_seconds": round(duration_sec, 2),
            "errors": len(report["errors"]),
        }

        logger.info("=" * 60)
        logger.info(f"OrchestratorAgent: Pipeline complete in {duration_sec:.1f}s")
        logger.info(
            f"  New leads: {len(new_lead_ids)}, Proposals: {proposals_created} "
            f"(auto-sent: {auto_sent_count})"
        )
        logger.info("=" * 60)

        await self.lead_hunter.close()
        return report

    async def _schedule_pending_followups(self, db: AsyncSession) -> int:
        """Schedule follow-ups for leads whose outreach was just sent."""
        sent_logs = await db.execute(
            select(OutreachLog).where(OutreachLog.status == OutreachStatus.SENT)
        )
        sent = sent_logs.scalars().all()
        count = 0

        for log in sent:
            lead_result = await db.execute(
                select(Lead).where(Lead.id == log.lead_id)
            )
            lead = lead_result.scalar_one_or_none()
            if not lead:
                continue

            lead_dict = {
                "id": lead.id,
                "title": lead.title,
                "company": lead.company or "",
            }

            scheduled = await self.followup.schedule_followups(
                db, lead.id, self.proposal_gen, lead_dict
            )
            count += len(scheduled)

        return count

    def _determine_channel(self, lead_data: dict) -> OutreachChannel:
        """Pick the best outreach channel based on lead source."""
        source = lead_data.get("source", "").lower()
        if source in ("upwork", "freelancer"):
            return OutreachChannel.UPWORK
        if source == "linkedin":
            return OutreachChannel.LINKEDIN
        return OutreachChannel.EMAIL
