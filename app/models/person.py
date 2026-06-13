"""
Modelo de Persona Sintética.
Representa individuos sintéticos de la Generación Z colombiana.
Variables demográficas y conductuales con distribuciones realistas.
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Person(Base):
    """Entidad Persona Sintética (Gen Z colombiana)."""

    __tablename__ = "persons"

    # Identificador sintético (hash, no real)
    id = Column(String(32), primary_key=True, index=True)

    # Variables demográficas
    edad = Column(Integer, nullable=False)
    sexo = Column(String(1), nullable=False)  # 'M' o 'F'
    ciudad_divipola = Column(String(10), ForeignKey("cities.divipola"), nullable=False)
    neighborhood_code = Column(String(20), ForeignKey("neighborhoods.code"), nullable=False)
    estrato = Column(Integer, nullable=False)  # 1-6

    # Variables educativas y ocupacionales
    nivel_educativo = Column(String(30), nullable=False)
    ocupacion = Column(String(30), nullable=False)

    # Variables conductuales y de conectividad
    acceso_internet = Column(Boolean, nullable=False, default=True)
    interes_musical = Column(String(30), nullable=False)
    interes_tecnologico = Column(String(30), nullable=False)
    uso_bicicleta = Column(String(20), nullable=False)

    # Relationships
    city = relationship("City", back_populates="persons")
    neighborhood = relationship("Neighborhood", back_populates="persons")

    def __repr__(self):
        return f"<Person {self.id} ({self.edad} años, {self.ciudad_divipola})>"
