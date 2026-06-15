"""Diccionario de las 52 variables de enriquecimiento.

Es el producto diferenciador (Propuesta, sección 3 y 7.6): cada variable se expone
con su dominio, tier de confianza, fuente, granularidad de verdad y método de
imputación. El catálogo es consultable por el cliente vía `/metadata` y
`/enrichment/dictionary`.

`truth_granularity` = nivel territorial al que la fuente es representativa. Por debajo
de ese nivel la variable se entrega como estimación modelada con banda, nunca como
hecho. `method`: IPF (anclada a marginal local), copula (dependencia conjunta Tier 3),
conditional (muestreo condicional directo), derived (índice/segmento compuesto).
"""

from __future__ import annotations

# Dominios (Propuesta 3.1–3.6)
DOMAINS = {
    "A": "Identidad sociodemográfica ampliada",
    "B": "Poder adquisitivo y economía del hogar",
    "C": "Consumo cultural (música, cine, TV, lectura, juego)",
    "D": "Tecnología, medios y vida digital",
    "E": "Estilo de vida, ocio y movilidad",
    "F": "Psicografía y segmentos derivados",
}


def _v(name, domain, tier, source, truth, method, dtype, categories=None, unit=None):
    return {
        "name": name,
        "domain": domain,
        "tier": tier,
        "source": source,
        "truth_granularity": truth,
        "method": method,
        "dtype": dtype,            # categorical | ordinal | binary | count
        "categories": categories,  # lista ordenada para categorical/ordinal/binary
        "unit": unit,              # para count
    }


VARIABLES: list[dict] = [
    # --- Dominio A — Identidad sociodemográfica ampliada (Tier 2, ancla Censo 2018) ---
    _v("education_level", "A", 2, "Censo CNPV 2018", "municipal", "IPF", "ordinal",
       ["ninguno", "primaria", "secundaria", "media", "tecnico", "universitario", "posgrado"]),
    _v("school_attendance", "A", 2, "Censo CNPV 2018", "municipal", "IPF", "binary", ["no", "si"]),
    _v("ethnic_self_recognition", "A", 2, "Censo CNPV 2018", "municipal", "IPF", "categorical",
       ["ninguno", "indigena", "afrocolombiano", "raizal", "rom", "palenquero"]),
    _v("mother_tongue", "A", 2, "Censo CNPV 2018", "municipal", "IPF", "categorical",
       ["espanol", "lengua_indigena", "creole", "otra"]),
    _v("socioeconomic_stratum", "A", 2, "Censo 2018 / estrato manzana", "manzana", "IPF", "ordinal",
       ["1", "2", "3", "4", "5", "6"]),
    _v("housing_tenure", "A", 2, "Censo CNPV 2018", "municipal", "IPF", "categorical",
       ["propia", "arriendo", "usufructo", "otra"]),
    _v("household_size", "A", 2, "Censo CNPV 2018", "municipal", "IPF", "count", unit="personas"),
    _v("dwelling_type", "A", 2, "Censo CNPV 2018", "municipal", "IPF", "categorical",
       ["casa", "apartamento", "cuarto", "otro"]),
    _v("migration_status", "A", 2, "Censo CNPV 2018", "municipal", "IPF", "binary", ["no", "si"]),
    _v("disability_status", "A", 2, "Censo CNPV 2018", "municipal", "IPF", "binary", ["no", "si"]),

    # --- Dominio B — Poder adquisitivo y economía del hogar (Tier 2–3) ---
    _v("household_income_decile", "B", 3, "GEIH", "regional", "copula", "ordinal",
       ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]),
    _v("purchasing_power_band", "B", 3, "GEIH + inclusion financiera", "regional", "copula", "ordinal",
       ["bajo", "medio_bajo", "medio", "medio_alto", "alto"]),
    _v("employment_status", "B", 3, "GEIH", "regional", "conditional", "categorical",
       ["ocupado", "desempleado", "inactivo", "estudiante"]),
    _v("occupation_sector", "B", 3, "GEIH", "regional", "conditional", "categorical",
       ["agro", "industria", "comercio", "servicios", "publico", "informal", "ninguno"]),
    _v("informality_status", "B", 3, "GEIH", "regional", "conditional", "binary", ["formal", "informal"]),
    _v("bank_account_holder", "B", 2, "Banca de las Oportunidades / SFC", "municipal", "IPF", "binary",
       ["no", "si"]),
    _v("credit_card_holder", "B", 3, "Inclusion financiera", "municipal", "copula", "binary", ["no", "si"]),
    _v("digital_payment_use", "B", 3, "Inclusion financiera + ENTIC", "regional", "copula", "binary",
       ["no", "si"]),
    _v("discretionary_spending_band", "B", 3, "GEIH / ENPH", "regional", "copula", "ordinal",
       ["nulo", "bajo", "medio", "alto"]),
    _v("savings_capacity", "B", 3, "Inclusion financiera", "regional", "copula", "ordinal",
       ["nula", "baja", "media", "alta"]),

    # --- Dominio C — Consumo cultural (Tier 3, ECC) ---
    _v("music_genre_preference", "C", 3, "Encuesta de Consumo Cultural (ECC)", "regional", "copula",
       "categorical", ["reggaeton", "vallenato", "salsa", "pop", "rock", "tropical", "electronica",
                        "regional_mexicana", "clasica", "otra"]),
    _v("music_listening_frequency", "C", 3, "ECC", "regional", "conditional", "ordinal",
       ["nunca", "ocasional", "semanal", "diaria"]),
    _v("live_concert_attendance", "C", 3, "ECC", "regional", "copula", "ordinal",
       ["nunca", "1-2_ano", "3-5_ano", "6+_ano"]),
    _v("cinema_attendance_frequency", "C", 3, "ECC", "regional", "copula", "ordinal",
       ["nunca", "ocasional", "mensual", "semanal"]),
    _v("favorite_film_genre", "C", 3, "ECC", "regional", "conditional", "categorical",
       ["accion", "comedia", "drama", "terror", "romance", "animacion", "documental", "ciencia_ficcion"]),
    _v("tv_viewing_hours", "C", 3, "ECC / ENUT", "regional", "conditional", "count", unit="horas_dia"),
    _v("favorite_tv_genre", "C", 3, "ECC", "regional", "conditional", "categorical",
       ["noticias", "telenovela", "deportes", "realities", "series", "infantil", "documentales",
        "entretenimiento"]),
    _v("reading_books_per_year", "C", 3, "ECC", "regional", "copula", "count", unit="libros_ano"),
    _v("reading_format", "C", 3, "ECC", "regional", "conditional", "categorical",
       ["no_lee", "impreso", "digital", "ambos"]),
    _v("videogame_player", "C", 3, "ECC", "regional", "copula", "binary", ["no", "si"]),
    _v("videogame_hours_week", "C", 3, "ECC / ENUT", "regional", "conditional", "count", unit="horas_semana"),
    _v("museum_gallery_visits", "C", 3, "ECC", "regional", "conditional", "ordinal",
       ["nunca", "1-2_ano", "3+_ano"]),
    _v("theater_dance_attendance", "C", 3, "ECC", "regional", "conditional", "ordinal",
       ["nunca", "1-2_ano", "3+_ano"]),
    _v("cultural_festival_participation", "C", 3, "ECC", "regional", "conditional", "binary", ["no", "si"]),

    # --- Dominio D — Tecnología, medios y vida digital (Tier 3, ENTIC) ---
    _v("smartphone_ownership", "D", 3, "ENTIC Hogares", "departamental", "conditional", "binary",
       ["no", "si"]),
    _v("internet_access_home", "D", 2, "MinTIC / Postdata", "municipal", "IPF", "binary", ["no", "si"]),
    _v("internet_use_frequency", "D", 3, "ENTIC", "departamental", "conditional", "ordinal",
       ["nunca", "ocasional", "semanal", "diaria"]),
    _v("primary_social_platform", "D", 3, "ENTIC", "departamental", "conditional", "categorical",
       ["whatsapp", "facebook", "instagram", "tiktok", "youtube", "x", "ninguna"]),
    _v("social_media_hours_day", "D", 3, "ENTIC / ENUT", "departamental", "copula", "count", unit="horas_dia"),
    _v("streaming_video_subscription", "D", 3, "ENTIC + inclusion financiera", "departamental", "copula",
       "binary", ["no", "si"]),
    _v("streaming_music_subscription", "D", 3, "ENTIC", "departamental", "copula", "binary", ["no", "si"]),
    _v("ecommerce_purchase_frequency", "D", 3, "ENTIC", "departamental", "copula", "ordinal",
       ["nunca", "ocasional", "mensual", "semanal"]),
    _v("device_count_household", "D", 3, "ENTIC", "departamental", "conditional", "count", unit="dispositivos"),
    _v("digital_skills_index", "D", 3, "ENTIC", "departamental", "derived", "ordinal",
       ["bajo", "medio", "alto"]),

    # --- Dominio E — Estilo de vida, ocio y movilidad (Tier 3, ENUT) ---
    _v("sports_practice_frequency", "E", 3, "ENUT / ECC", "regional", "conditional", "ordinal",
       ["nunca", "ocasional", "semanal", "diaria"]),
    _v("commute_mode", "E", 3, "ENUT / Censo", "regional", "conditional", "categorical",
       ["a_pie", "bicicleta", "moto", "transporte_publico", "auto", "otro"]),
    _v("bicycle_use", "E", 3, "ENUT / encuestas movilidad", "regional", "conditional", "ordinal",
       ["nunca", "ocasional", "frecuente", "diario"]),
    _v("eating_out_frequency", "E", 3, "ENPH / ENUT", "regional", "conditional", "ordinal",
       ["nunca", "mensual", "semanal", "diaria"]),
    _v("nightlife_frequency", "E", 3, "ECC / ENUT", "regional", "conditional", "ordinal",
       ["nunca", "mensual", "quincenal", "semanal"]),
    _v("religious_practice", "E", 3, "ENUT / encuestas valores", "regional", "conditional", "ordinal",
       ["nunca", "ocasional", "frecuente", "diaria"]),

    # --- Dominio F — Psicografía y segmentos derivados (Tier 3, índices) ---
    _v("consumer_psychographic_segment", "F", 3, "Derivado (clustering B–E)", "regional", "derived",
       "categorical", ["tradicional", "aspiracional", "digital_first", "pragmatico",
                       "experiencial", "ahorrador"]),
    _v("early_adopter_index", "F", 3, "Derivado (ENTIC + consumo)", "regional", "derived", "ordinal",
       ["rezagado", "mayoria_tardia", "mayoria_temprana", "adoptador_temprano", "innovador"]),
]

assert len(VARIABLES) == 52, f"Se esperaban 52 variables, hay {len(VARIABLES)}"

VARIABLES_BY_NAME = {v["name"]: v for v in VARIABLES}
VARIABLES_BY_DOMAIN: dict[str, list[dict]] = {d: [] for d in DOMAINS}
for _var in VARIABLES:
    VARIABLES_BY_DOMAIN[_var["domain"]].append(_var)


def public_dictionary() -> list[dict]:
    """Vista del diccionario apta para exponer en la API (con estado de validación)."""
    rows = []
    for v in VARIABLES:
        rows.append({
            "name": v["name"],
            "domain": v["domain"],
            "domain_label": DOMAINS[v["domain"]],
            "tier": v["tier"],
            "source": v["source"],
            "truth_granularity": v["truth_granularity"],
            "method": v["method"],
            "dtype": v["dtype"],
            "categories": v["categories"],
            "unit": v["unit"],
            # Tier 2 entra como release validada; Tier 3 requiere validación externa
            # antes de publicarse a nivel municipal (ver gate en validation.py).
            "status": "anchored" if v["tier"] == 2 else "modelled_pending_external_validation",
        })
    return rows
