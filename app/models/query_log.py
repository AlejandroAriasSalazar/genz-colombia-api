"""
Modelo de Query Log para trazabilidad.
Registra todas las consultas a la API para auditoría y análisis de uso.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class QueryLog(Base):
    """Entidad QueryLog (trazabilidad de consultas)."""

    __tablename__ = "query_logs"

    id = Column(String(32), primary_key=True, index=True)
    api_key_hash = Column(String(128), ForeignKey("api_keys.key_hash"), nullable=False)
    endpoint = Column(String(100), nullable=False)
    method = Column(String(10), nullable=False)
    query_params = Column(Text, nullable=True)  # JSON string
    response_status = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    api_key = relationship("APIKey", back_populates="query_logs")

    def __repr__(self):
        return f"<QueryLog {self.id} ({self.endpoint})>"
