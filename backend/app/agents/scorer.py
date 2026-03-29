"""
Opportunity Scorer Agent
Scores leads based on budget, skill match, remote flag, and delivery timeline.
"""
import logging
import json
import re
from typing import Any

logger = logging.getLogger(__name__)

JAVA_SPRING_KEYWORDS = [
    "java", "spring", "spring boot", "spring-boot", "microservices",
    "kafka", "hibernate", "jpa", "maven", "gradle",
]
HIGH_VALUE_KEYWORDS = [
    "react", "aws", "azure", "kubernetes", "docker", "postgresql",
    "sql", "rest api", "devops", "backend", "fullstack", "full-stack",
]
QUICK_DELIVERY_PATTERNS = [
    r"\b1\s*week", r"\b2\s*week", r"quick", r"urgent", r"asap",
    r"immediately", r"fast\s*turnaround", r"short\s*term",
]
MIN_SCORE_THRESHOLD = 70


class ScorerAgent:
    """Scores and filters leads to find the most promising opportunities."""

    def score_lead(self, lead: dict[str, Any]) -> dict[str, Any]:
        """Score a single lead. Returns lead dict with score and reasons added."""
        score = 0
        reasons = []

        # --- Budget scoring ---
        budget_min = float(lead.get("budget_min") or 0)
        budget_max = float(lead.get("budget_max") or 0)
        budget_value = max(budget_min, budget_max)

        if budget_value >= 1000:
            score += 40
            reasons.append(f"High budget (€{budget_value:.0f})")
        elif budget_value >= 300:
            score += 30
            reasons.append(f"Good budget (€{budget_value:.0f})")
        elif budget_value >= 100:
            score += 10
            reasons.append(f"Low budget (€{budget_value:.0f})")
        else:
            # Try to parse budget string
            budget_str = str(lead.get("budget", "")).lower()
            parsed = self._parse_budget_string(budget_str)
            if parsed >= 1000:
                score += 40
                reasons.append(f"High budget (~€{parsed:.0f})")
            elif parsed >= 300:
                score += 30
                reasons.append(f"Good budget (~€{parsed:.0f})")

        # --- Skill match scoring ---
        full_text = self._get_full_text(lead)

        java_matches = [kw for kw in JAVA_SPRING_KEYWORDS if kw in full_text]
        if len(java_matches) >= 3:
            score += 30
            reasons.append(f"Strong Java/Spring match ({', '.join(java_matches[:3])})")
        elif len(java_matches) >= 1:
            score += 20
            reasons.append(f"Java/Spring match ({', '.join(java_matches)})")

        # Secondary skills
        high_value_matches = [kw for kw in HIGH_VALUE_KEYWORDS if kw in full_text]
        if len(high_value_matches) >= 2:
            score += 15
            reasons.append(f"Tech stack match ({', '.join(high_value_matches[:3])})")
        elif len(high_value_matches) >= 1:
            score += 8
            reasons.append(f"Partial tech match ({', '.join(high_value_matches)})")

        # --- Remote scoring ---
        is_remote = lead.get("is_remote", 0)
        if is_remote or "remote" in full_text:
            score += 20
            reasons.append("Remote position")

        # --- Quick delivery scoring ---
        for pattern in QUICK_DELIVERY_PATTERNS:
            if re.search(pattern, full_text, re.IGNORECASE):
                score += 20
                reasons.append("Quick delivery possible")
                break

        # --- Contract type bonus ---
        if lead.get("lead_type") == "contract":
            score += 10
            reasons.append("Recurring contract")

        result = {
            **lead,
            "score": min(score, 100),
            "score_reasons": json.dumps(reasons),
        }
        logger.debug(f"ScorerAgent: '{lead.get('title', '')[:50]}' scored {score}")
        return result

    def score_leads(self, leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Score all leads and return only those meeting threshold."""
        scored = [self.score_lead(lead) for lead in leads]
        qualified = [l for l in scored if l["score"] >= MIN_SCORE_THRESHOLD]
        # Sort by score descending
        qualified.sort(key=lambda x: x["score"], reverse=True)
        logger.info(
            f"ScorerAgent: {len(leads)} leads → {len(qualified)} qualified "
            f"(threshold={MIN_SCORE_THRESHOLD})"
        )
        return qualified

    def _get_full_text(self, lead: dict) -> str:
        """Combine all text fields for keyword matching."""
        parts = [
            str(lead.get("title", "")),
            str(lead.get("description", "")),
            str(lead.get("tags", "")),
        ]
        return " ".join(parts).lower()

    def _parse_budget_string(self, budget_str: str) -> float:
        """Try to extract a numeric value from a budget string."""
        numbers = re.findall(r"[\d]+", budget_str.replace(",", ""))
        if numbers:
            vals = [float(n) for n in numbers]
            return max(vals)
        return 0.0
