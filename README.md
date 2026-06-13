# GenZ Colombia API

API privada de datos sintéticos de la **Generación Z colombiana** (jóvenes de 12 a 28 años), segmentada por ciudad, barrio/comuna/localidad y estrato socioeconómico.

## Descripción

Esta API expone datos **sintéticos** que preservan distribuciones marginales y correlaciones estadísticas basadas en fuentes oficiales colombianas:

- **DANE**: Censo Nacional de Población y Vivienda (CNPV), Gran Encuesta Integrada de Hogares (GEIH), Encuesta Continua de Hogares (ECH), Proyecciones de población
- **ICFES**: Resultados Saber 11 y Saber Pro
- **MinTIC**: Encuesta de Tecnologías de la Información (ENTIC)
- **Datos territoriales**: Datos Abiertos Bogotá, MEData Medellín, Área Metropolitana del Valle de Aburrá

**Importante**: Los datos expuestos son SINTÉTICOS. No representan individuos reales.

## Características

- Datos sintéticos con distribuciones realistas (estratos, edades, niveles educativos)
- Segmentación geográfica: Bogotá (20 localidades) y Medellín (16 comunas)
- Códigos DIVIPOLA oficiales
- Autenticación por API key con tiers (free, pro, enterprise)
- Rate limiting diferenciado por tier
- Trazabilidad completa de consultas
- Documentación OpenAPI 3.0 interactiva

## Stack Tecnológico

- **Backend**: Python 3.11+ / FastAPI
- **Base de datos**: PostgreSQL (Supabase o local)
- **ORM**: SQLAlchemy 2.0 (async)
- **Autenticación**: API keys con bcrypt hashing
- **Rate limiting**: slowapi
- **Contenedores**: Docker + docker-compose

## Inicio Rápido

### 1. Clonar y configurar

```bash
cd genz-api
cp .env.example .env
# Editar .env con tus variables si es necesario
```

### 2. Levantar con Docker Compose

```bash
# Levantar BD y API
docker-compose up -d

# Esperar a que los servicios estén listos
docker-compose ps

# Ejecutar seed data (puebla la BD)
docker-compose run --rm seed
```

### 3. Acceder a la API

- **API**: http://localhost:8000
- **Documentación interactiva (Swagger)**: http://localhost:8000/docs
- **Documentación ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 4. Probar endpoints

```bash
# Health check (público)
curl http://localhost:8000/health

# Metadata (requiere API key)
curl -H "X-API-Key: genz_free_test_key_12345" http://localhost:8000/metadata

# Listar ciudades
curl -H "X-API-Key: genz_free_test_key_12345" http://localhost:8000/cities

# Muestreo de población
curl -X POST http://localhost:8000/population/sample \
  -H "X-API-Key: genz_free_test_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"ciudad_divipola": "11001", "estrato": 3, "sample_size": 10}'

# Agregación
curl -X POST http://localhost:8000/aggregate/query \
  -H "X-API-Key: genz_free_test_key_12345" \
  -H "Content-Type: application/json" \
  -d '{"group_by": ["ciudad_divipola", "estrato"], "metric": "count"}'
```

## API Keys de Prueba

Después de ejecutar el seed data, tendrás estas API keys disponibles:

| Tier | API Key | Límites |
|------|---------|---------|
| Free | `genz_free_test_key_12345` | 100 req/min, 1000 req/día, muestra máx 100 |
| Pro | `genz_pro_test_key_67890` | 1000 req/min, 10000 req/día, muestra máx 500 |
| Enterprise | `genz_enterprise_test_key_abcde` | 10000 req/min, 100000 req/día, muestra máx 1000 |

**Importante**: Estas keys son solo para desarrollo. En producción, genera keys seguras.

## Endpoints

### Públicos (sin autenticación)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check básico |
| GET | `/health/detailed` | Health check con estado de BD |

### Autenticados (requieren `X-API-Key`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/metadata` | Metadata del dataset (variables, fuentes, metodología) |
| GET | `/schema` | Esquema de entidades y relaciones |
| GET | `/cities` | Listar ciudades con códigos DIVIPOLA |
| GET | `/cities/{divipola}` | Obtener ciudad por DIVIPOLA |
| GET | `/neighborhoods?city={divipola}` | Listar barrios/comunas por ciudad |
| POST | `/population/sample` | Muestreo de personas sintéticas con filtros |
| POST | `/aggregate/query` | Consultas de agregación (sin microdatos) |

### Filtros disponibles en `/population/sample`

- `ciudad_divipola`: Código DIVIPOLA de la ciudad
- `neighborhood_code`: Código de barrio/comuna/localidad
- `estrato`: Estrato socioeconómico (1-6)
- `edad_min`, `edad_max`: Rango de edad (12-28)
- `sexo`: M o F
- `nivel_educativo`: Nivel educativo
- `ocupacion`: Ocupación
- `acceso_internet`: Booleano
- `interes_musical`: Género musical
- `interes_tecnologico`: Área tecnológica
- `uso_bicicleta`: Frecuencia de uso
- `sample_size`: Tamaño de muestra (1-1000)

### Métricas disponibles en `/aggregate/query`

- `count`: Conteo de registros por grupo
- `avg_edad`: Promedio de edad por grupo
- `pct_internet`: Porcentaje con acceso a internet por grupo

### Agrupaciones permitidas en `/aggregate/query`

- `ciudad_divipola`
- `neighborhood_code`
- `estrato`
- `sexo`
- `nivel_educativo`
- `ocupacion`
- `interes_musical`
- `interes_tecnologico`
- `uso_bicicleta`

## Modelo de Datos

### Entidades

- **cities**: Ciudades con códigos DIVIPOLA oficiales
- **neighborhoods**: Barrios/comunas/localidades
- **persons**: Personas sintéticas de la Gen Z
- **api_keys**: API keys para autenticación
- **subscriptions**: Suscripciones con tiers y límites
- **query_logs**: Logs de consultas para trazabilidad

### Variables de personas sintéticas

- **Demográficas**: edad, sexo, estrato
- **Geográficas**: ciudad_divipola, neighborhood_code
- **Educativas**: nivel_educativo
- **Ocupacionales**: ocupacion
- **Conectividad**: acceso_internet
- **Conductuales**: interes_musical, interes_tecnologico, uso_bicicleta

### Distribuciones implementadas

- **Estratos por ciudad**: Basados en ECV/GEIH del DANE
- **Sexo**: 48% M, 52% F (proyecciones DANE)
- **Edades**: Distribución con pico en 18-24 años
- **Nivel educativo**: Condicional a edad y estrato
- **Ocupación**: Condicional a edad y nivel educativo
- **Acceso a internet**: Condicional a estrato (basado en ENTIC)

## Desarrollo Local (sin Docker)

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar BD PostgreSQL local
# (o usar Supabase)

# Ejecutar seed data
python -m scripts.seed_data

# Levantar API
uvicorn app.main:app --reload
```

## Tests

```bash
# Ejecutar tests
pytest tests/ -v

# Con cobertura
pytest tests/ --cov=app --cov-report=html
```

## Despliegue

### Railway

```bash
# Instalar CLI de Railway
npm i -g @railway/cli

# Login y deploy
railway login
railway init
railway up
```

### Render

1. Conectar repositorio en Render Dashboard
2. Configurar build command: `pip install -r requirements.txt`
3. Configurar start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Agregar variables de entorno

### VPS / Docker

```bash
# Build imagen
docker build -t genz-api .

# Run
docker run -d -p 8000:8000 --env-file .env genz-api
```

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_URL` | URL de conexión async a PostgreSQL | `postgresql+asyncpg://...` |
| `DATABASE_URL_SYNC` | URL de conexión sync (para Alembic) | `postgresql://...` |
| `APP_NAME` | Nombre de la aplicación | `GenZ Colombia API` |
| `APP_VERSION` | Versión de la API | `1.0.0` |
| `DEBUG` | Modo debug | `false` |
| `ENVIRONMENT` | Entorno (development/production) | `development` |
| `RATE_LIMIT_FREE` | Rate limit para tier free | `100/minute` |
| `RATE_LIMIT_PRO` | Rate limit para tier pro | `1000/minute` |
| `RATE_LIMIT_ENTERPRISE` | Rate limit para tier enterprise | `10000/minute` |
| `CORS_ORIGINS` | Orígenes CORS permitidos (JSON) | `["http://localhost:3000"]` |

## Metodología de Generación de Datos Sintéticos

1. **Columna vertebral demográfica**: Primero se construyen las variables estructurales (edad, sexo, ciudad, barrio, estrato) con distribuciones calibradas según DANE.
2. **Capa educativa y ocupacional**: Se generan condicionalmente a edad y estrato, preservando correlaciones reales.
3. **Capa de conectividad y comportamiento**: Acceso a internet condicional a estrato (ENTIC), intereses musicales y tecnológicos con distribuciones de Gen Z.
4. **Validación**: Se verifican distribuciones marginales y correlaciones bivariadas.

## Guardas de Seguridad y Privacidad

- **IDs sintéticos**: Los identificadores son hashes irreversibles, no hay IDs reales.
- **Sin singling out**: No se permiten filtros hiper-específicos que aislen individuos.
- **Rate limiting**: Protege contra scraping masivo.
- **Trazabilidad**: Todas las consultas se registran en `query_logs`.
- **Tiers de acceso**: Diferentes niveles de acceso según suscripción.

## Fuentes y Referencias

- [DANE - División Político-Administrativa (DIVIPOLA)](https://www.dane.gov.co)
- [DANE - Proyecciones de Población](https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion/)
- [DANE - Encuesta de Calidad de Vida (ECV)](https://www.dane.gov.co/index.php/estadisticas-por-tema/pobreza-y-condiciones-de-vida/encuesta-de-calidad-de-vida-ecv/)
- [MinTIC - ENTIC](https://www.mintic.gov.co/portal/715/w3-article-3224.html)
- [ICFES - Datos Abiertos](https://www.icfes.gov.co/resultados)

## Licencia

Este proyecto es de uso interno para investigación. Los datos sintéticos generados no representan individuos reales.

## Contacto

Para consultas sobre la API o solicitudes de acceso, contacta al equipo de desarrollo.

---

**Nota**: Esta API expone datos sintéticos con fines de investigación y análisis demográfico. No utilizar para tomar decisiones individuales sobre personas reales.
