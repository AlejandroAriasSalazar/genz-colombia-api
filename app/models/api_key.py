"""
Modelo de API Key para autenticación.
Cada key está asociada a un usuario y un tier de suscripción.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class APIKey(Base):
    """Entidad API Key para autenticación."""

    __tablename__ = "api_keys"

    key_hash = Column(String(128), primary_key=True, index=True)
    key_prefix = Column(String(8), nullable=False)  # Primeros 8 chars para identificación
    name = Column(String(100), nullable=False)
    tier = Column(String(20), nullable=False, default="free")  # free, pro, enterprise
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="api_key", uselist=False)
    query_logs = relationship("QueryLog", back_populates="api_key")

    def __repr__(self):
        return f"<APIKey {self.key_prefix}... ({self.tier})>"
