"""
Conversion Predictor
Predicts reply probability and deal-close probability for a lead
using a rule-based scoring model derived from lead signals.
No external ML library required — fast, deterministic, explainable.
"""
import logging
import json
from typing import Any

logger = logging.getLogger(__name__)

# ── Signal weights ─────────────────────────────────────────────────────────────
# Each weight contributes additively to a 0–1 probability.
# Final value is clamped to [0, 1].

REPLY_SIGNALS: list[tuple[str, float]] = [
    # Base: lead score normalised
    ("score_gte_80",   0.25),
    ("score_gte_60",   0.15),
    # Budget
    ("budget_gte_500", 0.15),
    ("budget_gte_200", 0.08),
    # Stack match
    ("java_match",     0.10),
    ("spring_match",   0.08),
    # Platform
    ("upwork",         0.10),
    ("linkedin",       0.07),
    # Completeness
    ("has_company",    0.05),
    ("has_description",0.05),
    ("is_remote",      0.03),
]

DEAL_SIGNALS: list[tuple[str, float]] = [
    ("score_gte_80",    0.30),
    ("score_gte_60",    0.15),
    ("budget_gte_1000", 0.20),
    ("budget_gte_500",  0.12),
    ("budget_gte_200",  0.06),
    ("java_match",      0.08),
    ("spring_match",    0.06),
    ("has_company",     0.04),
    ("upwork",          0.06),
    ("linkedin",        0.04),
]

# Auto-reject if score below this threshold
AUTO_REJECT_SCORE = 40


class ConversionPredictorAgent:
    """
    Predicts reply_probability and deal_probability for a lead dict.
    Also exposes a reject decision for low-quality leads.
    """

    def predict(self, lead: dict[str, Any]) -> dict[str, Any]:
        """
        Returns:
          reply_probability  float 0–1
          deal_probability   float 0–1
          should_reject      bool  — True if lead is too weak to pursue
          signals            list[str] — active signal labels for explainability
        """
        signals = self._extract_signals(lead)
        reply_prob = self._compute(signals, REPLY_SIGNALS)
        deal_prob = self._compute(signals, DEAL_SIGNALS)
        score = int(lead.get("score", 0))

        return {
            "reply_probability": round(reply_prob, 3),
            "deal_probability": round(deal_prob, 3),
            "should_reject": score < AUTO_REJECT_SCORE,
            "signals": signals,
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _extract_signals(self, lead: dict[str, Any]) -> list[str]:
        score = int(lead.get("score", 0))
        budget = self._max_budget(lead)
        source = (lead.get("source", "") or "").lower()
        description = (lead.get("description", "") or "").lower()
        company = lead.get("company", "") or ""

        try:
            tags = json.loads(lead.get("tags", "[]") or "[]")
            tags_lower = [t.lower() for t in tags]
        except Exception:
            tags_lower = []

        text = description + " " + " ".join(tags_lower)

        active: list[str] = []

        if score >= 80:
            active.append("score_gte_80")
        elif score >= 60:
            active.append("score_gte_60")

        if budget >= 1000:
            active.append("budget_gte_1000")
        if budget >= 500:
            active.append("budget_gte_500")
        if budget >= 200:
            active.append("budget_gte_200")

        if any(kw in text for kw in ("java", "jdk", "jvm")):
            active.append("java_match")
        if any(kw in text for kw in ("spring", "spring boot", "springboot")):
            active.append("spring_match")

        if "upwork" in source:
            active.append("upwork")
        elif "linkedin" in source:
            active.append("linkedin")

        if company.strip():
            active.append("has_company")
        if len(description) > 100:
            active.append("has_description")
        if int(lead.get("is_remote", 0)):
            active.append("is_remote")

        return active

    @staticmethod
    def _compute(active_signals: list[str], weight_table: list[tuple[str, float]]) -> float:
        total = 0.0
        for signal, weight in weight_table:
            if signal in active_signals:
                total += weight
        return min(total, 1.0)

    @staticmethod
    def _max_budget(lead: dict[str, Any]) -> float:
        budget = max(
            float(lead.get("budget_min") or 0),
            float(lead.get("budget_max") or 0),
        )
        if budget == 0:
            import re
            raw = str(lead.get("budget", "") or "")
            numbers = re.findall(r"[\d]+", raw.replace(",", ""))
            budget = max((float(n) for n in numbers), default=0.0)
        return budget
