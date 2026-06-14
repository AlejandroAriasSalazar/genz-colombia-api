# Auditoría V1 convertida en controles V2

| Hallazgo V1 | Control V2 |
|---|---|
| No había fuentes externas | Conector DANE, manifiesto, snapshot y checksum |
| Probabilidades manuales | Solo muestreo ponderado por celdas oficiales |
| Tablas eliminadas al arrancar | Alembic previo al proceso web |
| Límite por tier ignorado | Validación contra `max_sample_size` |
| Rate limiting inexistente | Redis Lua atómico por minuto y día |
| `LIMIT` presentado como aleatorio | PRNG con semilla y ponderación |
| Filtros frontend ignorados | Contrato anidado estricto, campos extra prohibidos |
| Privacidad solo declarada | Supresión de celdas y presupuesto de consulta |
| OpenAPI sin seguridad | `APIKeyHeader` aplicado mediante `Security` |
| Bcrypt escaneaba todas las claves | Prefijo indexado + HMAC-SHA256 |
| Logs destruidos o incompletos | Tabla persistente, request ID e IP hasheada |
| Secretos expuestos | Ningún secreto en V2; rotación exigida en operación |
| Tests condicionales | Assertions obligatorias sin ramas que oculten fallos |
