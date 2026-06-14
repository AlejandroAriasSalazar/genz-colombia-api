# Criterios de aceptación

| Control | Evidencia requerida |
|---|---|
| Fuente real | URL oficial, manifiesto, snapshot, tamaño y SHA-256 |
| Esquema | 202 columnas sexo-edad y dimensiones DANE verificadas |
| Completitud | 101 edades x 2 sexos x 2 municipios x años cargados |
| Reconciliación | Sumas por sexo y total iguales al XLSX |
| Publicación | Un candidato fallido no puede publicarse |
| Trazabilidad | Cada respuesta identifica release, método y checksum |
| Reproducibilidad | Misma release, filtros y semilla producen igual muestra |
| Seguridad | HMAC de claves, scopes, cuotas y límites probados |
| Privacidad | Celdas bajo umbral suprimidas; no hay identificadores reales |
| Persistencia | Reinicio no recrea ni elimina tablas |
| Migraciones | Upgrade, downgrade y upgrade ejecutados |
| Calidad de código | Ruff limpio y cobertura mínima 85% |
| Infraestructura | PostgreSQL y Redis pasan integración |
| Recuperación | Backup restaurado y smoke test documentado |

## Evidencia de producción del 14 de junio de 2026

- Archivo DANE: `PPED-AreaSexoEdadMun-2018-2042_VP.xlsx`.
- SHA-256:
  `7e461635315664d44ba52cc7f951947085a0ea6f2dda72fe2efed11a76880516`.
- Release: `dane-7e4616353156-m1`.
- Celdas cargadas: 10.100.
- Quality gate: `passed`.
- Base de datos: Supabase PostgreSQL, esquema aislado `api_v2`.
- Pruebas automatizadas: 23.
- Cobertura: 90,31%.
- Dominio: `https://api.databolico.com`.
- Liveness, PostgreSQL, Redis y release publicada: `ready`.
- Autenticación sin clave: `401`.
- Ciudades verificadas: Bogotá (`11001`) y Medellín (`05001`).
- Muestra autenticada: reproducible, filtrada y con cuotas.
- Agregación autenticada: 200 con grupos por sexo y población oficial.
- Persistencia: reinicio de Coolify conservó una sola release publicada con
  10.100 celdas, sin duplicados.

La restauración periódica de backups sigue siendo un control operativo externo:
debe programarse y probarse desde la política de backups del VPS/Supabase.
