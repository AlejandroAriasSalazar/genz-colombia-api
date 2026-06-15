"""Endpoints de enriquecimiento (V3).

Exponen el catálogo de 52 variables con su tier/fuente/granularidad/método, los
metadatos del modelo de enriquecimiento y un reporte del gate de validación. El
diccionario es público (transparencia = producto); la validación detallada queda
tras `enrich:read`.
"""

from fastapi import APIRouter, Query, Security

from app.api.deps import get_current_client
from app.models import ApiClient
from app.services.enrichment import ENRICHMENT_MODEL_VERSION, public_dictionary
from app.services.enrichment.dictionary import DOMAINS
from app.services.enrichment.validation import enrichment_quality_report

router = APIRouter(tags=["Enrichment"])


@router.get("/enrichment/dictionary", summary="Catálogo de las 52 variables enriquecidas")
def dictionary():
    rows = public_dictionary()
    return {
        "model_version": ENRICHMENT_MODEL_VERSION,
        "domains": DOMAINS,
        "variable_count": len(rows),
        "tier_legend": {
            "2": "Anclado a marginal local (Censo/MinTIC) vía IPF. Granularidad municipal. Libre + cita.",
            "3": "Modelado de encuesta (ECC/GEIH/ENTIC) vía cópula/condicional. Verdad regional; "
                 "municipal solo con validación externa. Solo derivados.",
        },
        "variables": rows,
    }


@router.get("/enrichment/model", summary="Metadatos del modelo de enriquecimiento")
def model():
    return {
        "model_version": ENRICHMENT_MODEL_VERSION,
        "pipeline": [
            "Capa 0: ancla oficial DANE (municipio×año×sexo×edad), totales como restricción dura",
            "Capa 1: IPF a marginales locales (Censo/MinTIC) para variables Tier 2",
            "Capa 2: cópula gaussiana + modelos condicionales para variables Tier 3",
            "Capa 3: cuantificación de incertidumbre + gate de validación interna y externa",
        ],
        "reproducibility": (
            "RNG por persona derivado de la identidad estable HMAC + model_version: "
            "misma seed + versión de dataset + versión de modelo => misma persona."
        ),
        "uncertainty": (
            "Cada atributo lleva confidence, intervalo y truth_granularity; penalización "
            "por transferencia al bajar de la granularidad de verdad a municipal."
        ),
        "data_status": (
            "Semillas ILUSTRATIVAS calibradas; pendiente de ingesta de microdatos reales "
            "(Censo 2018, GEIH, ECC, ENTIC) y de fuente de validación externa local."
        ),
    }


@router.get("/enrichment/validation", summary="Reporte del gate de validación del enriquecimiento")
def validation(
    sample_size: int = Query(400, ge=50, le=2000),
    _: ApiClient = Security(get_current_client, scopes=["enrich:read"]),
):
    # Lote sintético de control que cubre regiones, edades y sexos para evaluar
    # el ajuste IPF, la reproducción de marginales y el co-movimiento de la cópula.
    municipalities = ["11001", "05001", "08001", "76001", "27001", "50001",
                      "91001", "85001", "13001", "23001", "52001", "18001"]
    ages = list(range(13, 60, 2))
    persons = []
    i = 0
    for m in municipalities:
        for a in ages:
            persons.append({
                "synthetic_id": f"val-{m}-{a}-{i}",
                "age": a,
                "sex": "M" if i % 2 else "F",
                "municipality_code": m,
                "reference_year": 2026,
            })
            i += 1
            if len(persons) >= sample_size:
                break
        if len(persons) >= sample_size:
            break
    return enrichment_quality_report(persons)
