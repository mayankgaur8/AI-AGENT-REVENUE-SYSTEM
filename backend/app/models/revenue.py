from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class DealStatus(str, enum.Enum):
    PENDING = "pending"
    WON = "won"
    LOST = "lost"


class Revenue(Base):
    __tablename__ = "revenue"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    amount = Column(Float, default=0)
    currency = Column(String(10), default="EUR")
    status = Column(SAEnum(DealStatus), default=DealStatus.PENDING)
    notes = Column(Text)
    closed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    lead = relationship("Lead", back_populates="revenues")
