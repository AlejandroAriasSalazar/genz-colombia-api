"""
Endpoint de barrios/comunas/localidades.
Expone las subdivisiones territoriales de cada ciudad.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.neighborhood import Neighborhood
from app.models.city import City
from app.schemas.neighborhood import NeighborhoodResponse, NeighborhoodListResponse

router = APIRouter(tags=["Neighborhoods"])


@router.get(
    "/neighborhoods",
    summary="Listar barrios/comunas/localidades",
    description="Retorna las subdivisiones territoriales de una ciudad específica.",
    response_model=NeighborhoodListResponse,
    response_description="Lista de barrios/comunas/localidades de la ciudad",
)
async def get_neighborhoods(
    city: str = Query(..., description="Código DIVIPOLA de la ciudad (ej: 11001 para Bogotá, 05001 para Medellín)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna las subdivisiones territoriales de una ciudad.

    Para Bogotá retorna las 20 localidades.
    Para Medellín retorna las 16 comunas.

    Parámetros:
        - city: Código DIVIPOLA de la ciudad (query param requerido)

    Retorna 404 si la ciudad no existe.
    """
    # Verificar que la ciudad existe
    city_result = await db.execute(select(City).where(City.divipola == city))
    city_obj = city_result.scalar_one_or_none()

    if not city_obj:
        raise HTTPException(status_code=404, detail=f"Ciudad con DIVIPOLA {city} no encontrada.")

    # Obtener barrios/comunas
    result = await db.execute(
        select(Neighborhood)
        .where(Neighborhood.city_divipola == city)
        .order_by(Neighborhood.code)
    )
    neighborhoods = result.scalars().all()

    return NeighborhoodListResponse(
        count=len(neighborhoods),
        city_divipola=city,
        neighborhoods=[
            NeighborhoodResponse(
                code=n.code,
                name=n.name,
                city_divipola=n.city_divipola,
                neighborhood_type=n.neighborhood_type,
            )
            for n in neighborhoods
        ],
    )
