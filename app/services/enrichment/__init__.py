"""Paquete de enriquecimiento — síntesis de población multivariable (v3).

Convierte personas sintéticas demográficas (Tier 1, DANE) en personas con 52
variables culturales, sociales y económicas, vía IPF + cópula condicional, con
incertidumbre cuantificada y gate de validación. Ver Propuesta_Enriquecimiento.
"""

from app.services.enrichment.dictionary import VARIABLES, public_dictionary
from app.services.enrichment.engine import enrich_person
from app.services.enrichment.seeds import ENRICHMENT_MODEL_VERSION
from app.services.enrichment.validation import enrichment_quality_report

__all__ = [
    "VARIABLES",
    "public_dictionary",
    "enrich_person",
    "ENRICHMENT_MODEL_VERSION",
    "enrichment_quality_report",
]
