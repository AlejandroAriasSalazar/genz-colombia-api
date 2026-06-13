"""
Endpoint de metadata.
Expone información sobre el universo de datos, variables, clasificaciones y cobertura.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.utils.divipola import (
    NIVELES_EDUCATIVOS,
    OCUPACIONES,
    INTERESES_MUSICALES,
    INTERESES_TECNOLOGICOS,
    USO_BICICLETA,
)

router = APIRouter(tags=["Metadata"])


@router.get(
    "/metadata",
    summary="Metadata del dataset",
    description="Información sobre el universo de datos, variables, clasificaciones y cobertura.",
    response_description="Metadata completa del dataset sintético",
)
async def get_metadata(db: AsyncSession = Depends(get_db)):
    """
    Retorna metadata completa del dataset sintético de la Generación Z colombiana.

    Incluye:
        - Universo: Población objetivo (Gen Z, 12-28 años, Bogotá y Medellín)
        - Variables: Lista completa de variables disponibles
        - Clasificaciones: Taxonomías oficiales usadas (DIVIPOLA, CUOC, etc.)
        - Cobertura: Ciudades, barrios/comunas, estratos, rangos de edad
        - Fuentes: Referencias a las fuentes estadísticas oficiales
    """
    return {
        "api_version": settings.APP_VERSION,
        "dataset_name": "Generación Z Colombia - Datos Sintéticos",
        "description": "Dataset sintético de jóvenes colombianos (12-28 años) de Bogotá y Medellín, con distribuciones marginales basadas en estadísticas oficiales del DANE.",
        "universo": {
            "poblacion_objetivo": "Generación Z colombiana",
            "rango_edad": {"min": 12, "max": 28},
            "ciudades": ["Bogotá D.C.", "Medellín"],
            "total_registros_sinteticos": "Aproximadamente 1000 registros sintéticos",
        },
        "variables": {
            "demograficas": {
                "edad": {"tipo": "integer", "rango": [12, 28], "descripcion": "Edad en años"},
                "sexo": {"tipo": "string", "categorias": ["M", "F"], "descripcion": "Sexo biológico"},
                "estrato": {"tipo": "integer", "rango": [1, 6], "descripcion": "Estrato socioeconómico (1-6)"},
            },
            "geograficas": {
                "ciudad_divipola": {"tipo": "string", "clasificacion": "DIVIPOLA", "descripcion": "Código DIVIPOLA de la ciudad"},
                "neighborhood_code": {"tipo": "string", "descripcion": "Código de barrio/comuna/localidad"},
            },
            "educativas": {
                "nivel_educativo": {
                    "tipo": "string",
                    "categorias": NIVELES_EDUCATIVOS,
                    "descripcion": "Nivel educativo alcanzado",
                },
            },
            "ocupacionales": {
                "ocupacion": {
                    "tipo": "string",
                    "clasificacion": "CUOC simplificada",
                    "categorias": OCUPACIONES,
                    "descripcion": "Ocupación actual",
                },
            },
            "conectividad": {
                "acceso_internet": {"tipo": "boolean", "descripcion": "Tiene acceso a internet"},
            },
            "conductuales": {
                "interes_musical": {
                    "tipo": "string",
                    "categorias": INTERESES_MUSICALES,
                    "descripcion": "Género musical de mayor interés",
                },
                "interes_tecnologico": {
                    "tipo": "string",
                    "categorias": INTERESES_TECNOLOGICOS,
                    "descripcion": "Área tecnológica de mayor interés",
                },
                "uso_bicicleta": {
                    "tipo": "string",
                    "categorias": USO_BICICLETA,
                    "descripcion": "Frecuencia de uso de bicicleta",
                },
            },
        },
        "clasificaciones": {
            "geografica": {
                "estandares": ["DIVIPOLA (DANE)", "Localidades Bogotá (20)", "Comunas Medellín (16)"],
                "fuente": "DANE - División Político-Administrativa de Colombia",
            },
            "ocupacional": {
                "estandares": ["CUOC simplificada (Clasificación Uniforme de Ocupaciones de Colombia)"],
                "fuente": "DANE - Clasificación Uniforme de Ocupaciones",
            },
            "estratos": {
                "estandares": ["Estratificación socioeconómica urbana (1-6)"],
                "fuente": "Ley 142 de 1994 - Régimen de Servicios Públicos Domiciliarios",
            },
        },
        "fuentes": {
            "primarias": [
                "DANE - Censo Nacional de Población y Vivienda (CNPV)",
                "DANE - Gran Encuesta Integrada de Hogares (GEIH)",
                "DANE - Encuesta Continua de Hogares (ECH)",
                "DANE - Proyecciones de población 2018-2035",
                "ICFES - Resultados Saber 11 y Saber Pro",
                "MinTIC - Encuesta de Tecnologías de la Información (ENTIC)",
            ],
            "territoriales": [
                "Datos Abiertos Bogotá",
                "MEData - Medellín Datos Abiertos",
                "Área Metropolitana del Valle de Aburrá",
            ],
            "nota": "Los datos expuestos son SINTÉTICOS. Preservan distribuciones marginales y correlaciones estadísticas basadas en las fuentes oficiales, pero no representan individuos reales.",
        },
        "metodologia": {
            "generacion": "Datos sintéticos generados con distribuciones marginales calibradas según estadísticas oficiales del DANE.",
            "validacion": "Se verifican distribuciones de estratos por ciudad, proporciones de sexo, distribución de edades, y correlaciones edad-nivel_educativo.",
            "privacidad": "No se exponen identificadores reales. Los IDs son hashes irreversibles. Se aplican guardas de exposición para evitar singling out.",
        },
    }
