"""
Delivery Assistant Agent
Helps execute gigs faster: code snippets, bug fixes, API designs, documentation.
"""
import logging
from typing import Any

from app.services.ai_client import SharedAIClient, SharedAIError

logger = logging.getLogger(__name__)

DELIVERY_PROMPTS = {
    "code": """You are a senior Java/Spring Boot developer with 17+ years experience.

Generate production-quality code for:
{request}

Context: {context}

Requirements:
- Clean, readable code with proper error handling
- Follow Spring Boot best practices
- Include brief inline comments for non-obvious parts
- Production-ready (not just a proof of concept)

Return only the code with a brief explanation at the top.""",

    "bugfix": """You are a senior Java developer debugging a critical production issue.

Bug description:
{request}

Code/context:
{context}

Analyze the issue and provide:
1. Root cause analysis (2-3 sentences)
2. The fixed code
3. How to prevent this in future

Be precise and actionable.""",

    "api_design": """You are a senior API architect.

Design a REST API for:
{request}

Context: {context}

Provide:
1. OpenAPI/Swagger YAML spec (concise)
2. Key design decisions with brief rationale
3. Any security considerations

Focus on practical, production-ready design.""",

    "documentation": """You are a senior technical writer and developer.

Write clear technical documentation for:
{request}

Context: {context}

Format: Markdown
Include:
- Brief overview
- Prerequisites
- Step-by-step instructions
- Code examples where relevant
- Common troubleshooting points

Keep it concise and developer-friendly.""",

    "general": """You are a senior software consultant with 17+ years experience.

Help with this task:
{request}

Context: {context}

Provide a clear, actionable response. Include code examples if relevant.""",
}


class DeliveryAssistantAgent:
    """Helps deliver freelance gigs faster using AI assistance."""

    def __init__(self):
        self.ai_client = SharedAIClient()
        self.ai_enabled = self.ai_client.enabled

    async def generate(
        self,
        task_type: str,
        request: str,
        context: str = "",
    ) -> dict[str, Any]:
        """
        Generate delivery assistance.

        task_type: code | bugfix | api_design | documentation | general
        """
        if task_type not in DELIVERY_PROMPTS:
            task_type = "general"

        if not self.ai_enabled:
            return {
                "task_type": task_type,
                "request": request,
                "result": "AI not available. Configure AI_PLATFORM_URL and AI_PLATFORM_API_KEY in .env to enable.",
                "tokens_used": 0,
            }

        try:
            prompt = DELIVERY_PROMPTS[task_type].format(
                request=request[:3000],
                context=context[:2000] if context else "Not provided",
            )

            response = await self.ai_client.call_ai(
                prompt=prompt,
                prompt_type=f"delivery_{task_type}",
                max_tokens=2048,
                temperature=0.3,
            )

            result_text = response["reply"]
            usage = response.get("usage") or {}
            tokens = int(usage.get("total_tokens") or 0)

            logger.info(
                f"DeliveryAssistantAgent: Generated {task_type} response "
                f"({tokens} tokens)"
            )

            return {
                "task_type": task_type,
                "request": request,
                "result": result_text,
                "tokens_used": tokens,
            }

        except SharedAIError as e:
            logger.error(f"DeliveryAssistantAgent: Generation failed: {e}")
            return {
                "task_type": task_type,
                "request": request,
                "result": f"Error generating response: {str(e)}",
                "tokens_used": 0,
            }
