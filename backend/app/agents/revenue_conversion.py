"""
Revenue Conversion Agent
Implements the conversion-first execution engine:
outreach optimization, high-value filtering, instant replies,
deal closing, and payment guidance.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

MASTER_CONVERSION_SYSTEM_PROMPT = """
You are a Revenue Conversion AI Agent.

Your job is NOT to generate leads.
Your job is to convert leads into paying clients.

Optimize for:
- replies
- conversations
- closed deals
- revenue

Prioritize revenue over activity. Ignore low-converting patterns. Continuously optimize for deals closed.

This system is NOT an automatic money generator.
It is a: Lead -> Proposal -> Conversation -> Deal -> Payment system.
Human interaction is required to close deals.
""".strip()


class RevenueConversionAgent:
    def __init__(self):
        if settings.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.ai_enabled = True
        else:
            self.client = None
            self.ai_enabled = False

    def priority_tier(self, lead: dict[str, Any]) -> str:
        budget = max(float(lead.get("budget_min") or 0), float(lead.get("budget_max") or 0))
        if budget == 0:
            import re
            numbers = re.findall(r"[\d]+", str(lead.get("budget", "")).replace(",", ""))
            budget = max((float(n) for n in numbers), default=0.0)

        if budget >= 1500:
            return "gold"
        if budget >= 800:
            return "high"
        if budget >= 300:
            return "medium"
        if budget >= 150:
            return "low"
        return "ignore"

    def analyze_lead(self, lead: dict[str, Any]) -> dict[str, str]:
        description = (lead.get("description", "") or "").strip()
        problem = description.split(".")[0].strip() if description else lead.get("title", "") or "general implementation need"
        urgency = "high" if any(token in description.lower() for token in ("urgent", "asap", "immediately", "quick", "1 week", "2 week")) else "normal"
        budget_level = self.priority_tier(lead).upper()
        tech_text = f"{lead.get('title', '')} {description} {lead.get('tags', '')}".lower()
        if "java" in tech_text and "spring" in tech_text:
            tech_match = "strong"
        elif "java" in tech_text or "spring" in tech_text:
            tech_match = "partial"
        else:
            tech_match = "weak"

        complexity = "high" if any(token in tech_text for token in ("microservices", "kafka", "distributed", "architecture")) else "medium"
        return {
            "problem": problem,
            "urgency": urgency,
            "budget_level": budget_level,
            "tech_match": tech_match,
            "complexity": complexity,
        }

    def score_lead(self, lead: dict[str, Any]) -> dict[str, Any]:
        analysis = self.analyze_lead(lead)
        base_score = int(lead.get("score", 0))
        priority = self.priority_tier(lead).upper()

        if analysis["tech_match"] == "strong":
            base_score += 10
        elif analysis["tech_match"] == "partial":
            base_score += 5

        if analysis["urgency"] == "high":
            base_score += 5
        if priority == "GOLD":
            base_score += 10
        elif priority == "HIGH":
            base_score += 6
        elif priority == "LOW":
            base_score -= 5
        elif priority == "IGNORE":
            base_score -= 20

        score = max(0, min(base_score, 100))
        return {
            "score": score,
            "priority": priority,
            "should_reject": score < 70,
            "analysis": analysis,
        }

    def should_focus(self, lead: dict[str, Any]) -> bool:
        return self.priority_tier(lead) in {"medium", "high", "gold"}

    async def generate_outreach_message(self, lead: dict[str, Any]) -> str:
        if self.ai_enabled:
            try:
                prompt = f"""
{MASTER_CONVERSION_SYSTEM_PROMPT}

Generate a high-converting personalized outreach message.
Do not use generic openings like "Hi, I noticed", "I am interested", or "I can help".

Always use this structure:
Hi [Client Name],

Saw your [project/problem] - quick thought:

[Specific insight related to their problem]

I recently helped a client [specific measurable result].

If helpful, I can suggest a quick approach for your case too.

Worth a quick 10-min chat?

Rules:
- Personalize from the job description
- Include one measurable result
- Keep it under 120 words
- Conversational, not formal
- End with a soft CTA

Lead:
Title: {lead.get("title", "")}
Company: {lead.get("company", "")}
Description: {(lead.get("description", "") or "")[:1200]}
Platform: {lead.get("source", "")}
"""
                msg = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=250,
                    system=MASTER_CONVERSION_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text.strip()
            except Exception as exc:
                logger.error("RevenueConversionAgent outreach generation failed: %s", exc)

        title = lead.get("title", "project")
        description = (lead.get("description", "") or "the project requirements").split(".")[0].strip()
        company = lead.get("company", "your team") or "your team"
        return (
            f"Hi {company},\n\n"
            f"Saw your {title} brief - quick thought:\n\n"
            f"{description[:120] or 'The stack and delivery window suggest this needs a fast, low-risk implementation.'}\n\n"
            f"I recently helped a client reduce API latency by 40% with a focused Spring Boot optimization pass.\n\n"
            f"If helpful, I can suggest a quick approach for your case too.\n\n"
            f"Worth a quick 10-min chat?"
        )

    async def generate_instant_reply(self, name: str, context: str, quick_win: str = "") -> str:
        if self.ai_enabled:
            try:
                prompt = f"""
{MASTER_CONVERSION_SYSTEM_PROMPT}

Generate an instant reply using this exact structure:

Hi [Name],

Great to hear from you.

Based on what you shared, I suggest:
- point 1
- point 2
- point 3

I can start with [quick win / first step].

Would you like me to outline a quick plan or jump on a short call?

Keep it confident, concise, and conversion-oriented.

Name: {name}
Context: {context}
Quick win: {quick_win}
"""
                msg = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=300,
                    system=MASTER_CONVERSION_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text.strip()
            except Exception as exc:
                logger.error("RevenueConversionAgent instant reply failed: %s", exc)

        first_step = quick_win or "a quick architecture and scope outline"
        return (
            f"Hi {name},\n\n"
            f"Great to hear from you.\n\n"
            f"Based on what you shared, I suggest:\n"
            f"- clarify the highest-risk requirement first\n"
            f"- lock scope around the fastest revenue-producing deliverable\n"
            f"- ship an initial version quickly, then iterate\n\n"
            f"I can start with {first_step}.\n\n"
            f"Would you like me to outline a quick plan or jump on a short call?"
        )

    async def generate_pricing_response(self, requirement: str, solution: str, price_eur: float, timeline_days: int) -> str:
        if self.ai_enabled:
            try:
                prompt = f"""
{MASTER_CONVERSION_SYSTEM_PROMPT}

Create a confident pricing response.
Always anchor value before price and avoid underpricing.

Use this structure:
Based on your requirement, I'd approach it like this:

[brief solution]

Estimated cost: EUR XXX
Timeline: X days

If that works, I can get started immediately.

Requirement: {requirement}
Solution: {solution}
Price: {price_eur}
Timeline days: {timeline_days}
"""
                msg = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=250,
                    system=MASTER_CONVERSION_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text.strip()
            except Exception as exc:
                logger.error("RevenueConversionAgent pricing response failed: %s", exc)

        return (
            f"Based on your requirement, I'd approach it like this:\n\n"
            f"{solution}\n\n"
            f"Estimated cost: EUR {price_eur:,.0f}\n"
            f"Timeline: {timeline_days} days\n\n"
            f"If that works, I can get started immediately."
        )

    def generate_payment_message(self, method: Optional[str] = None) -> str:
        method_text = method or "Stripe/PayPal"
        return (
            f"To proceed, I can share a simple invoice or payment link ({method_text}).\n\n"
            f"Once confirmed, I'll start immediately."
        )

    def generate_payment_payload(
        self,
        *,
        lead_id: Optional[int],
        amount: float,
        currency: str = "EUR",
        method: Optional[str] = "Stripe/PayPal",
    ) -> dict[str, Any]:
        query = urlencode(
            {
                "lead_id": lead_id or "",
                "amount": int(amount),
                "currency": currency,
                "method": method or "Stripe/PayPal",
            }
        )
        payment_link = f"{settings.PAYMENT_BASE_URL}?{query}"
        return {
            "payment_link": payment_link,
            "amount": amount,
            "currency": currency,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def execute_revenue_flow(self, lead: dict[str, Any]) -> dict[str, Any]:
        scoring = self.score_lead(lead)
        if scoring["should_reject"]:
            return {
                "analysis": scoring["analysis"],
                "scoring": {
                    "score": scoring["score"],
                    "priority": scoring["priority"],
                    "should_reject": True,
                },
                "message": None,
            }

        smart_message = await self.generate_outreach_message(lead)
        return {
            "analysis": scoring["analysis"],
            "scoring": {
                "score": scoring["score"],
                "priority": scoring["priority"],
                "should_reject": False,
            },
            "message": smart_message,
        }
