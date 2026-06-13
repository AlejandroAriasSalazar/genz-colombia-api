"""
Schemas Pydantic para Barrio/Comuna/Localidad.
"""
from pydantic import BaseModel


class NeighborhoodBase(BaseModel):
    """Schema base de barrio/comuna/localidad."""
    code: str
    name: str
    city_divipola: str
    neighborhood_type: str


class NeighborhoodResponse(NeighborhoodBase):
    """Schema de respuesta de barrio/comuna/localidad."""
    pass


class NeighborhoodListResponse(BaseModel):
    """Schema de respuesta para lista de barrios."""
    count: int
    city_divipola: str
    neighborhoods: list[NeighborhoodResponse]
