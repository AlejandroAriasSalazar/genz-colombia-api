# Operación en VPS / Coolify

## Servicios

- `api`: FastAPI; no ejecuta migraciones durante el arranque.
- `bootstrap`: crea el esquema, ejecuta Alembic, ingiere DANE, publica la
  release aprobada y crea el cliente inicial de forma idempotente.
- `worker`: comprueba semanalmente la fuente y crea candidatos; nunca publica
  automáticamente.
- `supabase-db`: PostgreSQL 15 de Supabase, en la red privada del servicio.
- `redis`: Redis 7 con AOF.
- `raw_data`: snapshots originales DANE.

El despliegue de producción usa `docker-compose.coolify.yml`. La aplicación se
une explícitamente a la red externa de Supabase y a la red `coolify`; PostgreSQL
no expone un puerto público. V2 usa el esquema PostgreSQL `api_v2`, separado de
las tablas existentes de V1.

## Variables obligatorias

```text
ENVIRONMENT=production
POSTGRES_HOST=supabase-db-<service-uuid>
POSTGRES_PORT=5432
POSTGRES_USER=supabase_admin
POSTGRES_PASSWORD_B64=<SERVICE_PASSWORD_POSTGRES en base64url sin padding>
POSTGRES_DB=genz_api
POSTGRES_SCHEMA=api_v2
REDIS_URL=redis://...
API_KEY_PEPPER=<secreto aleatorio de 32+ bytes>
SYNTHETIC_ID_SECRET=<secreto independiente de 32+ bytes>
BOOTSTRAP_API_KEY=<clave gzv2 de alta entropía>
CORS_ORIGINS=["https://explorer.databolico.com"]
RAW_STORAGE_PATH=/data/raw
```

No guardar `DATABASE_URL` ni la contraseña PostgreSQL sin codificar en Coolify:
su parser puede expandir caracteres especiales. El entrypoint decodifica
`POSTGRES_PASSWORD_B64` dentro del contenedor y construye la URL codificada.

No reutilizar contraseñas, tokens ni API keys de V1. Los secretos expuestos en
la documentación madre deben revocarse fuera de este repositorio.

## Primer despliegue

1. Confirmar que Supabase está healthy y obtener su red Docker privada.
2. Configurar secretos en Coolify.
3. Desplegar `docker-compose.coolify.yml`.
4. Confirmar `/api/v2/health/live`.
5. Consultar el bootstrap con `X-Operations-Key` en
   `/api/v2/health/bootstrap`.
6. Confirmar que `/api/v2/health/ready` retorna `ready`.
7. Revisar `/api/v2/quality/{version}`.
8. Ejecutar los smoke tests autenticados.
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

El endpoint `/api/v2/health/bootstrap` no aparece en OpenAPI y responde `404`
sin una cabecera `X-Operations-Key` válida.
