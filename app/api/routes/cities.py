"""
Endpoint de ciudades.
Expone las ciudades disponibles en el dataset con sus códigos DIVIPOLA.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.city import City
from app.schemas.city import CityResponse, CityListResponse

router = APIRouter(tags=["Cities"])


@router.get(
    "/cities",
    summary="Listar ciudades",
    description="Retorna todas las ciudades disponibles en el dataset con sus códigos DIVIPOLA oficiales.",
    response_model=CityListResponse,
    response_description="Lista de ciudades con metadata demográfica",
)
async def get_cities(db: AsyncSession = Depends(get_db)):
    """
    Retorna la lista de ciudades disponibles en el dataset.

    Cada ciudad incluye:
        - divipola: Código DIVIPOLA oficial
        - name: Nombre de la ciudad
        - department: Departamento
        - population_total: Población total (proyección DANE)
        - population_genz: Población estimada de Gen Z (12-28 años)
    """
    result = await db.execute(select(City).order_by(City.name))
    cities = result.scalars().all()

    return CityListResponse(
        count=len(cities),
        cities=[
            CityResponse(
                divipola=c.divipola,
                name=c.name,
                department=c.department,
                population_total=c.population_total,
                population_genz=c.population_genz,
            )
            for c in cities
        ],
    )


@router.get(
    "/cities/{divipola}",
    summary="Obtener ciudad por DIVIPOLA",
    description="Retorna información de una ciudad específica por su código DIVIPOLA.",
    response_model=CityResponse,
    response_description="Información de la ciudad",
)
async def get_city_by_divipola(divipola: str, db: AsyncSession = Depends(get_db)):
    """
    Retorna información de una ciudad específica.

    Parámetros:
        - divipola: Código DIVIPOLA de la ciudad (ej: 11001 para Bogotá)

    Retorna 404 si la ciudad no existe.
    """
    result = await db.execute(select(City).where(City.divipola == divipola))
    city = result.scalar_one_or_none()

    if not city:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Ciudad con DIVIPOLA {divipola} no encontrada.")

    return CityResponse(
        divipola=city.divipola,
        name=city.name,
        department=city.department,
        population_total=city.population_total,
        population_genz=city.population_genz,
    )
