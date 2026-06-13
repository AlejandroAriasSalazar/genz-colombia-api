"""
Schemas Pydantic para Persona Sintética.
"""
from pydantic import BaseModel


class PersonBase(BaseModel):
    """Schema base de persona sintética."""
    id: str
    edad: int
    sexo: str
    ciudad_divipola: str
    neighborhood_code: str
    estrato: int
    nivel_educativo: str
    ocupacion: str
    acceso_internet: bool
    interes_musical: str
    interes_tecnologico: str
    uso_bicicleta: str


class PersonResponse(PersonBase):
    """Schema de respuesta de persona sintética."""
    pass


class PersonListResponse(BaseModel):
    """Schema de respuesta para lista de personas."""
    count: int
    filters_applied: dict
    persons: list[PersonResponse]
