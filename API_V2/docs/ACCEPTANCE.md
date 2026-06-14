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

## Evidencia local del 13 de junio de 2026

- Archivo DANE: `PPED-AreaSexoEdadMun-2018-2042_VP.xlsx`.
- SHA-256:
  `7e461635315664d44ba52cc7f951947085a0ea6f2dda72fe2efed11a76880516`.
- Release: `dane-7e4616353156-m1`.
- Celdas cargadas: 10.100.
- Quality gate: `passed`.
- Pruebas automatizadas: 22.
- Cobertura: 90,31%.

La certificación final de producción requiere todavía ejecutar en el VPS la
integración PostgreSQL/Redis, restaurar un backup y completar el smoke test del
dominio público.
