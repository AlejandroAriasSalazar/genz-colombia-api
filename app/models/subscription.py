"""
Modelo de Suscripción.
Define los tiers y límites de acceso para cada API key.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Subscription(Base):
    """Entidad Suscripción (tier y límites)."""

    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, index=True)
    api_key_hash = Column(String(128), ForeignKey("api_keys.key_hash"), nullable=False, unique=True)
    tier = Column(String(20), nullable=False, default="free")
    queries_per_minute = Column(Integer, nullable=False, default=100)
    queries_per_day = Column(Integer, nullable=False, default=1000)
    max_sample_size = Column(Integer, nullable=False, default=100)
    can_download = Column(String(1), nullable=False, default="N")  # S/N
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    api_key = relationship("APIKey", back_populates="subscription")

    def __repr__(self):
        return f"<Subscription {self.id} ({self.tier})>"
