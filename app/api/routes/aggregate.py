"""
Endpoint de consultas de agregación.
Permite realizar agregaciones sobre la población sin exponer microdatos.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from collections import defaultdict

from app.database import get_db
from app.models.person import Person
from app.schemas.query import AggregateQueryRequest, AggregateQueryResponse, AggregateResult

router = APIRouter(tags=["Aggregate"])


@router.post(
    "/aggregate/query",
    summary="Consulta de agregación",
    description="Retorna resultados agregados (conteos, promedios, porcentajes) sin exponer microdatos individuales.",
    response_model=AggregateQueryResponse,
    response_description="Resultados de la agregación",
)
async def get_aggregate_query(
    request: AggregateQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Realiza consultas de agregación sobre la población sintética.

    Métricas disponibles:
        - count: Conteo de registros por grupo
        - avg_edad: Promedio de edad por grupo
        - pct_internet: Porcentaje con acceso a internet por grupo

    Agrupaciones permitidas (group_by):
        - ciudad_divipola
        - neighborhood_code
        - estrato
        - sexo
        - nivel_educativo
        - ocupacion
        - interes_musical
        - interes_tecnologico
        - uso_bicicleta

    Filtros disponibles (mismos que /population/sample).

    Nota: Esta endpoint NO expone microdatos. Solo retorna agregaciones.
    """
    # Validar métrica
    valid_metrics = ["count", "avg_edad", "pct_internet"]
    if request.metric not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Métrica inválida. Debe ser una de: {valid_metrics}",
        )

    # Validar group_by
    valid_group_by = [
        "ciudad_divipola", "neighborhood_code", "estrato", "sexo",
        "nivel_educativo", "ocupacion", "interes_musical",
        "interes_tecnologico", "uso_bicicleta",
    ]
    for field in request.group_by:
        if field not in valid_group_by:
            raise HTTPException(
                status_code=400,
                detail=f"Campo de agrupación inválido: {field}. Debe ser uno de: {valid_group_by}",
            )

    # Construir query base con filtros
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

    # Ejecutar query para obtener datos
    result = await db.execute(query)
    persons = result.scalars().all()

    if not persons:
        return AggregateQueryResponse(
            metric=request.metric,
            group_by=request.group_by,
            filters_applied={k: v for k, v in request.model_dump().items() if v is not None},
            results=[],
            total_records=0,
        )

    # Agrupar datos
    groups = defaultdict(list)
    for p in persons:
        key = tuple(getattr(p, field) for field in request.group_by)
        groups[key].append(p)

    # Calcular métrica por grupo
    results = []
    for group_key, group_persons in groups.items():
        group_dict = dict(zip(request.group_by, group_key))

        if request.metric == "count":
            value = len(group_persons)
        elif request.metric == "avg_edad":
            value = round(sum(p.edad for p in group_persons) / len(group_persons), 2)
        elif request.metric == "pct_internet":
            with_internet = sum(1 for p in group_persons if p.acceso_internet)
            value = round((with_internet / len(group_persons)) * 100, 2)
        else:
            value = 0

        results.append(AggregateResult(group=group_dict, value=value))

    # Ordenar resultados por valor (descendente para count)
    if request.metric == "count":
        results.sort(key=lambda x: x.value, reverse=True)

    return AggregateQueryResponse(
        metric=request.metric,
        group_by=request.group_by,
        filters_applied={k: v for k, v in request.model_dump().items() if v is not None},
        results=results,
        total_records=len(persons),
    )
