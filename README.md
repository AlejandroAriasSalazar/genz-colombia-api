# GenZ Colombia API V3

API de producción que parte de las proyecciones demográficas oficiales del DANE y
añade una **capa de enriquecimiento de 52 variables** culturales, sociales y
económicas (gustos musicales, programas de TV, poder adquisitivo, consumo cultural,
tecnología, estilo de vida y psicografía) generadas con **síntesis de población
rigurosa**: IPF anclado a marginales locales + cópula gaussiana condicional, con
incertidumbre cuantificada y gate de validación.

V3 implementa la `Propuesta_Enriquecimiento_GenZ_API` (incluida en esta carpeta).

## Qué es real, qué es anclado y qué es modelado

- **Tier 1 · Oficial (real):** municipio, sexo, edad, año. Celdas agregadas del DANE,
  reconciliadas. Es la restricción dura: los totales no se alteran.
- **Tier 2 · Anclado:** educación, estrato, etnia, vivienda, conectividad, bancarización.
  Imputado con **IPF** a un marginal local verificable (Censo 2018 / MinTIC). Granularidad
  municipal. Uso comercial libre con cita.
- **Tier 3 · Modelado:** ingreso, consumo cultural, música, TV, tecnología, ocio. Aprendido
  de encuestas (ECC/GEIH/ENTIC) vía **cópula/condicional**. Verdad **regional**; se entrega
  con banda de confianza y NO se publica a municipal sin **validación externa**.
- **Tier 4 · Señal (no incluido como microdato):** tendencias en vivo (qué suena/ve la
  gente ahora) — capa efímera separada, "tendencia, no población".

> **Estado de los datos:** el motor está completo y verificado, pero las distribuciones
> condicionales actuales son **ILUSTRATIVAS** (calibradas a patrones plausibles de
> Colombia). En producción se reemplazan por las estimadas de los microdatos reales con
> sus factores de expansión, y cada variable Tier 3 pasa el gate de validación externa
> antes de habilitarse a municipal. Ver `app/services/enrichment/seeds.py`.

## Mecanismo de enriquecimiento (4 capas)

```text
Capa 0  Ancla oficial DANE (municipio×año×sexo×edad)  — totales = restricción dura
Capa 1  IPF  -> variables Tier 2 ancladas a marginales locales (consistencia exacta)
Capa 2  Cópula gaussiana + modelos condicionales -> distribución conjunta Tier 3
Capa 3  Incertidumbre por variable + gate de validación (interna SRMSE/TAE + externa)
```

- **IPF** (`app/services/enrichment/ipf.py`): ajusta una semilla de asociación a los
  marginales locales hasta que todos los márgenes coinciden. Garantiza consistencia con
  los totales oficiales; no inventa correlaciones sin ancla.
- **Cópula** (`copula.py`): cópula gaussiana (CDF normal e inversa sin scipy) que preserva
  el co-movimiento entre variables Tier 3 (p. ej. ingreso↔streaming) condicionado al bloque
  anclado.
- **Reproducibilidad:** el bloque enriquecido deriva de la identidad estable HMAC más
  `enrichment_model_version`. Misma seed + versión de dataset + versión de modelo ⇒ misma
  persona multivariable, estable entre entornos.
- **Incertidumbre:** cada atributo lleva `confidence`, `interval` y `truth_granularity`,
  con penalización por transferencia al bajar de la granularidad de verdad a municipal.

## Endpoints nuevos en V3

Autenticados con `X-API-Key`:

- `POST /api/v3/population/sample` — admite `"enrich": true` y `"enrich_domains": ["A".."F"]`.
  Cada persona regresa con su bloque `enrichment` (requiere scope `enrich:read`, planes Pro/Enterprise).

Públicos / catálogo:

- `GET /api/v3/metadata` — incluye el resumen del enriquecimiento y el diccionario completo.
- `GET /api/v3/enrichment/dictionary` — catálogo de las 52 variables (tier, fuente, granularidad, método, categorías).
- `GET /api/v3/enrichment/model` — metadatos del modelo y estado de los datos.

Con scope `enrich:read`:

- `GET /api/v3/enrichment/validation` — reporte del gate (IPF SRMSE/TAE por zona,
  reproducción de marginales, co-movimiento de la cópula, estado de validación externa).

Todo lo demás de V2 (cities, departments, aggregate/query, market/*, report) se mantiene
bajo el prefijo `/api/v3`.

## Ejemplo

```bash
curl -X POST http://localhost:8000/api/v3/population/sample \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $GENZ_API_KEY" \
  -d '{
    "filters": {"municipality_code": "11001", "year": 2026, "age_min": 18, "age_max": 24},
    "sample_size": 50,
    "seed": 2026,
    "enrich": true,
    "enrich_domains": ["B", "C", "D"]
  }'
```

Cada persona incluirá, por ejemplo:

```json
"enrichment": {
  "music_genre_preference": {"value": "reggaeton", "tier": 3, "source": "ECC",
     "truth_granularity": "regional", "method": "copula", "confidence": 0.574,
     "p_value": 0.41, "interval": [0.17, 0.65]},
  "household_income_decile": {"value": "5", "tier": 3, "method": "copula", "confidence": 0.574, ...},
  "socioeconomic_stratum": {"value": "3", "tier": 2, "method": "IPF", "confidence": 0.9, ...}
}
```

## Variables (52, por dominio)

- **A · Identidad sociodemográfica (10, Tier 2):** educación, asistencia escolar, etnia,
  lengua materna, estrato, tenencia y tipo de vivienda, tamaño del hogar, migración, discapacidad.
- **B · Poder adquisitivo (10):** decil de ingreso, poder adquisitivo, empleo, sector,
  informalidad, bancarización, tarjeta de crédito, pagos digitales, gasto discrecional, ahorro.
- **C · Consumo cultural (14):** gustos musicales, frecuencia, conciertos, cine, género de
  cine/TV favorito, horas de TV, lectura, videojuegos, museos, teatro, festivales.
- **D · Tecnología y vida digital (10):** smartphone, internet en hogar, frecuencia de uso,
  red social principal, horas en redes, streaming video/música, e-commerce, dispositivos,
  competencias digitales.
- **E · Estilo de vida y movilidad (6):** deporte, modo de transporte, bicicleta, comer fuera,
  vida nocturna, práctica religiosa.
- **F · Psicografía (2):** segmento psicográfico, índice de adopción tecnológica.

Catálogo completo y categorías en `GET /api/v3/enrichment/dictionary`.

## Verificación

```bash
make lint
make test            # suite completa (requiere PostgreSQL/Redis en CI)
```

Tests del motor de enriquecimiento en `tests/test_enrichment.py`: el IPF reproduce los
marginales objetivo (SRMSE < 1e-3), la cópula preserva el co-movimiento ingreso↔consumo,
el muestreo es reproducible por identidad, el diccionario tiene 52 variables y el gate pasa
la validación interna pero **bloquea Tier 3 a municipal** sin fuente externa.

## Límites (heredados del análisis legal/metodológico)

- Las encuestas DANE (ECC/GEIH/ENTIC) se usan **solo como modelo de correlación**; no se
  redistribuye su microdato.
- Las variables Tier 3 son representativas a nivel regional; bajarlas a municipal exige
  validación externa o se entregan como estimación regional explícita.
- Cada variable entra por el quality gate con su fuente y tier, o no entra al microdato.

Fuente demográfica base: DANE, *Serie municipal de población por área, sexo y edad
2018-2042* (actualización 8 de agosto de 2025).
