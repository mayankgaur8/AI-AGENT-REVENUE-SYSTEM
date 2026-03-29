"""
Tests for the Revenue AI Agent System.
Run: pytest tests/ -v
"""
import pytest
import json
from app.agents.scorer import ScorerAgent
from app.agents.lead_hunter import LeadHunterAgent


# ── Scorer Tests ─────────────────────────────────────────────────────────────

class TestScorerAgent:
    def setup_method(self):
        self.scorer = ScorerAgent()

    def test_high_budget_java_remote_scores_above_70(self):
        lead = {
            "title": "Senior Java Developer",
            "description": "Need Spring Boot microservices developer. Remote OK.",
            "budget": "€800-€1200/month",
            "budget_min": 800,
            "budget_max": 1200,
            "is_remote": 1,
            "tags": json.dumps(["java", "spring-boot", "microservices"]),
            "lead_type": "contract",
            "source": "upwork",
        }
        result = self.scorer.score_lead(lead)
        assert result["score"] >= 70
        assert len(json.loads(result["score_reasons"])) > 0

    def test_low_budget_no_match_scores_below_70(self):
        lead = {
            "title": "WordPress blog setup",
            "description": "Simple blog setup, no coding needed.",
            "budget": "€20",
            "budget_min": 20,
            "budget_max": 20,
            "is_remote": 0,
            "tags": json.dumps(["wordpress"]),
            "lead_type": "freelance",
            "source": "fiverr",
        }
        result = self.scorer.score_lead(lead)
        assert result["score"] < 70

    def test_score_leads_filters_below_threshold(self):
        leads = [
            {
                "title": "Java Spring Boot Developer",
                "description": "Spring Boot microservices, Kafka, AWS. Remote.",
                "budget_min": 1000, "budget_max": 1500,
                "budget": "€1000-1500", "is_remote": 1,
                "tags": json.dumps(["java", "spring-boot", "kafka", "aws"]),
                "lead_type": "contract", "source": "linkedin",
            },
            {
                "title": "Data entry clerk",
                "description": "Type documents",
                "budget_min": 5, "budget_max": 10,
                "budget": "€5-10", "is_remote": 0,
                "tags": json.dumps([]),
                "lead_type": "freelance", "source": "upwork",
            },
        ]
        qualified = self.scorer.score_leads(leads)
        assert len(qualified) == 1
        assert qualified[0]["title"] == "Java Spring Boot Developer"

    def test_score_sorted_by_score_descending(self):
        leads = [
            {
                "title": "React Developer",
                "description": "React, AWS, remote",
                "budget_min": 500, "budget_max": 700,
                "budget": "€500-700", "is_remote": 1,
                "tags": json.dumps(["react", "aws"]),
                "lead_type": "freelance", "source": "upwork",
            },
            {
                "title": "Java Architect",
                "description": "Java Spring Boot microservices Kafka AWS remote contract",
                "budget_min": 1500, "budget_max": 2000,
                "budget": "€1500-2000", "is_remote": 1,
                "tags": json.dumps(["java", "spring-boot", "kafka", "aws", "microservices"]),
                "lead_type": "contract", "source": "linkedin",
            },
        ]
        result = self.scorer.score_leads(leads)
        if len(result) >= 2:
            assert result[0]["score"] >= result[1]["score"]

    def test_remote_flag_adds_points(self):
        base = {
            "title": "Java developer",
            "description": "Java developer needed",
            "budget_min": 500, "budget_max": 500,
            "budget": "€500", "tags": json.dumps(["java"]),
            "lead_type": "freelance", "source": "upwork",
        }
        remote = {**base, "is_remote": 1}
        non_remote = {**base, "is_remote": 0}
        assert self.scorer.score_lead(remote)["score"] > self.scorer.score_lead(non_remote)["score"]


# ── Lead Hunter Tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestLeadHunterAgent:
    async def test_fetch_mock_returns_leads(self):
        agent = LeadHunterAgent()
        leads = await agent.fetch_all(use_mock=True)
        await agent.close()
        assert len(leads) > 0
        for lead in leads:
            assert "title" in lead
            assert "source" in lead
            assert "url" in lead

    async def test_mock_leads_have_required_fields(self):
        agent = LeadHunterAgent()
        leads = await agent.fetch_all(use_mock=True)
        await agent.close()
        required = {"title", "company", "budget", "url", "description", "source", "lead_type"}
        for lead in leads:
            for field in required:
                assert field in lead, f"Missing field: {field}"

    async def test_no_duplicate_urls(self):
        agent = LeadHunterAgent()
        leads = await agent.fetch_all(use_mock=True)
        await agent.close()
        urls = [l["url"] for l in leads if l.get("url")]
        assert len(urls) == len(set(urls)), "Duplicate URLs found"
