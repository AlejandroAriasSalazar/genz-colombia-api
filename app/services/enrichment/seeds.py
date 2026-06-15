"""Semillas y distribuciones condicionales del modelo de enriquecimiento.

IMPORTANTE — naturaleza de estos parámetros:
    Estas distribuciones son ILUSTRATIVAS y CALIBRADAS a patrones plausibles de
    Colombia (por región, edad, sexo y estrato). NO provienen todavía de la ingesta
    de los microdatos reales (Censo 2018, GEIH, ECC, ENTIC). En producción, el
    pipeline reemplaza estas semillas por las distribuciones estimadas de cada fuente
    (con factores de expansión) y NINGUNA variable Tier 3 se publica a nivel municipal
    sin pasar el gate de validación externa (ver validation.py y Propuesta sección 6).

El motor (engine.py) consume:
  - Marginales ilustrativos por región para anclar con IPF (stratum × education).
  - Una semilla de asociación (odds-ratios) para esa tabla conjunta.
  - Matrices de correlación latente para los bloques de cópula (econ y cultura/digital).
  - Modelos condicionales log-multiplicativos para el resto de variables Tier 3.
"""

from __future__ import annotations

import numpy as np

from app.services.enrichment.dictionary import VARIABLES_BY_NAME

ENRICHMENT_MODEL_VERSION = "enrich-2025.06-illustrative"

# --- Geografía: departamento DIVIPOLA -> macro-región -----------------------------
_REGION_BY_DEPT = {
    "11": "bogota",
    "05": "andina", "15": "andina", "17": "andina", "25": "andina", "63": "andina",
    "66": "andina", "68": "andina", "73": "andina", "76": "andina", "54": "andina",
    "08": "caribe", "13": "caribe", "20": "caribe", "23": "caribe", "44": "caribe",
    "47": "caribe", "70": "caribe", "88": "caribe",
    "19": "pacifico", "27": "pacifico", "52": "pacifico",
    "18": "amazonia", "86": "amazonia", "91": "amazonia", "94": "amazonia",
    "95": "amazonia", "97": "amazonia", "99": "orinoquia",
    "50": "orinoquia", "81": "orinoquia", "85": "orinoquia",
}


def region_of(department_code: str) -> str:
    return _REGION_BY_DEPT.get(department_code, "andina")


def age_band(age: int) -> str:
    if age < 18:
        return "12-17"
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 50:
        return "35-49"
    return "50+"


# --- Capa 1: marginales ilustrativos para IPF (stratum × education) ----------------
# Marginales de estrato (1..6) por región — proporciones que suman 1.
STRATUM_MARGINALS = {
    "bogota":    [0.09, 0.34, 0.36, 0.13, 0.05, 0.03],
    "andina":    [0.22, 0.36, 0.27, 0.10, 0.03, 0.02],
    "caribe":    [0.38, 0.34, 0.18, 0.06, 0.02, 0.02],
    "pacifico":  [0.41, 0.33, 0.17, 0.06, 0.02, 0.01],
    "orinoquia": [0.30, 0.35, 0.23, 0.08, 0.02, 0.02],
    "amazonia":  [0.45, 0.31, 0.16, 0.05, 0.02, 0.01],
}
# Marginales de nivel educativo (7 categorías) por región.
EDUCATION_MARGINALS = {
    "bogota":    [0.01, 0.07, 0.20, 0.27, 0.16, 0.25, 0.04],
    "andina":    [0.03, 0.15, 0.27, 0.25, 0.13, 0.15, 0.02],
    "caribe":    [0.05, 0.20, 0.30, 0.23, 0.10, 0.11, 0.01],
    "pacifico":  [0.06, 0.22, 0.30, 0.22, 0.09, 0.10, 0.01],
    "orinoquia": [0.04, 0.18, 0.29, 0.24, 0.11, 0.13, 0.01],
    "amazonia":  [0.07, 0.24, 0.30, 0.21, 0.08, 0.09, 0.01],
}

# Semilla de asociación stratum(6) × education(7): mayor estrato -> mayor educación.
# Se construye como producto exterior modulado por una diagonal de afinidad.
def stratum_education_seed() -> np.ndarray:
    strat = np.linspace(0.0, 1.0, 6).reshape(6, 1)      # 0=estrato1 ... 1=estrato6
    educ = np.linspace(0.0, 1.0, 7).reshape(1, 7)       # 0=ninguno ... 1=posgrado
    # afinidad positiva: penaliza combinaciones lejanas (estrato alto/sin educación)
    affinity = np.exp(-3.0 * (strat - educ) ** 2)
    return affinity + 0.05  # piso para evitar ceros estructurales


# --- Capa 2: bloques de cópula (orden de variables + correlación latente) ----------
ECON_BLOCK = [
    "household_income_decile", "purchasing_power_band", "discretionary_spending_band",
    "savings_capacity", "credit_card_holder", "digital_payment_use",
    "streaming_video_subscription", "streaming_music_subscription",
    "ecommerce_purchase_frequency",
]
# Correlación positiva fuerte dentro del bloque económico (co-movimiento ingreso↔consumo).
ECON_CORR = (np.full((len(ECON_BLOCK), len(ECON_BLOCK)), 0.55)
             + np.eye(len(ECON_BLOCK)) * 0.45)

CULTURE_BLOCK = [
    "live_concert_attendance", "cinema_attendance_frequency", "reading_books_per_year",
    "videogame_player", "social_media_hours_day", "music_genre_preference",
]
CULTURE_CORR = (np.full((len(CULTURE_BLOCK), len(CULTURE_BLOCK)), 0.35)
                + np.eye(len(CULTURE_BLOCK)) * 0.65)
# La música no co-mueve linealmente con asistencia; se reduce su acoplamiento.
_mi = CULTURE_BLOCK.index("music_genre_preference")
CULTURE_CORR[_mi, :] = 0.10
CULTURE_CORR[:, _mi] = 0.10
CULTURE_CORR[_mi, _mi] = 1.0


# --- Modelos condicionales log-multiplicativos -----------------------------------
# Cada entrada: base (vector de pesos por categoría) + tilts por covariable.
# Un tilt es {valor_covariable: vector_multiplicador}. El engine multiplica y
# normaliza. Para 'count' se usa ('count', lambda_base, {cov: factor}).

def _u(n):  # uniforme
    return [1.0] * n


COND_MODELS: dict[str, dict] = {
    # ---- Dominio A (anclados aparte por IPF, salvo estos condicionales) ----
    "school_attendance": {  # asiste a institución educativa: alto en jóvenes
        "base": [0.4, 0.6],
        "tilts": {"age_band": {"12-17": [0.05, 0.95], "18-24": [0.45, 0.55],
                                "25-34": [0.9, 0.1], "35-49": [0.97, 0.03], "50+": [0.99, 0.01]}},
    },
    "ethnic_self_recognition": {
        "base": [0.80, 0.05, 0.10, 0.02, 0.01, 0.02],
        "tilts": {"region": {"caribe": [0.62, 0.06, 0.22, 0.06, 0.01, 0.03],
                              "pacifico": [0.45, 0.10, 0.40, 0.02, 0.01, 0.02],
                              "amazonia": [0.55, 0.35, 0.07, 0.01, 0.01, 0.01]}},
    },
    "mother_tongue": {
        "base": [0.94, 0.03, 0.01, 0.02],
        "tilts": {"region": {"amazonia": [0.70, 0.28, 0.01, 0.01],
                              "caribe": [0.92, 0.02, 0.04, 0.02]}},
    },
    "housing_tenure": {"base": [0.45, 0.40, 0.10, 0.05],
                       "tilts": {"stratum": {0: [0.40, 0.40, 0.15, 0.05], 4: [0.62, 0.30, 0.05, 0.03]}}},
    "dwelling_type": {"base": [0.55, 0.30, 0.10, 0.05],
                      "tilts": {"region": {"bogota": [0.30, 0.58, 0.08, 0.04]}}},
    "migration_status": {"base": [0.85, 0.15], "tilts": {}},
    "disability_status": {"base": [0.93, 0.07],
                          "tilts": {"age_band": {"50+": [0.82, 0.18], "12-17": [0.96, 0.04]}}},
    "household_size": {"count": True, "lambda": 3.4, "factors": {"region": {"caribe": 1.18, "bogota": 0.85}}},
    "bank_account_holder": {"base": [0.35, 0.65],
                            "tilts": {"stratum": {0: [0.55, 0.45], 4: [0.08, 0.92]},
                                      "age_band": {"12-17": [0.70, 0.30]}}},

    # ---- Dominio B ----
    "household_income_decile": {  # ordinal 1..10, sube con estrato y educación
        "base": _u(10),
        "tilts": {"stratum": {0: [3,3,2.5,1.5,1,.6,.4,.2,.1,.05], 2: _u(10),
                              4: [.05,.1,.2,.4,.7,1,1.4,1.8,2.2,2.5]},
                  "age_band": {"12-17": [2,1.6,1.2,1,.8,.6,.4,.3,.2,.1]}},
    },
    "purchasing_power_band": {"base": _u(5),
                              "tilts": {"stratum": {0: [2.5,1.6,1,.4,.15], 4: [.1,.3,1,1.8,2.2]}}},
    "employment_status": {  # ocupado/desempleado/inactivo/estudiante
        "base": [0.5, 0.1, 0.15, 0.25],
        "tilts": {"age_band": {"12-17": [0.05, 0.02, 0.08, 0.85], "18-24": [0.45, 0.18, 0.10, 0.27],
                                "25-34": [0.72, 0.12, 0.12, 0.04], "50+": [0.55, 0.06, 0.38, 0.01]}},
    },
    "occupation_sector": {"base": [0.10, 0.12, 0.20, 0.28, 0.08, 0.18, 0.04],
                          "tilts": {"region": {"caribe": [0.16, 0.08, 0.22, 0.22, 0.07, 0.21, 0.04]},
                                    "stratum": {4: [0.03, 0.10, 0.18, 0.40, 0.18, 0.07, 0.04]}}},
    "informality_status": {"base": [0.4, 0.6],
                           "tilts": {"stratum": {0: [0.18, 0.82], 4: [0.78, 0.22]}}},
    "credit_card_holder": {"base": [0.7, 0.3],
                           "tilts": {"stratum": {0: [0.92, 0.08], 4: [0.32, 0.68]}}},
    "digital_payment_use": {"base": [0.45, 0.55],
                            "tilts": {"age_band": {"12-17": [0.55, 0.45], "50+": [0.70, 0.30]},
                                      "stratum": {0: [0.66, 0.34], 4: [0.20, 0.80]}}},
    "discretionary_spending_band": {"base": _u(4),
                                    "tilts": {"stratum": {0: [2.2, 1.4, .6, .2], 4: [.1, .5, 1.4, 2.0]}}},
    "savings_capacity": {"base": _u(4),
                         "tilts": {"stratum": {0: [2.4, 1.3, .5, .15], 4: [.15, .6, 1.5, 1.8]}}},

    # ---- Dominio C ----
    "music_genre_preference": {
        "base": [0.26, 0.14, 0.12, 0.14, 0.07, 0.08, 0.05, 0.04, 0.03, 0.07],
        "tilts": {"age_band": {"12-17": [0.42, 0.06, 0.05, 0.16, 0.06, 0.04, 0.10, 0.04, 0.01, 0.06],
                                "50+": [0.08, 0.28, 0.22, 0.10, 0.07, 0.10, 0.01, 0.03, 0.06, 0.05]},
                  "region": {"caribe": [0.30, 0.32, 0.12, 0.08, 0.03, 0.07, 0.02, 0.01, 0.01, 0.04],
                             "pacifico": [0.28, 0.06, 0.30, 0.10, 0.04, 0.12, 0.03, 0.01, 0.02, 0.04]}},
    },
    "music_listening_frequency": {"base": [0.05, 0.20, 0.35, 0.40],
                                  "tilts": {"age_band": {"12-17": [0.02, 0.10, 0.30, 0.58]}}},
    "live_concert_attendance": {"base": _u(4),
                                "tilts": {"stratum": {0: [2.4, 1.2, .4, .15], 4: [.4, 1, 1.4, 1.2]},
                                          "age_band": {"50+": [2.0, 1.2, .5, .2]}}},
    "cinema_attendance_frequency": {"base": _u(4),
                                    "tilts": {"stratum": {0: [2.2, 1.3, .5, .2], 4: [.3, 1, 1.5, 1.2]},
                                              "region": {"bogota": [.5, 1, 1.4, 1.1]}}},
    "favorite_film_genre": {"base": [0.20, 0.20, 0.14, 0.10, 0.12, 0.12, 0.05, 0.07],
                            "tilts": {"age_band": {"12-17": [0.18, 0.18, 0.06, 0.14, 0.10, 0.20, 0.02, 0.12]}}},
    "tv_viewing_hours": {"count": True, "lambda": 2.6,
                         "factors": {"age_band": {"12-17": 0.8, "50+": 1.5}}},
    "favorite_tv_genre": {"base": [0.16, 0.16, 0.14, 0.10, 0.16, 0.08, 0.08, 0.12],
                          "tilts": {"age_band": {"12-17": [0.05, 0.06, 0.12, 0.18, 0.22, 0.05, 0.04, 0.28],
                                                  "50+": [0.30, 0.22, 0.14, 0.03, 0.10, 0.03, 0.12, 0.06]}}},
    "reading_books_per_year": {"count": True, "lambda": 2.2,
                               "factors": {"stratum": {0: 0.5, 4: 2.2}, "region": {"bogota": 1.4}}},
    "reading_format": {"base": [0.30, 0.30, 0.20, 0.20],
                       "tilts": {"age_band": {"12-17": [0.20, 0.18, 0.38, 0.24], "50+": [0.40, 0.42, 0.08, 0.10]}}},
    "videogame_player": {"base": [0.6, 0.4],
                         "tilts": {"age_band": {"12-17": [0.25, 0.75], "18-24": [0.45, 0.55],
                                                 "50+": [0.88, 0.12]}}},
    "videogame_hours_week": {"count": True, "lambda": 3.0,
                             "factors": {"age_band": {"12-17": 2.0, "50+": 0.2}}},
    "museum_gallery_visits": {"base": _u(3),
                              "tilts": {"stratum": {0: [2.5, 1, .3], 4: [.6, 1.2, 1.0]}}},
    "theater_dance_attendance": {"base": _u(3),
                                 "tilts": {"stratum": {0: [2.4, 1, .35], 4: [.7, 1.2, .9]}}},
    "cultural_festival_participation": {"base": [0.55, 0.45],
                                        "tilts": {"region": {"caribe": [0.40, 0.60], "pacifico": [0.42, 0.58]}}},

    # ---- Dominio D ----
    "smartphone_ownership": {"base": [0.15, 0.85],
                             "tilts": {"age_band": {"12-17": [0.10, 0.90], "50+": [0.35, 0.65]},
                                       "stratum": {0: [0.30, 0.70], 4: [0.02, 0.98]}}},
    "internet_access_home": {"base": [0.30, 0.70],
                             "tilts": {"stratum": {0: [0.55, 0.45], 4: [0.05, 0.95]},
                                       "region": {"bogota": [0.18, 0.82], "amazonia": [0.55, 0.45]}}},
    "internet_use_frequency": {"base": [0.08, 0.17, 0.30, 0.45],
                               "tilts": {"age_band": {"12-17": [0.02, 0.08, 0.25, 0.65], "50+": [0.20, 0.25, 0.30, 0.25]}}},
    "primary_social_platform": {"base": [0.34, 0.16, 0.20, 0.14, 0.10, 0.03, 0.03],
                                "tilts": {"age_band": {"12-17": [0.18, 0.04, 0.24, 0.40, 0.10, 0.02, 0.02],
                                                        "50+": [0.46, 0.30, 0.08, 0.02, 0.08, 0.02, 0.04]}}},
    "social_media_hours_day": {"count": True, "lambda": 2.8,
                               "factors": {"age_band": {"12-17": 1.7, "50+": 0.5}}},
    "streaming_video_subscription": {"base": [0.55, 0.45],
                                     "tilts": {"stratum": {0: [0.85, 0.15], 4: [0.18, 0.82]}}},
    "streaming_music_subscription": {"base": [0.62, 0.38],
                                     "tilts": {"age_band": {"12-17": [0.45, 0.55]},
                                               "stratum": {0: [0.88, 0.12], 4: [0.30, 0.70]}}},
    "ecommerce_purchase_frequency": {"base": _u(4),
                                     "tilts": {"stratum": {0: [2.4, 1.2, .5, .15], 4: [.4, 1, 1.3, 1.0]}}},
    "device_count_household": {"count": True, "lambda": 2.5,
                               "factors": {"stratum": {0: 0.6, 4: 2.0}}},
    "digital_skills_index": {"base": _u(3),
                             "tilts": {"age_band": {"12-17": [.3, 1, 1.6], "50+": [1.8, 1, .4]},
                                       "stratum": {4: [.4, 1, 1.7]}}},

    # ---- Dominio E ----
    "sports_practice_frequency": {"base": [0.30, 0.30, 0.25, 0.15],
                                  "tilts": {"age_band": {"12-17": [0.12, 0.28, 0.32, 0.28], "50+": [0.45, 0.30, 0.18, 0.07]}}},
    "commute_mode": {"base": [0.22, 0.06, 0.20, 0.34, 0.14, 0.04],
                     "tilts": {"region": {"bogota": [0.18, 0.08, 0.10, 0.50, 0.10, 0.04]},
                               "stratum": {4: [0.08, 0.04, 0.10, 0.20, 0.54, 0.04]}}},
    "bicycle_use": {"base": [0.45, 0.30, 0.18, 0.07],
                    "tilts": {"region": {"pacifico": [0.30, 0.32, 0.26, 0.12]}}},
    "eating_out_frequency": {"base": [0.20, 0.35, 0.30, 0.15],
                             "tilts": {"stratum": {0: [0.35, 0.38, 0.20, 0.07], 4: [0.08, 0.25, 0.40, 0.27]}}},
    "nightlife_frequency": {"base": [0.30, 0.30, 0.25, 0.15],
                            "tilts": {"age_band": {"18-24": [0.12, 0.28, 0.32, 0.28], "50+": [0.62, 0.24, 0.10, 0.04]}}},
    "religious_practice": {"base": [0.15, 0.35, 0.35, 0.15],
                           "tilts": {"age_band": {"12-17": [0.22, 0.40, 0.28, 0.10], "50+": [0.08, 0.25, 0.40, 0.27]}}},
}


def categories_of(name: str) -> list[str]:
    return VARIABLES_BY_NAME[name]["categories"] or []
