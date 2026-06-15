"""Gate de validación del enriquecimiento (Propuesta sección 6).

Regla de decisión: ninguna variable Tier 3 se publica a nivel municipal solo por
validación interna. El gate combina:

  - Interna (mínimo, casi nunca suficiente): SRMSE/TAE por zona del ajuste IPF y
    reproducción de marginales anclados. Por construcción suele dar ~0 -> no prueba
    realismo.
  - Plausibilidad de correlaciones: signos esperados del co-movimiento (p. ej.
    ingreso ↔ suscripción a streaming positivo) que la cópula debe preservar.
  - Externa (gate duro): hook para comparar contra una fuente independiente local
    no usada en el ajuste. Mientras las semillas sean ILUSTRATIVAS, este check queda
    en estado `pending_external_source` y las variables Tier 3 NO se habilitan a
    municipal; se entregan como estimación regional explícita.
"""

from __future__ import annotations

import numpy as np

from app.services.enrichment import seeds
from app.services.enrichment.engine import anchored_fit_report, enrich_person

_SRMSE_MAX = 1e-3  # tolerancia interna del ajuste IPF


def validate_anchoring() -> dict:
    """Validación interna del IPF para todas las regiones."""
    reports = [anchored_fit_report(r) for r in seeds.STRATUM_MARGINALS]
    worst = max(r["srmse"] for r in reports)
    return {
        "check": "ipf_marginal_fit",
        "passed": worst < _SRMSE_MAX,
        "worst_srmse": worst,
        "per_region": reports,
    }


def _ordinal_idx(value: str, name: str) -> int:
    from app.services.enrichment.dictionary import VARIABLES_BY_NAME
    cats = VARIABLES_BY_NAME[name]["categories"]
    return cats.index(value) if value in cats else 0


def validate_correlations(persons: list[dict]) -> dict:
    """Plausibilidad: la cópula debe preservar el co-movimiento ingreso↔consumo."""
    income, streaming, ecom = [], [], []
    for p in persons:
        attrs = enrich_person(p)["attributes"]
        income.append(_ordinal_idx(attrs["household_income_decile"]["value"],
                                   "household_income_decile"))
        streaming.append(1 if attrs["streaming_video_subscription"]["value"] == "si" else 0)
        ecom.append(_ordinal_idx(attrs["ecommerce_purchase_frequency"]["value"],
                                 "ecommerce_purchase_frequency"))
    checks = []
    for label, a, b in (("income~streaming", income, streaming),
                        ("income~ecommerce", income, ecom)):
        if np.std(a) > 0 and np.std(b) > 0:
            r = float(np.corrcoef(a, b)[0, 1])
        else:
            r = 0.0
        checks.append({"pair": label, "pearson": round(r, 3), "expected_sign": "+",
                       "passed": r > 0.05})
    return {
        "check": "correlation_plausibility",
        "passed": all(c["passed"] for c in checks),
        "pairs": checks,
    }


def validate_marginals(persons: list[dict]) -> dict:
    """Reproducción de los marginales anclados (estrato) por región en la muestra."""
    by_region: dict[str, list[int]] = {}
    for p in persons:
        out = enrich_person(p)
        idx = _ordinal_idx(out["attributes"]["socioeconomic_stratum"]["value"],
                           "socioeconomic_stratum")
        by_region.setdefault(out["region"], []).append(idx)

    rows = []
    worst = 0.0
    for region, idxs in by_region.items():
        observed = np.bincount(idxs, minlength=6).astype(float)
        observed = observed / observed.sum()
        target = np.array(seeds.STRATUM_MARGINALS[region])
        srmse = float(np.sqrt(np.mean((observed - target) ** 2)) / np.mean(target))
        worst = max(worst, srmse)
        rows.append({"region": region, "n": len(idxs), "srmse": round(srmse, 3)})
    # Tolerancia muestral: con n por región moderado el SRMSE empírico es pequeño
    # pero no nulo; umbral laxo porque es un check muestral, no de ajuste.
    return {
        "check": "anchored_marginal_reproduction",
        "passed": worst < 0.35,
        "worst_srmse": round(worst, 3),
        "per_region": rows,
    }


def enrichment_quality_report(persons: list[dict]) -> dict:
    """Reporte consolidado para el quality gate de una release enriquecida."""
    anchoring = validate_anchoring()
    correlations = validate_correlations(persons)
    marginals = validate_marginals(persons)

    internal_passed = anchoring["passed"] and marginals["passed"] and correlations["passed"]
    external = {
        "check": "external_validation",
        "status": "pending_external_source",
        "passed": False,
        "note": (
            "Semillas ilustrativas: sin fuente local independiente, las variables "
            "Tier 3 NO se habilitan a municipal. Se entregan como estimación regional "
            "con banda. Sustituir por ECC/GEIH/ENTIC reales + fuente de validación."
        ),
    }
    return {
        "model_version": seeds.ENRICHMENT_MODEL_VERSION,
        "internal": {"anchoring": anchoring, "marginals": marginals, "correlations": correlations},
        "external": external,
        "tier2_municipal_publishable": internal_passed,
        "tier3_municipal_publishable": internal_passed and external["passed"],
        "status": "passed_internal" if internal_passed else "failed",
    }
