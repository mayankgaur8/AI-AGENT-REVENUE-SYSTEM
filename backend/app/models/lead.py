from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class LeadStatus(str, enum.Enum):
    NEW = "new"
    SCORED = "scored"
    PROPOSAL_SENT = "proposal_sent"
    RESPONDED = "responded"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    REJECTED = "rejected"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    company = Column(String(200))
    description = Column(Text)
    budget = Column(String(100))
    budget_min = Column(Float, default=0)
    budget_max = Column(Float, default=0)
    url = Column(String(1000))
    source = Column(String(100))  # upwork, remotive, linkedin, etc.
    lead_type = Column(String(50), default="freelance")  # freelance | contract
    tags = Column(Text)  # JSON string of tags
    score = Column(Integer, default=0)
    score_reasons = Column(Text)  # JSON string
    status = Column(SAEnum(LeadStatus), default=LeadStatus.NEW)
    is_remote = Column(Integer, default=0)  # 0/1
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    proposals = relationship("Proposal", back_populates="lead", cascade="all, delete-orphan")
    outreach_logs = relationship("OutreachLog", back_populates="lead", cascade="all, delete-orphan")
    followups = relationship("FollowUp", back_populates="lead", cascade="all, delete-orphan")
    revenues = relationship("Revenue", back_populates="lead", cascade="all, delete-orphan")
    outcome_events = relationship("OutcomeEvent", back_populates="lead", cascade="all, delete-orphan")
