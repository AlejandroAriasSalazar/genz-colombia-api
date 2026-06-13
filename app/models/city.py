"""
Modelo de Ciudad.
Representa las ciudades del proyecto con códigos DIVIPOLA oficiales.
"""
from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.orm import relationship
from app.database import Base


class City(Base):
    """Entidad Ciudad con código DIVIPOLA oficial."""

    __tablename__ = "cities"

    divipola = Column(String(10), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    population_total = Column(Integer, nullable=False)
    population_genz = Column(Integer, nullable=False)

    # Relationships
    neighborhoods = relationship("Neighborhood", back_populates="city")
    persons = relationship("Person", back_populates="city")

    def __repr__(self):
        return f"<City {self.name} ({self.divipola})>"
