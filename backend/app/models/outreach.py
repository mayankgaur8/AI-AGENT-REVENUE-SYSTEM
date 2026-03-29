from sqlalchemy import Column, Integer, Text, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class OutreachChannel(str, enum.Enum):
    UPWORK = "upwork"
    LINKEDIN = "linkedin"
    EMAIL = "email"
    FREELANCER = "freelancer"
    DIRECT = "direct"


class OutreachStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    REPLIED = "replied"


class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    message = Column(Text, nullable=False)
    subject = Column(String(300))               # email subject line (if channel=email)
    channel = Column(SAEnum(OutreachChannel), nullable=False)
    variant = Column(String(2), default="A")    # "A" = technical, "B" = business
    status = Column(SAEnum(OutreachStatus), default=OutreachStatus.PENDING)
    auto_sent = Column(Integer, default=0)      # 1 if auto-sent (no user click required)
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    error_message = Column(Text)

    lead = relationship("Lead", back_populates="outreach_logs")
