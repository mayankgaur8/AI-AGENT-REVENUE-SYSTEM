from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Enum as SAEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class FollowUpStage(str, enum.Enum):
    DAY_2 = "day_2"
    DAY_5 = "day_5"
    DAY_10 = "day_10"


class FollowUp(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    stage = Column(SAEnum(FollowUpStage), nullable=False)
    message = Column(Text)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True))
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lead = relationship("Lead", back_populates="followups")
