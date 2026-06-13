# Guía de Inicio Rápido - GenZ Colombia API

## Paso 1: Configurar entorno

```bash
cd genz-api
cp .env.example .env
```

## Paso 2: Levantar servicios con Docker

```bash
# Levantar BD PostgreSQL y API
docker-compose up -d

# Verificar que los servicios están corriendo
docker-compose ps
```

Espera ~10 segundos a que PostgreSQL esté listo.

## Paso 3: Ejecutar seed data

```bash
# Poblar la base de datos con datos sintéticos
docker-compose run --rm seed
```

Esto creará:
- 2 ciudades (Bogotá y Medellín)
- 36 barrios/comunas/localidades (20 localidades Bogotá + 16 comunas Medellín)
- 1000 personas sintéticas
- 3 API keys de prueba (free, pro, enterprise)

## Paso 4: Probar la API

### Health check (público)
```bash
curl http://localhost:8000/health
```

### Metadata (requiere API key)
```bash
curl -H "X-API-Key: genz_free_test_key_12345" http://localhost:8000/metadata
```

### Listar ciudades
```bash
curl -H "X-API-Key: genz_free_test_key_12345" http://localhost:8000/cities
```

### Listar barrios de Bogotá
```bash
curl -H "X-API-Key: genz_free_test_key_12345" "http://localhost:8000/neighborhoods?city=11001"
```

### Muestreo de población
```bash
curl -X POST http://localhost:8000/population/sample \
  -H "X-API-Key: genz_free_test_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "ciudad_divipola": "11001",
    "estrato": 3,
    "edad_min": 18,
    "edad_max": 24,
    "sample_size": 10
  }'
```

### Consulta de agregación
```bash
curl -X POST http://localhost:8000/aggregate/query \
  -H "X-API-Key: genz_free_test_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "group_by": ["ciudad_divipola", "estrato"],
    "metric": "count"
  }'
```

## Paso 5: Acceder a documentación interactiva

Abre en tu navegador:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Keys de prueba

| Tier | API Key | Límites |
|------|---------|---------|
| Free | `genz_free_test_key_12345` | 100 req/min, muestra máx 100 |
| Pro | `genz_pro_test_key_67890` | 1000 req/min, muestra máx 500 |
| Enterprise | `genz_enterprise_test_key_abcde` | 10000 req/min, muestra máx 1000 |

## Comandos útiles

```bash
# Ver logs de la API
docker-compose logs -f api

# Ver logs de la BD
docker-compose logs -f db

# Reiniciar servicios
docker-compose restart

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v

# Ejecutar tests
docker-compose exec api pytest tests/ -v
```

## Desarrollo local sin Docker

Si prefieres desarrollar sin Docker:

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar PostgreSQL local o usar Supabase
# Editar .env con DATABASE_URL

# Ejecutar seed data
python3 -m scripts.seed_data

# Levantar API
uvicorn app.main:app --reload
```

## Crear nuevas API keys

```bash
# Crear key para tier free
python3 -m scripts.create_api_keys --name "Mi App" --tier free

# Crear key para tier pro
python3 -m scripts.create_api_keys --name "Cliente Premium" --tier pro

# Crear key para tier enterprise
python3 -m scripts.create_api_keys --name "Enterprise Client" --tier enterprise
```

## Troubleshooting

### La API no responde
```bash
# Verificar que los servicios están corriendo
docker-compose ps

# Ver logs de la API
docker-compose logs api

# Reiniciar servicios
docker-compose restart
```

### Error de conexión a BD
```bash
# Verificar que PostgreSQL está listo
docker-compose logs db | grep "ready to accept connections"

# Esperar unos segundos y reintentar
```

### Seed data falla
```bash
# Asegurarte de que la BD está corriendo
docker-compose ps db

# Ejecutar seed manualmente
docker-compose run --rm seed
```

## Siguientes pasos

1. Explorar la documentación interactiva en http://localhost:8000/docs
2. Probar diferentes filtros en `/population/sample`
3. Experimentar con agregaciones en `/aggregate/query`
4. Crear tus propias API keys con `scripts/create_api_keys.py`
5. Revisar el README.md para más detalles

## Soporte

Para problemas o preguntas:
- Revisa el README.md completo
- Consulta la documentación OpenAPI en /docs
- Revisa los logs con `docker-compose logs`
