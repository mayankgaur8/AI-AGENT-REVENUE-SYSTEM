"""
Proposal Generator Agent
Uses Claude AI to generate winning freelance proposals.
"""
import logging
import json
from typing import Any

import anthropic
from app.config import settings

logger = logging.getLogger(__name__)

PROPOSAL_PROMPT = """You are a senior freelance consultant with 17+ years of experience.

Generate a winning freelance proposal for this job.

JOB TITLE: {title}
JOB DESCRIPTION:
{description}

CANDIDATE PROFILE:
- 17+ years experience in Java, Spring Boot, Microservices, React
- Expertise: AWS, Azure, SQL, Kafka, REST APIs, Docker, Kubernetes
- Delivered 50+ projects for fintech, healthtech, and enterprise clients

REQUIREMENTS:
1. Write a MAIN PROPOSAL (150–200 words)
   - Open with a direct statement addressing their problem
   - Show you understand their specific tech requirements
   - Include ONE specific technical insight or approach
   - End with a clear call-to-action
   - Confident, professional tone (not salesy)

2. Write a SHORT PITCH (under 50 words)
   - Perfect for LinkedIn DM or Upwork title

3. Write a TECHNICAL APPROACH (2-3 bullet points)
   - Specific implementation approach
   - Tech stack choices with brief reasoning

Return ONLY valid JSON in this exact format:
{{
  "proposal": "...",
  "short_pitch": "...",
  "technical_approach": "..."
}}"""

OUTREACH_PROMPT = """Write a LinkedIn outreach message under 80 words.

Goal: Get a reply. Not spammy. Professional.

Context:
- You are reaching out about: {title} at {company}
- Your background: 17+ years Java/Spring Boot/Microservices expert
- Their need: {description_snippet}

Rules:
- Mention ONE specific relevant skill that matches their need
- Ask a simple, easy-to-answer question at the end
- No generic phrases like "I hope this message finds you well"
- Sound like a peer, not a vendor

Return ONLY the message text, nothing else."""

FOLLOWUP_PROMPTS = {
    "day_2": """Write a polite Day 2 follow-up message (under 60 words).

Context:
- You sent a proposal for: {title} at {company}
- This is the first follow-up

Rules:
- Reference your original proposal briefly
- Add ONE small value-add (a quick insight or relevant link concept)
- Ask if they have any questions
- Friendly but professional

Return ONLY the message text.""",

    "day_5": """Write a Day 5 follow-up message that adds value (under 80 words).

Context:
- Job: {title} at {company}
- This is the second follow-up

Rules:
- Mention a relevant insight about their tech stack or problem
- Show you've thought about their specific situation
- Keep it conversational
- End with a simple yes/no question

Return ONLY the message text.""",

    "day_10": """Write a final Day 10 follow-up message (under 50 words).

Context:
- Job: {title} at {company}
- This is the last follow-up

Rules:
- Keep it very brief
- No pressure, just closing the loop
- Leave the door open for future work
- Graceful exit

Return ONLY the message text.""",
}


class ProposalGeneratorAgent:
    """Generates AI-powered proposals and outreach messages using Claude."""

    def __init__(self):
        if settings.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.ai_enabled = True
        else:
            self.client = None
            self.ai_enabled = False
            logger.warning("ProposalGeneratorAgent: No ANTHROPIC_API_KEY — using fallback templates")

    async def generate_proposal(self, lead: dict[str, Any]) -> dict[str, str]:
        """Generate a full proposal for a lead."""
        if self.ai_enabled:
            return await self._generate_with_ai(lead)
        return self._generate_fallback_proposal(lead)

    async def _generate_with_ai(self, lead: dict[str, Any]) -> dict[str, str]:
        """Generate proposal using Claude."""
        try:
            prompt = PROPOSAL_PROMPT.format(
                title=lead.get("title", ""),
                description=(lead.get("description", "") or "")[:2000],
            )
            message = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            content = message.content[0].text.strip()
            # Extract JSON even if wrapped in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            result = json.loads(content)
            logger.info(f"ProposalGeneratorAgent: Generated AI proposal for '{lead.get('title', '')[:50]}'")
            return result
        except Exception as e:
            logger.error(f"ProposalGeneratorAgent: AI generation failed: {e}")
            return self._generate_fallback_proposal(lead)

    def _generate_fallback_proposal(self, lead: dict[str, Any]) -> dict[str, str]:
        """Fallback template-based proposal when AI is unavailable."""
        title = lead.get("title", "your project")
        company = lead.get("company", "your team")
        tags = json.loads(lead.get("tags", "[]") or "[]")
        tech_mentioned = ", ".join(tags[:3]) if tags else "Java/Spring Boot"

        proposal = (
            f"Hi, I'm a senior developer with 17+ years specializing in {tech_mentioned} — "
            f"exactly what you need for '{title}'.\n\n"
            f"Having built microservices architectures for fintech and enterprise clients at scale, "
            f"I understand the performance and reliability requirements involved. "
            f"My approach would be to start with a quick discovery call to understand your constraints, "
            f"then deliver a clean, well-tested implementation in phases.\n\n"
            f"I've worked extensively with the stack mentioned and can hit the ground running from day one. "
            f"Happy to share relevant code samples or a quick technical overview of my approach. "
            f"When would work for a 15-minute call?"
        )

        short_pitch = (
            f"17yr Java/Spring Boot expert — built similar systems for 3 clients. "
            f"Can start immediately. Worth a quick chat?"
        )

        technical_approach = (
            f"• Start with API contract definition using OpenAPI, ensuring clean interface boundaries\n"
            f"• Implement domain-driven microservices with Spring Boot, using async Kafka messaging for decoupling\n"
            f"• CI/CD pipeline with Docker + GitHub Actions, deployed to cloud with health checks and observability"
        )

        return {
            "proposal": proposal,
            "short_pitch": short_pitch,
            "technical_approach": technical_approach,
        }

    async def generate_outreach_message(self, lead: dict[str, Any]) -> str:
        """Generate a short LinkedIn/email outreach message."""
        if self.ai_enabled:
            try:
                description = (lead.get("description", "") or "")[:300]
                prompt = OUTREACH_PROMPT.format(
                    title=lead.get("title", ""),
                    company=lead.get("company", ""),
                    description_snippet=description,
                )
                message = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=256,
                    messages=[{"role": "user", "content": prompt}],
                )
                return message.content[0].text.strip()
            except Exception as e:
                logger.error(f"Outreach AI generation failed: {e}")

        # Fallback
        return (
            f"Hi! I noticed you're looking for help with '{lead.get('title', 'your project')}'. "
            f"With 17+ years in Java/Spring Boot and microservices, I've delivered similar systems. "
            f"Would a quick 15-minute call be worthwhile?"
        )

    async def generate_followup_message(self, lead: dict[str, Any], stage: str) -> str:
        """Generate a follow-up message for a given stage."""
        if self.ai_enabled and stage in FOLLOWUP_PROMPTS:
            try:
                prompt = FOLLOWUP_PROMPTS[stage].format(
                    title=lead.get("title", ""),
                    company=lead.get("company", ""),
                )
                message = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}],
                )
                return message.content[0].text.strip()
            except Exception as e:
                logger.error(f"Follow-up AI generation failed: {e}")

        # Fallback templates
        fallbacks = {
            "day_2": f"Hi! Just following up on my proposal for '{lead.get('title', '')}'. Happy to answer any questions or share code samples. Let me know!",
            "day_5": f"Checking in on '{lead.get('title', '')}' — I've worked through a few approaches and have some thoughts that might help. Are you still actively looking?",
            "day_10": f"Final check-in on '{lead.get('title', '')}'. No worries if you've moved on — happy to help if anything comes up in the future!",
        }
        return fallbacks.get(stage, "Hi! Following up on my earlier message.")
