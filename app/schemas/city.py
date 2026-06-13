"""
Schemas Pydantic para Ciudad.
"""
from pydantic import BaseModel


class CityBase(BaseModel):
    """Schema base de ciudad."""
    divipola: str
    name: str
    department: str
    population_total: int
    population_genz: int


class CityResponse(CityBase):
    """Schema de respuesta de ciudad."""
    pass


class CityListResponse(BaseModel):
    """Schema de respuesta para lista de ciudades."""
    count: int
    cities: list[CityResponse]
