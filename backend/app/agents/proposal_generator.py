"""
Proposal Generator Agent
Generates high-converting proposals in two variants (A: technical, B: business-focused)
plus cold email with subject line and LinkedIn DM sequences.
"""
import logging
import json
from typing import Any

import anthropic
from app.config import settings

logger = logging.getLogger(__name__)

# ── Variant A — Technical focus ───────────────────────────────────────────────
PROPOSAL_PROMPT_A = """You are a senior freelance consultant with 17+ years of Java/Spring Boot expertise.
Generate a HIGH-CONVERTING proposal. Be specific, not generic.

JOB TITLE: {title}
DESCRIPTION: {description}
CLIENT BUDGET: {budget}
PLATFORM: {platform}
PLATFORM STYLE: {platform_style}

MY PROFILE:
- 17+ years Java, Spring Boot, Microservices, Kafka, AWS, Azure
- Delivered 50+ systems for fintech, healthtech, enterprise

OUTPUT FORMAT (STRICT — under 150 words total):

🔹 HOOK (1–2 lines): Show you understand their EXACT problem. Use keywords from their description.
🔹 CREDIBILITY (1 line): Relevant experience. Be specific (e.g., "Built 3 similar Spring Boot microservices for fintech").
🔹 SOLUTION APPROACH (2–3 lines): Step-by-step technical plan. Mention their specific stack.
🔹 PROOF (1 line): One similar result. Numbers if possible.
🔹 CTA: Ask ONE smart technical question about their requirements.

RULES:
- Under 150 words
- No "I hope this message finds you well" or generic phrases
- Use keywords from the job description naturally
- Focus on ROI and delivery speed
- Technical, confident tone

Return ONLY valid JSON:
{{
  "proposal": "...",
  "short_pitch": "...(under 50 words, for Upwork title or LinkedIn DM)...",
  "technical_approach": "...(2-3 bullet points, specific stack + reasoning)..."
}}"""

# ── Variant B — Business focus ────────────────────────────────────────────────
PROPOSAL_PROMPT_B = """You are a senior freelance consultant with 17+ years experience.
Generate a HIGH-CONVERTING business-focused proposal. No jargon — think outcomes.

JOB TITLE: {title}
DESCRIPTION: {description}
CLIENT BUDGET: {budget}
PLATFORM: {platform}
PLATFORM STYLE: {platform_style}

MY PROFILE:
- 17+ years delivering Java/Spring Boot systems that save time and cut costs
- Clients: fintech, healthtech, enterprise — measurable outcomes every time

OUTPUT FORMAT (STRICT — under 150 words total):

🔹 HOOK (1–2 lines): Lead with a BUSINESS OUTCOME or problem they're losing money on.
🔹 CREDIBILITY (1 line): A business result you delivered (e.g., "Reduced API latency 60% for a payments client").
🔹 SOLUTION (2 lines): What you'll deliver and by when. Business language, not tech specs.
🔹 PROOF (1 line): ROI number or business impact from a similar engagement.
🔹 CTA: Ask ONE business-level question (timeline, budget, success metric).

RULES:
- Under 150 words
- Lead with ROI and business value, NOT technology
- Avoid tech jargon (no "microservices", "Kafka" etc.)
- Confident, peer-level tone
- Use their exact problem words from the description

Return ONLY valid JSON:
{{
  "proposal": "...",
  "short_pitch": "...(under 50 words, ROI-focused for LinkedIn DM)...",
  "technical_approach": "...(2-3 bullet points in plain business language)..."
}}"""

# ── Cold Email ────────────────────────────────────────────────────────────────
COLD_EMAIL_PROMPT = """Generate a cold outreach email for a freelance opportunity.

JOB/COMPANY: {title} at {company}
THEIR NEED: {description_snippet}

OUTPUT (80–120 words body, separate subject line):

Subject line options:
- Pain-driven: references a problem they likely have
- Curiosity-based: makes them want to know more

Body structure:
1. Problem they're facing (1 sentence, their words)
2. My solution / how I've solved this before (1–2 sentences)
3. Proof: one specific result (numbers help)
4. CTA: one easy yes/no question

RULES:
- Max 120 words body
- Subject max 60 chars
- No "I hope this email finds you well"
- No generic phrases — be specific
- Sound like a peer, not a vendor

Return ONLY valid JSON:
{{
  "subject": "...",
  "body": "..."
}}"""

# ── LinkedIn DM — Day 0 ───────────────────────────────────────────────────────
LINKEDIN_DM_PROMPT = """Write a LinkedIn DM to open a conversation about a freelance opportunity.

JOB: {title} at {company}
CONTEXT: {description_snippet}

Structure (under 80 words):
1. PERSONALIZATION: Reference something specific about them or the job
2. VALUE HOOK: One specific thing you can do that helps THEM
3. SOFT CTA: One easy question — not "are you interested?"

RULES:
- Under 80 words
- No "I hope this message finds you well"
- Sound like a peer reaching out, not a vendor pitching
- One question only at the end
- Use their exact problem language

Return ONLY the message text, nothing else."""

# ── Follow-up sequence ────────────────────────────────────────────────────────
FOLLOWUP_PROMPTS = {
    "day_2": """Write a Day 2 follow-up under 60 words.

Job: {title} at {company}
First follow-up — reference original proposal briefly.
Add ONE small value-add (quick insight or approach idea).
Ask if they have questions. Friendly but professional.

Return ONLY the message text.""",

    "day_5": """Write a Day 5 follow-up that adds real value. Under 80 words.

Job: {title} at {company}
Second follow-up — share a specific insight about their tech problem or industry.
Show you've thought about their situation specifically.
End with a simple yes/no question.

Return ONLY the message text.""",

    "day_10": """Write a final Day 10 follow-up. Under 50 words.

Job: {title} at {company}
Last follow-up — brief, no pressure, close the loop gracefully.
Leave the door open for future work.

Return ONLY the message text.""",
}

AUTO_SEND_SCORE_THRESHOLD = 70
AUTO_SEND_BUDGET_THRESHOLD = 300.0  # EUR
TRUSTED_AUTO_SEND_CHANNELS = {"email", "direct"}


class ProposalGeneratorAgent:
    """
    Generates AI-powered proposals in two variants:
      A — Technical focus (architecture, stack, performance)
      B — Business focus (ROI, outcomes, time-to-market)

    Also generates cold emails with subject lines and LinkedIn DM sequences.
    """

    def __init__(self):
        if settings.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.ai_enabled = True
        else:
            self.client = None
            self.ai_enabled = False
            logger.warning("ProposalGeneratorAgent: No ANTHROPIC_API_KEY — using fallback templates")

    # ── Public API ─────────────────────────────────────────────────────────────

    async def generate_proposal(self, lead: dict[str, Any], variant: str = "A") -> dict[str, str]:
        """Generate a proposal for the given lead in variant A or B."""
        if self.ai_enabled:
            return await self._generate_with_ai(lead, variant)
        return self._fallback_proposal(lead, variant)

    async def generate_ab_proposals(self, lead: dict[str, Any]) -> dict[str, dict]:
        """Generate both A and B variants. Returns {A: {...}, B: {...}}."""
        variant_a = await self.generate_proposal(lead, "A")
        variant_b = await self.generate_proposal(lead, "B")
        return {"A": variant_a, "B": variant_b}

    async def generate_cold_email(self, lead: dict[str, Any]) -> dict[str, str]:
        """Generate a cold email with subject line for the given lead."""
        if self.ai_enabled:
            try:
                prompt = COLD_EMAIL_PROMPT.format(
                    title=lead.get("title", ""),
                    company=lead.get("company", "") or "your company",
                    description_snippet=(lead.get("description", "") or "")[:400],
                )
                msg = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=400,
                    messages=[{"role": "user", "content": prompt}],
                )
                content = self._extract_json(msg.content[0].text)
                result = json.loads(content)
                logger.info(f"ProposalGeneratorAgent: Generated cold email for '{lead.get('title', '')[:50]}'")
                return result
            except Exception as e:
                logger.error(f"Cold email generation failed: {e}")
        return self._fallback_cold_email(lead)

    async def generate_outreach_message(self, lead: dict[str, Any]) -> str:
        """Generate LinkedIn DM Day 0 message."""
        if self.ai_enabled:
            try:
                prompt = LINKEDIN_DM_PROMPT.format(
                    title=lead.get("title", ""),
                    company=lead.get("company", "") or "your company",
                    description_snippet=(lead.get("description", "") or "")[:300],
                )
                msg = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text.strip()
            except Exception as e:
                logger.error(f"LinkedIn DM generation failed: {e}")
        return self._fallback_linkedin_dm(lead)

    async def generate_followup_message(self, lead: dict[str, Any], stage: str) -> str:
        """Generate follow-up message for Day 2 / Day 5 / Day 10."""
        if self.ai_enabled and stage in FOLLOWUP_PROMPTS:
            try:
                prompt = FOLLOWUP_PROMPTS[stage].format(
                    title=lead.get("title", ""),
                    company=lead.get("company", "") or "your company",
                )
                msg = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text.strip()
            except Exception as e:
                logger.error(f"Follow-up generation failed (stage={stage}): {e}")
        return self._fallback_followup(lead, stage)

    def is_auto_send_eligible(self, lead: dict[str, Any]) -> bool:
        """Return True only for trusted email/direct channels and strong leads."""
        channel = self.get_channel_name(lead)
        if channel not in TRUSTED_AUTO_SEND_CHANNELS:
            return False

        score = int(lead.get("score", 0))
        budget = max(
            float(lead.get("budget_min") or 0),
            float(lead.get("budget_max") or 0),
        )
        if budget == 0:
            budget = self._parse_budget_string(str(lead.get("budget", "")))
        return score >= AUTO_SEND_SCORE_THRESHOLD and budget >= AUTO_SEND_BUDGET_THRESHOLD

    def get_channel_name(self, lead: dict[str, Any]) -> str:
        source = (lead.get("source", "") or "").lower()
        if "upwork" in source:
            return "upwork"
        if "freelancer" in source:
            return "freelancer"
        if "linkedin" in source:
            return "linkedin"
        if "direct" in source:
            return "direct"
        return "email"

    def get_send_policy(self, lead: dict[str, Any]) -> dict[str, Any]:
        channel = self.get_channel_name(lead)
        auto_send_eligible = self.is_auto_send_eligible(lead)
        manual_review_required = channel in {"upwork", "freelancer", "linkedin"} or not auto_send_eligible
        return {
            "channel": channel,
            "auto_send_eligible": auto_send_eligible,
            "manual_review_required": manual_review_required,
            "policy_label": (
                "Manual review required"
                if manual_review_required
                else "Trusted template auto-send ready"
            ),
        }

    # ── AI generation ──────────────────────────────────────────────────────────

    async def _generate_with_ai(self, lead: dict[str, Any], variant: str) -> dict[str, str]:
        try:
            prompt_template = PROPOSAL_PROMPT_A if variant == "A" else PROPOSAL_PROMPT_B
            budget_str = lead.get("budget") or f"€{lead.get('budget_min', 0)}–€{lead.get('budget_max', 0)}"
            platform = self._platform_name(lead)
            platform_style = self._platform_style(platform)

            prompt = prompt_template.format(
                title=lead.get("title", ""),
                description=(lead.get("description", "") or "")[:1500],
                budget=budget_str,
                platform=platform,
                platform_style=platform_style,
            )
            msg = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            content = self._extract_json(msg.content[0].text)
            result = json.loads(content)
            logger.info(
                f"ProposalGeneratorAgent: Generated variant {variant} proposal "
                f"for '{lead.get('title', '')[:50]}'"
            )
            return result
        except Exception as e:
            logger.error(f"AI proposal generation failed (variant={variant}): {e}")
            return self._fallback_proposal(lead, variant)

    # ── Fallbacks ──────────────────────────────────────────────────────────────

    def _fallback_proposal(self, lead: dict[str, Any], variant: str) -> dict[str, str]:
        title = lead.get("title", "your project")
        company = lead.get("company", "your team") or "your team"
        platform = self._platform_name(lead)
        import json as _json
        tags = _json.loads(lead.get("tags", "[]") or "[]")
        tech = ", ".join(tags[:3]) if tags else "Java/Spring Boot"

        if variant == "A":
            proposal = (
                f"Your need for {tech} expertise on '{title}' is exactly my wheelhouse. "
                f"I've architected microservices for 3 fintech clients handling 10M+ transactions/day — "
                f"clean domain boundaries, async Kafka messaging, and full observability built in from day one. "
                f"My approach: API contract first → domain service implementation → CI/CD with automated tests. "
                f"I can share a relevant architecture diagram. "
                f"What's your current bottleneck — performance, reliability, or delivery speed?"
            )
            short_pitch = (
                f"17yr Java/Spring expert. Built similar systems on {platform}. "
                f"Can start this week. Worth a chat?"
            )
            approach = (
                "• API-first design with OpenAPI spec, agreed upfront with stakeholders\n"
                "• Domain-driven Spring Boot services, async Kafka for decoupling, Postgres for persistence\n"
                "• Docker + GitHub Actions CI/CD, deployed to cloud with health checks + Grafana dashboards"
            )
        else:
            proposal = (
                f"Companies like yours lose weeks to '{title}'-type challenges — I've seen it repeatedly. "
                f"My last three clients cut their delivery time by 40% and reduced system downtime to near-zero. "
                f"I'll have a working prototype in your hands within the first sprint, "
                f"so you're not paying for months of uncertainty. "
                f"One question: what does success look like for you in the first 30 days?"
            )
            short_pitch = (
                f"40% faster delivery, near-zero downtime — proven results for {company} via {platform}. "
                f"15-min call?"
            )
            approach = (
                "• Week 1: Discovery + working prototype you can see and test\n"
                "• Week 2–3: Full delivery with documentation and handover\n"
                "• Ongoing: Optional retainer for support and iterations"
            )

        return {"proposal": proposal, "short_pitch": short_pitch, "technical_approach": approach}

    def _fallback_cold_email(self, lead: dict[str, Any]) -> dict[str, str]:
        title = lead.get("title", "your opening")
        company = lead.get("company", "your company") or "your company"
        return {
            "subject": f"Java/Spring expert for {title[:40]} — quick question",
            "body": (
                f"Hi,\n\n"
                f"Most {company}-sized teams lose 2–3 weeks on the {title} problem before they get traction. "
                f"I've delivered identical systems for 3 fintech clients, cutting their timeline in half. "
                f"Worth a 15-minute call to see if there's a fit?\n\n"
                f"Best, Mayank"
            ),
        }

    def _fallback_linkedin_dm(self, lead: dict[str, Any]) -> str:
        title = lead.get("title", "your project")
        return (
            f"Hi — noticed you're working on '{title}'. "
            f"I've built very similar systems for 3 clients in the past year "
            f"and could likely save you significant time. "
            f"Are you still actively looking for help?"
        )

    def _fallback_followup(self, lead: dict[str, Any], stage: str) -> str:
        title = lead.get("title", "your project")
        fallbacks = {
            "day_2": f"Hi! Following up on my proposal for '{title}'. Happy to share a quick architecture sketch or code samples. Any questions?",
            "day_5": f"Checking in on '{title}' — I've outlined an approach specific to your stack that might be useful. Still actively looking?",
            "day_10": f"Final check-in on '{title}'. No worries if priorities have shifted — happy to reconnect if this comes up again!",
        }
        return fallbacks.get(stage, "Hi! Following up on my earlier message.")

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_json(text: str) -> str:
        """Strip markdown code fences if present."""
        if "```json" in text:
            return text.split("```json")[1].split("```")[0].strip()
        if "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text.strip()

    @staticmethod
    def _parse_budget_string(budget_str: str) -> float:
        import re
        numbers = re.findall(r"[\d]+", budget_str.replace(",", ""))
        return max((float(n) for n in numbers), default=0.0)

    @staticmethod
    def _platform_name(lead: dict[str, Any]) -> str:
        source = (lead.get("source", "") or "").lower()
        if "upwork" in source:
            return "Upwork"
        if "freelancer" in source:
            return "Freelancer"
        if "linkedin" in source:
            return "LinkedIn DM"
        return "Email"

    @staticmethod
    def _platform_style(platform: str) -> str:
        styles = {
            "Upwork": "Execution-focused. Be concise, specific, and immediately credible. Emphasize shipping fast.",
            "Freelancer": "Competitive and delivery-focused. Highlight scope control, milestones, and reliability.",
            "LinkedIn DM": "Conversational and human. Sound like a peer, not a cold template.",
            "Email": "Business-focused. Lead with ROI, clarity, and a simple CTA.",
        }
        return styles.get(platform, "Professional, direct, and specific.")
