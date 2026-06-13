# GenZ Colombia API - Resumen de Arquitectura

## Visión General

API privada de datos sintéticos de la Generación Z colombiana (12-28 años), segmentada por ciudad, barrio/comuna/localidad y estrato socioeconómico. Diseñada para investigación demográfica y análisis de mercado con datos que preservan distribuciones estadísticas reales basadas en fuentes oficiales colombianas.

## Decisiones Arquitectónicas

### Fase 0 — Descubrimiento

| Decisión | Elección | Justificación |
|----------|----------|---------------|
| **Objetivo** | API privada de datos sintéticos Gen Z por suscripción | Modelo de negocio claro, datos de interés público |
| **Lenguaje/Framework** | Python 3.11+ / FastAPI | Ecosistema rico para datos (pandas, numpy), OpenAPI nativo, async nativo |
| **Base de datos** | Supabase (PostgreSQL gestionado) | Relacional fuerte, PostGIS disponible, API REST automática, auth incluido |
| **Modelo de liberación** | API REST privada con API keys + tiers | Monetización por suscripción, control de acceso granular |
| **Despliegue** | Docker + docker-compose local, portable a Railway/Render/VPS | Desarrollo rápido, infraestructura portable |

### Fase 1 — Arquitectura y Diseño

#### Modelo de Datos Normalizado

```
cities (1) ──── (N) neighborhoods
   │                    │
   │                    │
   └────── (N) persons ─┘

api_keys (1) ──── (1) subscriptions
   │
   └────── (N) query_logs
```

**Entidades:**
- `cities`: Ciudades con códigos DIVIPOLA oficiales (Bogotá 11001, Medellín 05001)
- `neighborhoods`: 20 localidades Bogotá + 16 comunas Medellín
- `persons`: Personas sintéticas Gen Z con 12 variables
- `api_keys`: Autenticación con bcrypt hashing
- `subscriptions`: Tiers y límites de acceso
- `query_logs`: Trazabilidad completa

#### Variables de Personas Sintéticas

**Demográficas:**
- edad (12-28)
- sexo (M/F)
- estrato (1-6)

**Geográficas:**
- ciudad_divipola (código DIVIPOLA)
- neighborhood_code (código barrio/comuna)

**Educativas/Ocupacionales:**
- nivel_educativo (8 categorías)
- ocupacion (6 categorías CUOC simplificada)

**Conectividad/Comportamiento:**
- acceso_internet (boolean)
- interes_musical (12 categorías)
- interes_tecnologico (11 categorías)
- uso_bicicleta (5 frecuencias)

#### Distribuciones Estadísticas Implementadas

| Variable | Distribución | Fuente |
|----------|--------------|--------|
| Estratos Bogotá | 15% E1, 35% E2, 30% E3, 12% E4, 5% E5, 3% E6 | DANE ECV |
| Estratos Medellín | 18% E1, 33% E2, 32% E3, 12% E4, 4% E5, 1% E6 | DANE ECV |
| Sexo | 48% M, 52% F | DANE Proyecciones |
| Edad | Pico en 18-24, distribución Gen Z | DANE CNPV |
| Nivel educativo | Condicional a edad y estrato | DANE + ICFES |
| Ocupación | Condicional a edad y nivel educativo | DANE GEIH |
| Acceso internet | 75-99% según estrato | MinTIC ENTIC |

#### Códigos Oficiales

- **DIVIPOLA**: Clasificación político-administrativa de Colombia (DANE)
- **Localidades Bogotá**: 20 localidades con códigos 11001-11020
- **Comunas Medellín**: 16 comunas con códigos 05001-01 a 05001-16
- **CUOC**: Clasificación Uniforme de Ocupaciones de Colombia
- **Estratos**: Ley 142 de 1994 (1-6)

### Fase 2 — Implementación

#### Estructura del Proyecto

```
genz-api/
├── app/
│   ├── main.py                 # Aplicación FastAPI principal
│   ├── config.py               # Configuración (pydantic-settings)
│   ├── database.py             # SQLAlchemy async + Supabase
│   ├── models/                 # Modelos SQLAlchemy
│   │   ├── city.py
│   │   ├── neighborhood.py
│   │   ├── person.py
│   │   ├── api_key.py
│   │   ├── subscription.py
│   │   └── query_log.py
│   ├── schemas/                # Schemas Pydantic
│   │   ├── city.py
│   │   ├── neighborhood.py
│   │   ├── person.py
│   │   └── query.py
│   ├── api/
│   │   ├── deps.py             # Dependencias (auth, rate limit)
│   │   ├── middleware/
│   │   │   ├── auth.py         # Middleware autenticación
│   │   │   └── rate_limit.py   # Middleware rate limiting
│   │   └── routes/
│   │       ├── health.py       # GET /health
│   │       ├── metadata.py     # GET /metadata
│   │       ├── cities.py       # GET /cities
│   │       ├── neighborhoods.py # GET /neighborhoods
│   │       ├── population.py   # POST /population/sample
│   │       └── aggregate.py    # POST /aggregate/query
│   ├── services/
│   │   └── data_generator.py   # Generador de datos sintéticos
│   └── utils/
│       └── divipola.py         # Códigos DIVIPOLA oficiales
├── scripts/
│   ├── seed_data.py            # Seed data (1000 personas)
│   └── create_api_keys.py      # Generador seguro de API keys
├── tests/                      # Tests pytest
├── alembic/                    # Migraciones de BD
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── Makefile
└── README.md
```

#### Endpoints Implementados

| Método | Endpoint | Auth | Descripción |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check básico |
| GET | `/health/detailed` | No | Health check con estado BD |
| GET | `/metadata` | Sí | Metadata completa del dataset |
| GET | `/schema` | Sí | Esquema de entidades y relaciones |
| GET | `/cities` | Sí | Listar ciudades |
| GET | `/cities/{divipola}` | Sí | Ciudad por DIVIPOLA |
| GET | `/neighborhoods?city=` | Sí | Barrios/comunas por ciudad |
| POST | `/population/sample` | Sí | Muestreo con filtros |
| POST | `/aggregate/query` | Sí | Agregaciones sin microdatos |

#### Sistema de Autenticación

- **Mecanismo**: API key en header `X-API-Key`
- **Hashing**: bcrypt (passlib)
- **Almacenamiento**: Solo hashes en BD, keys planas nunca se guardan
- **Validación**: Middleware que verifica key en cada request (excepto /health)
- **Trazabilidad**: Cada request se loguea en `query_logs`

#### Rate Limiting por Tier

| Tier | Requests/min | Requests/día | Muestra máx | Descargas |
|------|--------------|--------------|-------------|-----------|
| Free | 100 | 1,000 | 100 | No |
| Pro | 1,000 | 10,000 | 500 | Sí |
| Enterprise | 10,000 | 100,000 | 1,000 | Sí |

#### Guardas de Seguridad

1. **IDs sintéticos**: Hashes SHA-256 irreversibles, no IDs reales
2. **Sin singling out**: No se permiten filtros hiper-específicos
3. **Rate limiting**: Protege contra scraping masivo
4. **Trazabilidad**: Todas las consultas se registran
5. **Hashing de keys**: bcrypt, nunca se guardan keys planas
6. **CORS configurado**: Solo orígenes permitidos
7. **Validación de entrada**: Pydantic valida todos los inputs

### Fase 3 — Calidad y Validación

#### Tests Implementados

- `test_health.py`: Health check básico y detallado
- `test_metadata.py`: Metadata y schema
- `test_cities.py`: Listado de ciudades y filtros
- `test_population.py`: Muestreo con varios filtros
- `test_aggregate.py`: Agregaciones y validación de inputs

#### Validaciones de Datos Sintéticos

1. **Distribuciones marginales**: Estratos por ciudad calibrados según DANE
2. **Correlaciones edad-educación**: Niveles educativos condicionados a edad
3. **Correlaciones estrato-conectividad**: Acceso a internet condicional a estrato
4. **Rangos válidos**: Edad 12-28, estrato 1-6, códigos DIVIPOLA oficiales
5. **Consistencia territorial**: Barrios/comunas pertenecen a ciudades correctas

#### Métricas de Calidad

- **Cobertura de tests**: Tests para todos los endpoints principales
- **Tipado estricto**: Pydantic schemas + SQLAlchemy models
- **Documentación**: OpenAPI 3.0 completo con descripciones
- **Logging estructurado**: Cada request trazable con timing

### Fase 4 — Despliegue y Entrega

#### Artefactos de Despliegue

- `Dockerfile`: Imagen optimizada Python 3.11-slim
- `docker-compose.yml`: Servicios API + PostgreSQL + seed
- `Makefile`: Comandos comunes para desarrollo
- `QUICKSTART.md`: Guía de inicio rápido

#### Portabilidad

La API es portable a:
- **Railway**: Deploy desde git, PostgreSQL incluido
- **Render**: Web service con build commands
- **VPS**: Docker en cualquier servidor Linux
- **Supabase**: Ya compatible como backend de BD

#### Variables de Entorno

Todas configurables vía `.env`:
- DATABASE_URL (async)
- DATABASE_URL_SYNC (para Alembic)
- APP_NAME, APP_VERSION, DEBUG, ENVIRONMENT
- RATE_LIMIT_FREE, RATE_LIMIT_PRO, RATE_LIMIT_ENTERPRISE
- CORS_ORIGINS

## Fuentes de Datos

### Primarias
- DANE - Censo Nacional de Población y Vivienda (CNPV)
- DANE - Gran Encuesta Integrada de Hogares (GEIH)
- DANE - Encuesta Continua de Hogares (ECH)
- DANE - Proyecciones de población 2018-2035
- ICFES - Resultados Saber 11 y Saber Pro
- MinTIC - Encuesta de Tecnologías de la Información (ENTIC)

### Territoriales
- Datos Abiertos Bogotá
- MEData - Medellín Datos Abiertos
- Área Metropolitana del Valle de Aburrá

### Clasificaciones Oficiales
- DIVIPOLA: División Político-Administrativa de Colombia
- CUOC: Clasificación Uniforme de Ocupaciones
- CIIU: Clasificación Industrial Internacional Uniforme
- Estratos: Ley 142 de 1994

## Limitaciones Conocidas

1. **Datos sintéticos**: No representan individuos reales, solo preservan distribuciones
2. **Cobertura geográfica**: Solo Bogotá y Medellín (expandible)
3. **Rango de edad**: Solo Gen Z (12-28 años)
4. **Variables conductuales**: Distribuciones estimadas, no validadas con encuestas específicas
5. **Temporalidad**: Datos estáticos, no incluyen tendencias temporales

## Próximos Pasos Recomendados

### Corto Plazo
1. **Validación estadística**: Comparar distribuciones sintéticas vs datos reales DANE
2. **Más ciudades**: Expandir a Cali, Barranquilla, Cartagena
3. **Variables adicionales**: Ingresos, tenencia de dispositivos, redes sociales
4. **Tests de privacidad**: Evaluar riesgo de singling out, linkability, inference

### Mediano Plazo
1. **API de series temporales**: Datos sintéticos por año (2018-2024)
2. **Descarga de datasets**: Endpoints para descargar CSV/Parquet por versión
3. **Dashboard de calidad**: Visualización de distribuciones y validaciones
4. **Integración con Stripe**: Gestión de suscripciones y billing

### Largo Plazo
1. **Generador condicional avanzado**: Modelos generativos (VAE, GAN) para datos sintéticos
2. **API de predicción**: Modelos ML entrenados con datos sintéticos
3. **Expansión nacional**: Todas las ciudades principales de Colombia
4. **Colaboración con DANE**: Validación oficial de distribuciones

## Metodología de Generación Sintética

### Principios
1. **Columna vertebral primero**: Variables demográficas estructurales antes que conductuales
2. **Distribuciones condicionales**: Variables dependientes modeladas con correlaciones reales
3. **Fuentes oficiales**: Calibración con datos DANE, ICFES, MinTIC
4. **Reproducibilidad**: Semilla fija (42) para generación determinística
5. **Validación multinivel**: Marginales, bivariados, correlaciones, perfiles por subgrupo

### Proceso de Generación
1. Generar edad con distribución Gen Z (pico 18-24)
2. Generar sexo (48% M, 52% F)
3. Generar ciudad (75% Bogotá, 25% Medellín)
4. Generar barrio/comuna (uniforme dentro de ciudad)
5. Generar estrato (distribución por ciudad según DANE)
6. Generar nivel educativo (condicional a edad + estrato)
7. Generar ocupación (condicional a edad + educación)
8. Generar acceso internet (condicional a estrato)
9. Generar intereses musicales y tecnológicos (distribuciones Gen Z)
10. Generar uso de bicicleta (condicional a ciudad + estrato)

### Guardas de Privacidad
- IDs sintéticos (hashes irreversibles)
- No exponer identificadores reales
- No permitir filtros hiper-específicos
- Rate limiting por tier
- Trazabilidad de todas las consultas

## Conclusión

La API está completamente funcional y lista para:
- Desarrollo local con Docker
- Despliegue en Railway/Render/VPS
- Integración con Supabase como backend
- Consumo por clientes con API keys
- Expansión a más ciudades y variables

La arquitectura es modular, portable y sigue mejores prácticas de la industria para APIs de datos sintéticos con fines de investigación.
