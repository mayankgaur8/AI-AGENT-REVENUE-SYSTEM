from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./revenue_agent.db"
    ANTHROPIC_API_KEY: str = ""
    SECRET_KEY: str = "dev-secret-key"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"
    PAYMENT_BASE_URL: str = "http://localhost:3000/payments/checkout"
    AI_PLATFORM_URL: str = ""
    AI_PLATFORM_API_KEY: str = ""
    AI_REQUIRE_APP_KEY: bool = True
    AI_TIMEOUT_MS: int = 60000

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Remotive
    REMOTIVE_API_URL: str = "https://remotive.com/api/remote-jobs"

    # Candidate profile
    CANDIDATE_NAME: str = "Mayank Gaur"
    CANDIDATE_SKILLS: str = "Java, Spring Boot, Microservices, React, AWS, Azure, SQL, Kafka"
    CANDIDATE_YEARS: int = 17

    class Config:
        env_file = ".env"


settings = Settings()
