"""Motor de enriquecimiento — orquestación de las cuatro capas (Propuesta 4.1).

Dada una persona sintética base (municipio, edad, sexo, año, identidad estable),
produce el bloque enriquecido de 52 variables:

  Capa 1  IPF        -> ancla (estrato × educación) a marginales locales.
  Capa 2  Cópula     -> bloques económico y cultural con dependencia conjunta.
          Condicional-> resto de variables Tier 3 dado el bloque anclado.
          Derivadas  -> índices y segmentos psicográficos compuestos.
  Capa 3  Incertid.  -> cada atributo lleva intervalo y nivel de confianza, con
                        penalización por transferencia regional->municipal.

Reproducibilidad (Propuesta 4.4): el RNG por persona deriva de la identidad estable
(HMAC) más `ENRICHMENT_MODEL_VERSION`. Misma seed + misma versión de dataset + misma
versión de modelo => misma persona multivariable, estable entre entornos.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

import numpy as np

from app.services.enrichment import seeds
from app.services.enrichment.copula import correlated_uniforms, inverse_cdf_pick
from app.services.enrichment.dictionary import VARIABLES, VARIABLES_BY_NAME
from app.services.enrichment.ipf import fit_ipf

# Penalización de confianza por bajar de la granularidad de verdad a municipal.
_TRANSFER_PENALTY = {
    "manzana": 0.0, "municipal": 0.0, "departamental": 0.10,
    "regional": 0.18, "nacional": 0.30,
}
_TIER_BASE_CONFIDENCE = {1: 1.0, 2: 0.9, 3: 0.7, 4: 0.4}

_ANCHORED_IPF = {"socioeconomic_stratum", "education_level"}
_DERIVED = {"digital_skills_index", "early_adopter_index", "consumer_psychographic_segment"}


# --- RNG determinista por persona -------------------------------------------------

def _person_rng(synthetic_id: str) -> np.random.Generator:
    payload = f"{synthetic_id}:{seeds.ENRICHMENT_MODEL_VERSION}".encode()
    digest = hashlib.sha256(payload).digest()
    seed_int = int.from_bytes(digest[:8], "big")
    return np.random.default_rng(seed_int)


# --- Capa 1: IPF anclado (estrato × educación) por región -------------------------

@lru_cache(maxsize=16)
def _anchored_joint(region: str) -> np.ndarray:
    """Tabla conjunta estrato(6)×educación(7) ajustada por IPF a los marginales
    locales de la región. Cacheada por región."""
    result = fit_ipf(
        seeds.stratum_education_seed(),
        [np.array(seeds.STRATUM_MARGINALS[region]),
         np.array(seeds.EDUCATION_MARGINALS[region])],
    )
    joint = result.fitted
    return joint / joint.sum()


def anchored_fit_report(region: str) -> dict:
    """Diagnóstico de convergencia del IPF para una región (para el quality gate)."""
    result = fit_ipf(
        seeds.stratum_education_seed(),
        [np.array(seeds.STRATUM_MARGINALS[region]),
         np.array(seeds.EDUCATION_MARGINALS[region])],
    )
    return {
        "region": region,
        "converged": result.converged,
        "iterations": result.iterations,
        "tae": round(result.tae, 8),
        "srmse": round(result.srmse, 8),
    }


# --- Modelos condicionales --------------------------------------------------------

def _nearest_key(mapping: dict, value: int):
    keys = list(mapping.keys())
    return min(keys, key=lambda k: abs(k - value))


def _conditional_probs(name: str, cov: dict) -> np.ndarray:
    """Vector de probabilidades de una variable categórica/ordinal dado `cov`."""
    model = seeds.COND_MODELS[name]
    weights = np.array(model["base"], dtype=float)
    for cov_key, mapping in model.get("tilts", {}).items():
        if cov_key == "stratum":
            key = _nearest_key(mapping, cov["stratum"])
            weights = weights * np.array(mapping[key], dtype=float)
        else:
            value = cov.get(cov_key)
            if value in mapping:
                weights = weights * np.array(mapping[value], dtype=float)
    total = weights.sum()
    return weights / total if total > 0 else np.full(len(weights), 1.0 / len(weights))


def _conditional_lambda(name: str, cov: dict) -> float:
    model = seeds.COND_MODELS[name]
    lam = float(model["lambda"])
    for cov_key, mapping in model.get("factors", {}).items():
        if cov_key == "stratum":
            key = _nearest_key(mapping, cov["stratum"])
            lam *= mapping[key]
        elif cov.get(cov_key) in mapping:
            lam *= mapping[cov[cov_key]]
    return lam


def _poisson_ppf(u: float, lam: float, cap: int = 60) -> int:
    """Cuantil de una Poisson(lam) en u — para muestrear counts desde la cópula."""
    cdf = 0.0
    term = np.exp(-lam)
    for k in range(cap):
        cdf += term
        if u <= cdf:
            return k
        term *= lam / (k + 1)
    return cap


# --- Construcción de atributos con incertidumbre ----------------------------------

def _attribute(name: str, value, *, p_value: float | None,
               numeric_interval: tuple | None) -> dict:
    spec = VARIABLES_BY_NAME[name]
    penalty = _TRANSFER_PENALTY.get(spec["truth_granularity"], 0.2)
    confidence = round(_TIER_BASE_CONFIDENCE[spec["tier"]] * (1.0 - penalty), 3)
    attr = {
        "value": value,
        "tier": spec["tier"],
        "source": spec["source"],
        "truth_granularity": spec["truth_granularity"],
        "method": spec["method"],
        "confidence": confidence,
    }
    if p_value is not None:
        band = min(0.5, 0.06 + penalty)
        attr["p_value"] = round(float(p_value), 4)
        attr["interval"] = [round(float(max(0.0, p_value - band)), 4),
                            round(float(min(1.0, p_value + band)), 4)]
    if numeric_interval is not None:
        attr["interval"] = [int(numeric_interval[0]), int(numeric_interval[1])]
    return attr


def _pick_categorical(name: str, cov: dict, u: float) -> dict:
    probs = _conditional_probs(name, cov)
    idx = inverse_cdf_pick(u, probs.tolist())
    cats = VARIABLES_BY_NAME[name]["categories"]
    return _attribute(name, cats[idx], p_value=probs[idx], numeric_interval=None), idx


def _pick_count(name: str, cov: dict, u: float | None, rng) -> dict:
    lam = _conditional_lambda(name, cov)
    u = rng.random() if u is None else u
    value = _poisson_ppf(u, lam)
    spec = VARIABLES_BY_NAME[name]
    penalty = _TRANSFER_PENALTY.get(spec["truth_granularity"], 0.2)
    w = 0.15 + penalty
    lo = int(max(0, np.floor(value * (1 - w))))
    hi = int(np.ceil(value * (1 + w)) + 1)
    return _attribute(name, int(value), p_value=None, numeric_interval=(lo, hi))


# --- Capa 2 derivadas -------------------------------------------------------------

def _ordinal_index(attr: dict, name: str) -> int:
    cats = VARIABLES_BY_NAME[name]["categories"]
    return cats.index(attr["value"]) if attr["value"] in cats else 0


def _derive(results: dict, cov: dict, rng) -> None:
    # digital_skills_index: de uso de internet + dispositivos + smartphone
    iu = _ordinal_index(results["internet_use_frequency"], "internet_use_frequency")
    dev = results["device_count_household"]["value"]
    smart = 1 if results["smartphone_ownership"]["value"] == "si" else 0
    score = iu / 3 * 0.5 + min(dev, 5) / 5 * 0.3 + smart * 0.2
    skill = ["bajo", "medio", "alto"][int(min(2, np.floor(score * 3)))]
    results["digital_skills_index"] = _attribute(
        "digital_skills_index", skill, p_value=None, numeric_interval=None)

    # early_adopter_index: tecnología + consumo digital
    streaming = sum(1 for k in ("streaming_video_subscription", "streaming_music_subscription")
                    if results[k]["value"] == "si")
    ecom = _ordinal_index(results["ecommerce_purchase_frequency"], "ecommerce_purchase_frequency")
    young = 1 if cov["age_band"] in ("12-17", "18-24") else 0
    adopt = (score * 0.4 + streaming / 2 * 0.3 + ecom / 3 * 0.2 + young * 0.1)
    levels = ["rezagado", "mayoria_tardia", "mayoria_temprana", "adoptador_temprano", "innovador"]
    results["early_adopter_index"] = _attribute(
        "early_adopter_index", levels[int(min(4, np.floor(adopt * 5)))],
        p_value=None, numeric_interval=None)

    # consumer_psychographic_segment: regla simple sobre estrato/edad/digital
    seg = "pragmatico"
    if cov["stratum"] >= 3 and adopt > 0.6:
        seg = "aspiracional"
    elif young and score > 0.6:
        seg = "digital_first"
    elif cov["age_band"] == "50+":
        seg = "tradicional"
    elif _ordinal_index(results["savings_capacity"], "savings_capacity") >= 2:
        seg = "ahorrador"
    elif _ordinal_index(results["nightlife_frequency"], "nightlife_frequency") >= 2:
        seg = "experiencial"
    results["consumer_psychographic_segment"] = _attribute(
        "consumer_psychographic_segment", seg, p_value=None, numeric_interval=None)


# --- Orquestación principal -------------------------------------------------------

def enrich_person(person: dict, domains: set[str] | None = None) -> dict:
    """Devuelve el bloque enriquecido para una persona base.

    `person` debe traer: synthetic_id, age, sex, municipality_code, reference_year.
    `domains`: subconjunto de {A,B,C,D,E,F} a generar (None = todos).
    """
    rng = _person_rng(person["synthetic_id"])
    dept = person["municipality_code"][:2]
    region = seeds.region_of(dept)
    cov = {"region": region, "age_band": seeds.age_band(person["age"]),
           "sex": person["sex"]}

    results: dict[str, dict] = {}

    # Capa 1 — ancla IPF: estrato × educación
    joint = _anchored_joint(region)
    flat = joint.ravel()
    cell = inverse_cdf_pick(rng.random(), flat.tolist())
    s_idx, e_idx = np.unravel_index(cell, joint.shape)
    cov["stratum"] = int(s_idx)
    results["socioeconomic_stratum"] = _attribute(
        "socioeconomic_stratum", VARIABLES_BY_NAME["socioeconomic_stratum"]["categories"][s_idx],
        p_value=float(joint[s_idx].sum()), numeric_interval=None)
    results["education_level"] = _attribute(
        "education_level", VARIABLES_BY_NAME["education_level"]["categories"][e_idx],
        p_value=float(joint[:, e_idx].sum()), numeric_interval=None)

    # Capa 2 — cópula bloque económico
    econ_u = correlated_uniforms(seeds.ECON_CORR, rng)
    for var, u in zip(seeds.ECON_BLOCK, econ_u):
        spec = VARIABLES_BY_NAME[var]
        if spec["dtype"] == "count":
            results[var] = _pick_count(var, cov, float(u), rng)
        else:
            results[var], _ = _pick_categorical(var, cov, float(u))

    # Capa 2 — cópula bloque cultural
    cult_u = correlated_uniforms(seeds.CULTURE_CORR, rng)
    for var, u in zip(seeds.CULTURE_BLOCK, cult_u):
        spec = VARIABLES_BY_NAME[var]
        if spec["dtype"] == "count":
            results[var] = _pick_count(var, cov, float(u), rng)
        else:
            results[var], _ = _pick_categorical(var, cov, float(u))

    # Resto condicional independiente
    already = set(results) | _DERIVED
    for spec in VARIABLES:
        name = spec["name"]
        if name in already or name in _ANCHORED_IPF:
            continue
        if spec["dtype"] == "count":
            results[name] = _pick_count(name, cov, None, rng)
        else:
            results[name], _ = _pick_categorical(name, cov, rng.random())

    # Capa 2 — derivadas
    _derive(results, cov, rng)

    # Filtrado por dominios solicitados
    if domains is not None:
        results = {k: v for k, v in results.items()
                   if VARIABLES_BY_NAME[k]["domain"] in domains}

    return {
        "enrichment_model_version": seeds.ENRICHMENT_MODEL_VERSION,
        "region": region,
        "attributes": results,
    }
