"""
Modelo de Barrio/Comuna/Localidad.
Representa las subdivisiones territoriales con códigos oficiales.
- Bogotá: Localidades (código DIVIPOLA de 5 dígitos)
- Medellín: Comunas (código municipio + sufijo de comuna)
"""
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Neighborhood(Base):
    """Entidad Barrio/Comuna/Localidad."""

    __tablename__ = "neighborhoods"

    code = Column(String(20), primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    city_divipola = Column(String(10), ForeignKey("cities.divipola"), nullable=False)
    neighborhood_type = Column(String(20), nullable=False, default="localidad")  # 'localidad' o 'comuna'

    # Relationships
    city = relationship("City", back_populates="neighborhoods")
    persons = relationship("Person", back_populates="neighborhood")

    def __repr__(self):
        return f"<Neighborhood {self.name} ({self.code})>"
