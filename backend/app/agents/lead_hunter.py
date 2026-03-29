"""
Lead Hunter Agent
Fetches freelance/contract opportunities from multiple sources.
"""
import logging
import json
import re
from typing import Any
from datetime import datetime

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

TECH_KEYWORDS = [
    "java", "spring", "spring boot", "microservices", "kafka", "react",
    "aws", "azure", "sql", "postgresql", "api", "backend", "fullstack",
    "full-stack", "rest api", "devops", "docker", "kubernetes", "python",
    "node", "typescript"
]

MOCK_LEADS = [
    {
        "title": "Senior Java Backend Developer - Fintech Startup",
        "company": "FinFlow GmbH",
        "budget": "€800-€1200/month",
        "budget_min": 800,
        "budget_max": 1200,
        "url": "https://upwork.com/jobs/mock-001",
        "description": "We need an experienced Java/Spring Boot developer to build microservices for our payment processing platform. Must know Kafka, PostgreSQL, and AWS. Remote OK. Project: 3 months.",
        "source": "upwork",
        "lead_type": "contract",
        "is_remote": 1,
        "tags": json.dumps(["java", "spring-boot", "kafka", "aws", "microservices"]),
    },
    {
        "title": "React + Node.js Developer for SaaS Dashboard",
        "company": "CloudMetrics Ltd",
        "budget": "€500-€700",
        "budget_min": 500,
        "budget_max": 700,
        "url": "https://freelancer.com/jobs/mock-002",
        "description": "Build an analytics dashboard using React and Node.js. REST API integration required. 2-3 weeks project. Remote.",
        "source": "freelancer",
        "lead_type": "freelance",
        "is_remote": 1,
        "tags": json.dumps(["react", "nodejs", "rest-api", "dashboard"]),
    },
    {
        "title": "Microservices Architecture Consultant",
        "company": "TechScale AG",
        "budget": "€1500-€2000/month",
        "budget_min": 1500,
        "budget_max": 2000,
        "url": "https://linkedin.com/jobs/mock-003",
        "description": "Design and implement microservices architecture for our e-commerce platform. Experience with Spring Boot, Docker, Kubernetes required. Long-term contract.",
        "source": "linkedin",
        "lead_type": "contract",
        "is_remote": 1,
        "tags": json.dumps(["microservices", "spring-boot", "docker", "kubernetes"]),
    },
    {
        "title": "Bug Fix & Code Review - Java API",
        "company": "RetailTech BV",
        "budget": "€150-€300",
        "budget_min": 150,
        "budget_max": 300,
        "url": "https://upwork.com/jobs/mock-004",
        "description": "Fix bugs in existing Java REST API. Spring Boot backend, MySQL database. Quick turnaround needed within 1 week.",
        "source": "upwork",
        "lead_type": "freelance",
        "is_remote": 1,
        "tags": json.dumps(["java", "rest-api", "bug-fix", "mysql"]),
    },
    {
        "title": "Azure Cloud Migration Specialist",
        "company": "LogiCorp SE",
        "budget": "€1000-€1500/month",
        "budget_min": 1000,
        "budget_max": 1500,
        "url": "https://remotive.com/jobs/mock-005",
        "description": "Migrate on-premise Java applications to Azure cloud. Must have Azure certifications or strong hands-on experience. 6-month contract. Fully remote.",
        "source": "remotive",
        "lead_type": "contract",
        "is_remote": 1,
        "tags": json.dumps(["azure", "java", "cloud-migration", "microservices"]),
    },
    {
        "title": "Kafka Streams Developer",
        "company": "DataStream Inc",
        "budget": "€700-€900",
        "budget_min": 700,
        "budget_max": 900,
        "url": "https://remoteok.com/jobs/mock-006",
        "description": "Implement real-time data pipelines using Kafka Streams and Spring Boot. AWS environment. 4-6 week engagement.",
        "source": "remoteok",
        "lead_type": "freelance",
        "is_remote": 1,
        "tags": json.dumps(["kafka", "spring-boot", "aws", "data-pipeline"]),
    },
    {
        "title": "Full Stack Developer (React + Spring Boot)",
        "company": "HealthTech Ventures",
        "budget": "€400-€600",
        "budget_min": 400,
        "budget_max": 600,
        "url": "https://upwork.com/jobs/mock-007",
        "description": "Build a patient management portal. React frontend, Spring Boot backend, PostgreSQL. Remote-first company. 6-8 weeks.",
        "source": "upwork",
        "lead_type": "freelance",
        "is_remote": 1,
        "tags": json.dumps(["react", "spring-boot", "postgresql", "fullstack"]),
    },
    {
        "title": "API Design & Documentation",
        "company": "OpenAPI Systems",
        "budget": "€200-€350",
        "budget_min": 200,
        "budget_max": 350,
        "url": "https://freelancer.com/jobs/mock-008",
        "description": "Design and document REST APIs using OpenAPI/Swagger. Existing Spring Boot codebase. 1-2 weeks.",
        "source": "freelancer",
        "lead_type": "freelance",
        "is_remote": 1,
        "tags": json.dumps(["api-design", "swagger", "spring-boot", "rest"]),
    },
]


class LeadHunterAgent:
    """Fetches earning opportunities from multiple job sources."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_all(self, use_mock: bool = True) -> list[dict[str, Any]]:
        """Fetch leads from all sources."""
        leads = []
        logger.info("LeadHunterAgent: Starting lead fetch")

        if use_mock:
            leads.extend(MOCK_LEADS)
            logger.info(f"LeadHunterAgent: Loaded {len(MOCK_LEADS)} mock leads")

        # Fetch from Remotive (free, no auth needed)
        try:
            remotive_leads = await self._fetch_remotive()
            leads.extend(remotive_leads)
        except Exception as e:
            logger.warning(f"LeadHunterAgent: Remotive fetch failed: {e}")

        # Deduplicate by URL
        seen_urls = set()
        unique_leads = []
        for lead in leads:
            url = lead.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_leads.append(lead)

        logger.info(f"LeadHunterAgent: Total unique leads fetched: {len(unique_leads)}")
        return unique_leads

    async def _fetch_remotive(self) -> list[dict[str, Any]]:
        """Fetch jobs from Remotive API (free, no auth)."""
        leads = []
        search_terms = ["java", "spring", "backend", "api"]

        for term in search_terms:
            try:
                url = f"{settings.REMOTIVE_API_URL}?search={term}&limit=10"
                response = await self.client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    jobs = data.get("jobs", [])
                    for job in jobs[:5]:  # Limit per term
                        lead = self._parse_remotive_job(job)
                        if lead:
                            leads.append(lead)
            except Exception as e:
                logger.warning(f"Remotive fetch for '{term}' failed: {e}")

        logger.info(f"LeadHunterAgent: Fetched {len(leads)} leads from Remotive")
        return leads

    def _parse_remotive_job(self, job: dict) -> dict[str, Any] | None:
        """Parse a Remotive job into our lead format."""
        try:
            description = job.get("description", "") or ""
            # Strip HTML tags
            description = re.sub(r"<[^>]+>", " ", description)
            description = " ".join(description.split())[:1000]

            title = job.get("title", "")
            company = job.get("company_name", "")

            # Extract tech tags
            full_text = f"{title} {description}".lower()
            tags = [kw for kw in TECH_KEYWORDS if kw in full_text]

            # Estimate budget from salary if provided
            salary = job.get("salary") or ""
            budget_min, budget_max = self._parse_salary(str(salary))

            return {
                "title": title[:500],
                "company": company[:200],
                "budget": salary or "Not specified",
                "budget_min": budget_min,
                "budget_max": budget_max,
                "url": job.get("url", "")[:1000],
                "description": description[:2000],
                "source": "remotive",
                "lead_type": "contract",
                "is_remote": 1,
                "tags": json.dumps(tags),
            }
        except Exception as e:
            logger.warning(f"Failed to parse Remotive job: {e}")
            return None

    def _parse_salary(self, salary_str: str) -> tuple[float, float]:
        """Extract min/max budget from salary string."""
        if not salary_str:
            return 0.0, 0.0
        numbers = re.findall(r"[\d,]+", salary_str.replace(",", ""))
        nums = []
        for n in numbers:
            try:
                nums.append(float(n))
            except ValueError:
                pass
        if len(nums) >= 2:
            return min(nums), max(nums)
        elif len(nums) == 1:
            return nums[0], nums[0]
        return 0.0, 0.0

    async def close(self):
        await self.client.aclose()
