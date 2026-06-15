"""Commercial plans — single source of truth for tier limits, scopes and pricing.

Used by `scripts.manage create-key` (to provision keys) and by the public `/plans`
endpoint (the pricing page as data).
"""

SCOPE_SAMPLE = "sample:read"
SCOPE_AGGREGATE = "aggregate:read"
SCOPE_MARKET = "market:read"
# V3: acceso al bloque enriquecido de 52 variables (Tier 2 anclado + Tier 3 modelado).
SCOPE_ENRICH = "enrich:read"

PLANS: dict[str, dict] = {
    "free": {
        "label": "Free",
        "price_usd_month": 0,
        "requests_per_minute": 60,
        "requests_per_day": 1000,
        "max_sample_size": 100,
        "scopes": [SCOPE_SAMPLE, SCOPE_AGGREGATE],
        "coverage": "Nacional (municipal)",
        "includes": [
            "Muestreo sintético reproducible",
            "Agregados oficiales (aggregate/query)",
            "Catálogo: ciudades, departamentos, fuentes",
        ],
    },
    "pro": {
        "label": "Pro",
        "price_usd_month": 199,
        "requests_per_minute": 600,
        "requests_per_day": 20000,
        "max_sample_size": 500,
        "scopes": [SCOPE_SAMPLE, SCOPE_AGGREGATE, SCOPE_MARKET, SCOPE_ENRICH],
        "coverage": "Nacional (municipal)",
        "includes": [
            "Todo lo de Free",
            "Endpoints de decisión: market sizing, ranking territorial, perfil",
            "Informe por territorio (JSON y página)",
            "Enriquecimiento: 52 variables (Tier 2 anclado + Tier 3 modelado) con bandas",
        ],
    },
    "enterprise": {
        "label": "Enterprise",
        "price_usd_month": "custom",
        "requests_per_minute": 3000,
        "requests_per_day": 200000,
        "max_sample_size": 1000,
        "scopes": [SCOPE_SAMPLE, SCOPE_AGGREGATE, SCOPE_MARKET, SCOPE_ENRICH],
        "coverage": "Nacional (municipal) + datos a medida",
        "includes": [
            "Todo lo de Pro",
            "SLA y soporte dedicado",
            "Variables enriquecidas a medida y cobertura multipaís (roadmap)",
        ],
    },
}


def plan_limits(tier: str) -> tuple[int, int, int]:
    plan = PLANS[tier]
    return plan["requests_per_minute"], plan["requests_per_day"], plan["max_sample_size"]


def plan_scopes(tier: str) -> list[str]:
    return list(PLANS[tier]["scopes"])
