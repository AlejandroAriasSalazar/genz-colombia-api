# Operación en VPS / Coolify

## Servicios

- `api`: FastAPI. Ejecuta `alembic upgrade head` antes de Uvicorn.
- `worker`: comprueba semanalmente la fuente y crea candidatos; nunca publica.
- `postgres`: PostgreSQL 16 con volumen persistente.
- `redis`: Redis 7 con AOF.
- `raw_data`: snapshots originales DANE.

En Coolify pueden reutilizarse PostgreSQL y Redis administrados externamente.
En ese caso, desplegar `api` y `worker` como aplicaciones separadas con la misma
imagen, red privada, volumen de snapshots y variables.

## Variables obligatorias

```text
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://...
API_KEY_PEPPER=<secreto aleatorio de 32+ bytes>
SYNTHETIC_ID_SECRET=<secreto independiente de 32+ bytes>
CORS_ORIGINS=["https://explorer.databolico.com"]
RAW_STORAGE_PATH=/data/raw
```

No reutilizar contraseñas, tokens ni API keys de V1. Los secretos expuestos en
la documentación madre deben revocarse fuera de este repositorio.

## Primer despliegue

1. Crear PostgreSQL, Redis y volumen de snapshots.
2. Configurar secretos en Coolify.
3. Desplegar `api`; confirmar `/api/v2/health/live`.
4. Ejecutar `python -m scripts.manage ingest`.
5. Revisar `/api/v2/quality/{version}`.
6. Publicar con `python -m scripts.manage publish VERSION`.
7. Crear una clave con `python -m scripts.manage create-key --name frontend`.
8. Confirmar `/api/v2/health/ready` y smoke tests.
9. Cambiar el proxy/frontend a `/api/v2`.

## Rollback

- Código: redeploy de la imagen anterior.
- Dataset: publicar una release anterior aprobada. La operación marca la release
  vigente como `superseded`.
- Esquema: usar `alembic downgrade REVISION` solo después de restaurar y probar
  una copia del backup.

## Backup y restauración

Programar `scripts/backup.sh` diariamente y enviar el archivo fuera del VPS.
Ejecutar una restauración de prueba mensual:

```bash
DATABASE_URL=... scripts/restore.sh /backups/genz_v2_TIMESTAMP.dump
```

La prueba no se considera exitosa hasta consultar una release, sus fuentes y un
agregado después de restaurar.

## Monitoreo

Alertar por:

- readiness distinto de `ready`;
- ausencia de release publicada;
- fallo del worker;
- incremento de respuestas 5xx o 429;
- latencia p95 superior a 750 ms en agregados;
- falta de backup reciente;
- fuente sin snapshot nuevo después de una actualización anunciada.
