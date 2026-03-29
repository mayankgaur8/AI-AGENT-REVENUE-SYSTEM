from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class OutcomeEvent(Base):
    __tablename__ = "outcome_events"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=True)
    outreach_id = Column(Integer, ForeignKey("outreach_logs.id"), nullable=True)
    revenue_id = Column(Integer, ForeignKey("revenue.id"), nullable=True)

    event_type = Column(String(64), nullable=False)
    platform = Column(String(64), default="")
    variant = Column(String(8), default="")
    niche = Column(String(120), default="")
    stack_snapshot = Column(Text, default="[]")

    reply_received = Column(Boolean, nullable=True)
    proposal_outcome = Column(String(32), nullable=True)
    deal_status = Column(String(32), nullable=True)
    deal_value = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lead = relationship("Lead", back_populates="outcome_events")
