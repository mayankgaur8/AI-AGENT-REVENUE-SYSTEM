from sqlalchemy import Column, Integer, Text, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    proposal_text = Column(Text, nullable=False)
    short_pitch = Column(Text)
    technical_approach = Column(Text)
    email_subject = Column(String(300))          # cold email subject line
    email_body = Column(Text)                    # full cold email body
    variant = Column(String(2), default="A")     # "A" = technical, "B" = business
    word_count = Column(Integer, default=0)
    auto_sent = Column(Boolean, default=False)   # True when auto-sent (score≥70, budget≥€300)
    reply_probability = Column(Float, default=0) # predicted reply probability 0–1
    deal_probability = Column(Float, default=0)  # predicted deal close probability 0–1
    is_approved = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    lead = relationship("Lead", back_populates="proposals")
