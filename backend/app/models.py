from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text

from .database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True)
    agent = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    tags = Column(Text, default="[]")      # JSON array string
    sections = Column(Text, default="[]")  # JSON array string
    received_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(DateTime(timezone=True), nullable=True)
    # bumped_at drives feed order; equals received_at on create, set to now() on PUT
    bumped_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
