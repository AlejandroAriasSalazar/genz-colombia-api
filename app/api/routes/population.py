"""
Endpoint de muestreo de población.
Permite obtener muestras de personas sintéticas con filtros específicos.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.person import Person
from app.schemas.query import PopulationSampleRequest, PopulationSampleResponse

router = APIRouter(tags=["Population"])


@router.post(
    "/population/sample",
    summary="Muestreo de población sintética",
    description="Retorna una muestra de personas sintéticas que cumplen con los filtros especificados.",
    response_model=PopulationSampleResponse,
    response_description="Muestra de personas sintéticas con filtros aplicados",
)
async def get_population_sample(
    request: PopulationSampleRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna una muestra aleatoria de personas sintéticas que cumplen con los filtros.

    Filtros disponibles:
        - ciudad_divipola: Código DIVIPOLA de la ciudad
        - neighborhood_code: Código de barrio/comuna/localidad
        - estrato: Estrato socioeconómico (1-6)
        - edad_min: Edad mínima (12-28)
        - edad_max: Edad máxima (12-28)
        - sexo: Sexo (M o F)
        - nivel_educativo: Nivel educativo
        - ocupacion: Ocupación
        - acceso_internet: Tiene acceso a internet
        - interes_musical: Interés musical
        - interes_tecnologico: Interés tecnológico
        - uso_bicicleta: Frecuencia de uso de bicicleta
        - sample_size: Tamaño de la muestra (1-1000, default 100)

    Nota: Los datos son SINTÉTICOS. No representan individuos reales.
    """
    # Construir query con filtros
    query = select(Person)

    if request.ciudad_divipola:
        query = query.where(Person.ciudad_divipola == request.ciudad_divipola)
    if request.neighborhood_code:
        query = query.where(Person.neighborhood_code == request.neighborhood_code)
    if request.estrato:
        query = query.where(Person.estrato == request.estrato)
    if request.edad_min:
        query = query.where(Person.edad >= request.edad_min)
    if request.edad_max:
        query = query.where(Person.edad <= request.edad_max)
    if request.sexo:
        query = query.where(Person.sexo == request.sexo)
    if request.nivel_educativo:
        query = query.where(Person.nivel_educativo == request.nivel_educativo)
    if request.ocupacion:
        query = query.where(Person.ocupacion == request.ocupacion)
    if request.acceso_internet is not None:
        query = query.where(Person.acceso_internet == request.acceso_internet)
    if request.interes_musical:
        query = query.where(Person.interes_musical == request.interes_musical)
    if request.interes_tecnologico:
        query = query.where(Person.interes_tecnologico == request.interes_tecnologico)
    if request.uso_bicicleta:
        query = query.where(Person.uso_bicicleta == request.uso_bicicleta)

    # Contar total de registros que cumplen filtros
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_matching = total_result.scalar()

    # Aplicar límite de muestra
    sample_size = min(request.sample_size or 100, 1000)
    query = query.limit(sample_size)

    # Ejecutar query
    result = await db.execute(query)
    persons = result.scalars().all()

    # Construir filtros aplicados para respuesta
    filters_applied = {
        k: v for k, v in request.model_dump().items() if v is not None and k != "sample_size"
    }

    return PopulationSampleResponse(
        count=len(persons),
        total_matching=total_matching,
        filters_applied=filters_applied,
        persons=[
            {
                "id": p.id,
                "edad": p.edad,
                "sexo": p.sexo,
                "ciudad_divipola": p.ciudad_divipola,
                "neighborhood_code": p.neighborhood_code,
                "estrato": p.estrato,
                "nivel_educativo": p.nivel_educativo,
                "ocupacion": p.ocupacion,
                "acceso_internet": p.acceso_internet,
                "interes_musical": p.interes_musical,
                "interes_tecnologico": p.interes_tecnologico,
                "uso_bicicleta": p.uso_bicicleta,
            }
            for p in persons
        ],
    )
