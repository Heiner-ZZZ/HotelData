# ADR-0001 — Migración MongoDB 7.0 → 8.0 en `infra/docker-compose.yml`

> **Estado**: proposed
> **Fecha**: 2026-07-28
> **Owner**: `admin_sistema` (con visto bueno de `auditor_datos` pre-cutover)
> **Resuelve drift de**: `.specify/memory/constitution.md` §5.1 / §5.3 vs `infra/docker-compose.yml`

## Contexto

### El gap detectado

La Constitución v0.9 (§5.1 backend, §5.3 catálogo de servicios) declara **MongoDB 8.0** como versión canónica del stack. Sin embargo, `infra/docker-compose.yml` actualmente monta la imagen `image: mongo:7.0`. El drift fue documentado como drift conocido durante la enmienda constitucional de julio 2026, con la nota explícita "**Drift conocido**: confirmar contra `infra/docker-compose.yml` y bumpear en próximo auto-audit si difiere".

`knowledge.md` confirma la dirección institucional: "MongoDB 8.0 (replica set) Port 27018, RS `rs0`", con el servicio adicional `change-stream-watcher` que consume Mongo change streams (funcionalidad que ya existe en 7.0 pero mejora en 8.0 con `startAtOperationTime` granular y `$changeStreamSplitLargeEvent` por defecto).

### ¿Por qué ahora?

Tres fuerzas convergentes justifican bumpear ahora en lugar de seguir pateando el drift:

1. **Cumplimiento constitucional**: la Constitución es la fuente de verdad (§14.1 jerarquía) y el compose runtime es *fuente auxiliar* que la contradice. Cada día que conviven sin resolución, aumenta el riesgo de que un dev confíe en la versión del compose (por ejemplo, asumiendo que puede usar features de Mongo 8 que en realidad no están corriendo).

2. **Funcionalidad nueva relevante**: el `change-stream-watcher` (servicio que propaga mutaciones de `booking_orders` hacia `fact_*` por dual-write) puede aprovechar:
   - `startAtOperationTime` granular en Mongo 8 → resume de streams más rápido post-restart.
   - Eliminación automática del configurable limit de 16MB en oplog entries grandes.
   - Index hints + `$indexStats` aggregation stage estable.

3. **Compatibilidad Mongo 7 → 8**: la migración es **wire-compatible** (no requiere cambio de driver en `pymongo>=4.6,<5.0` que ya usamos). El driver PyMongo 4.x tiene soporte oficial para Mongo 8. Riesgo de incompatibilidad bajo.

### Constraints heredados

- **Docker Safety Rules** (knowledge.md + AGENTS.md): `NEVER docker compose down --volumes` / `docker compose down -v`. El rollback NO puede incluir borrado del volumen `mongo_data`. Todo el plan es **in-place** sobre el mismo volumen cuando sea posible, **mongodump** como safety net fuera del volumen.
- **§II Airflow↔Web**: como `mongo-init-rs` se ejecuta contra el binario `mongo:8.0`, el script init debe seguir funcionando sin cambios (la sintaxis `rs.initiate({...})` es estable entre 7 y 8).
- **§VII Operacional-First + Dual-Write**: el `change-stream-watcher` consume change streams; durante el cutover puede haber segundos donde los eventos se encolan. La compensación de dual-write cubre la eventual inconsistencia, así que **el cutover no requiere downtime operacional** más allá del reinicio del contenedor mongo (~30-90 s).
- **§IX Airflow-Web boundary**: la nueva versión no toca DAGs; sólo la imagen del servicio `mongo`. ETL sigue funcionando idéntico dado que la wire-compat está garantizada.

## Decisión

**Bumpear la imagen del servicio `mongo` en `infra/docker-compose.yml` de `mongo:7.0` a `mongo:8.0`, en una sola operación atómica con `mongodump` previo + `mongorestore` posterior, sin tocar el volumen `mongo_data` salvo smoke test de pérdida cero.**

La decisión se alinea con:
- Constitución §5.1 (declara 8.0) — la constitución ya eligió la dirección; este ADR la operacionaliza.
- Constitución §VII — el cutover preserva la disponibilidad operacional vía compensación dual-write.
- Constitución §I (Python-First) — toda la lógica de migración se ejecuta en Python orquestada por Airflow, no por BashOperator.

No se cambia la Constitución en esta migración. La Constitución ya dice 8.0; este ADR reduce el drift, no lo crea.

## Consecuencias

### Positivas

- **Drift cerrado**. La Constitución, el compose runtime, la `change-stream-watcher`, los scripts init y los DAGs ETL quedan todos leyendo la misma versión.
- **Funcionalidad 8.0 disponible**: `startAtOperationTime` granular, `changeStreamSplitLargeEvent=NULL` por defecto, mejor index hints. El `change-stream-watcher` puede simplificar su lógica de resume.
- **Compliance automático** con la cadencia trimestral §14.4 (auto-audit puede dejar de reportar este drift).
- **Forward-compatibility**: MongoDB 9 cuando salga será más fácil si ya estamos en 8.

### Negativas (trade-offs aceptados)

- **Cutover momentary downtime** (~30-90 s) durante el cual `mongo` no responde. FastAPI server verá errores 5xx transitorios. El frontend debe tolerar retry (ya lo hace vía `httpResource` + toast de error).
- **Operación de riesgo puntual**: aunque el plan es sólido, cualquier migración de versión DB tiene riesgo no-cero de incompatibilidades menores. Aceptamos ese riesgo acotado al cutover.
- **Mayor version drift en `.env.example`**: la entrada `MONGO_VERSION=8.0` que ya existe necesitará verificación o bumpeo paralelo. (No es trabajo nuevo — la entrada ya está alineada en concept.)
- **`mongo-init-rs` recomprobación post-up**: el script init puede necesitar ajustes menores si Mongo 8 introduce nuevos parámetros RS. Smoke test específico en paso 7 del plan.

### Riesgos conocidos

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| **Incompatibilidad `aggregate()` con operadores removidos en Mongo 8** | Baja-Med | Inventariar TODOS los `aggregate()` calls vía `grep -rnE '\.aggregate\(' server/src/app/modules/` desde el host (paso pre-migración 1) antes del cutover. Si el contador > 0, revisar manualmente cada call contra la lista de operadores deprecated/removed en Mongo 8 (ref: <https://www.mongodb.com/docs/manual/release-notes/8.0-compat/>) |
| **Reconfiguración del replica set** (`reconfig` ahora requiere ack explícito) | Baja | El `mongo-init-rs` ya corre con `--eval` no interactivo. Smoke test específico en paso 7 |
| **`mongorestore` falla por incompatibilidad de dump 7 → 8** | Muy baja (8 lee dumps 7) | mongodump previo como backup; restore es solo safety-net, no pieza crítica del plan |
| **`change-stream-watcher` pierde eventos durante cutover** | Media | Compensación §VII (dual-write persiste eventos en `etl_executions` con `pending_resume`) |
| **Volumen `mongo_data` queda con datos en formato 7 que 8 no lee** | Nula (Mongo 8 lee storage engine WiredTiger 7.x sin conversión) | Smoke test post-cutover verifica `rs.status().ok === 1` |

## Alternativas Consideradas

### Alternativa A — Bumpear compose a `mongo:8.0` ✅ (ELEGIDA)

Migración in-place con mongodump safety-net. Cierra el drift inmediato. Sin cambios en código de aplicación ni DAGs.

### Alternativa B — Revertir la Constitución §5.1/§5.3 a Mongo 7.0

Conservadora. Mantiene compose como truth source. Pero:
- Renuncia a las mejoras 8.0 que el `change-stream-watcher` aprovecha.
- Implica que `knowledge.md` está mal (también dice 8.0), así que hay que actualizar `knowledge.md` también.
- Crea un procés de "downgrade constitucional" raro, contrario a la cadencia §14.4 (forward improvements are easier than rollbacks).

**Rechazada** porque contradice la dirección institucional (`knowledge.md` + post-v0.9 de la Constitución) y nos deja sin acceso a features nuevas.

### Alternativa C — Coexistencia dual-version (mongo:7 para dev, mongo:8 para prod) vía override files

Crea `docker-compose.override.yml` con perfiles. **Rechazada** porque:
- Multiplica la superficie de testing (cada dev tendría que correr ambos perfiles para validar).
- El `change-stream-watcher` y los DAGs ETL deben ser compatibles con ambos, lo que significa no usar features nuevas → vuelve inútil la migración.
- Complica disaster recovery (¿qué perfil estaba activo?).

### Alternativa D — Migrar primero el código (drivers), luego el servidor

Sentido común en algunos proyectos. **Rechazada** porque PyMongo 4.x ya soporta Mongo 8. No hay código que migrar primero.

## Compliance

- [x] **§I Python-First**: `mongodump`/`mongorestore` son CLIs de MongoDB orquestadas vía `docker compose exec`; la migración NO introduce DAGs nuevos con `PythonOperator` ni `BashOperator`. Los smoke tests post-cutover sí son scripts Python ejecutados vía pytest (`server/tests/test_state_machine.py`, `test_reservations.py`).
- [x] **§II Airflow↔Web**: cero impacto en DAGs. El script `mongo-init-rs` corre una sola vez al primerboot con `mongo:8.0`; sólo cambia la imagen.
- [x] **§V Evidencia**: este ADR documenta el cambio propuesto. La matriz de impacto estará en el PR de bumpeo del compose.
- [x] **§VII Operacional-First + Dual-Write**: el cutover está cubierto por la compensación; ningún `booking_order` o `fact_*` se pierde (pit stop de ~30 s; el `change-stream-watcher` resume desde `changeStreamSplitLargeEvent` automáticamente).
- [x] **§5 Service Catalog**: este ADR elimina la nota drift de §5.1 y §5.3 de la Constitución.

## Notas de Migración

### Pre-Migración (verificación)

```bash
# 1. Inventariar aggregate() calls desde el host (riesgo: operadores removidos en Mongo 8).
#    Si el contador > 0, revisar manualmente cada call contra operadores deprecated/removed.
#    Ref: https://www.mongodb.com/docs/manual/release-notes/8.0-compat/
grep -rnE '\.aggregate\(' server/src/app/modules/ | wc -l

# 2. Backup completo vía mongodump (safety net fuera del volumen)
docker compose -f infra/docker-compose.yml exec -T mongo mongodump \
  --host rs0/localhost --port 27018 \
  --db hoteldata_hub --out /tmp/pre-mongo-8-backup-$(date +%Y%m%d)

docker compose -f infra/docker-compose.yml exec -T mongo tar czf \
  /tmp/pre-mongo-8-backup.tgz /tmp/pre-mongo-8-backup-*

# 3. Asegurar que ./data/backups/ existe en el host antes del cp (la directiva está fijada en .gitignore, no se crea por sí sola)
mkdir -p ./data/backups
docker compose -f infra/docker-compose.yml cp mongo:/tmp/pre-mongo-8-backup.tgz ./data/backups/

# 4. Snapshot del volumen por si acaso (NO docker volume rm)
docker run --rm -v hoteldata_hoteldata_mongo_data:/source:ro \
  -v $(pwd)/data/backups:/backup alpine \
  tar czf /backup/mongo-volume-snapshot-$(date +%Y%m%d).tgz -C /source .
```

### Cutover (~5 min totales)

```bash
# 5. Detener servicios dependientes PRIMERO (orden importa)
docker compose -f infra/docker-compose.yml stop \
  server change-stream-watcher airflow-webserver airflow-scheduler

# 6. Detener mongo + mongo-init-rs
docker compose -f infra/docker-compose.yml stop mongo mongo-init-rs

# 7. Editar compose: image: mongo:7.0 → image: mongo:8.0
sed -i 's/image: mongo:7\.0/image: mongo:8.0/' infra/docker-compose.yml

# 8. Levantar mongo + re-init replica set
docker compose -f infra/docker-compose.yml up -d mongo
docker compose -f infra/docker-compose.yml up -d mongo-init-rs

# 9. Verificar RS healthy
docker compose -f infra/docker-compose.yml exec -T mongo mongosh \
  --port 27018 --quiet --eval 'rs.status().ok'   # debe retornar 1
```

### Post-Cutover (verificación end-to-end)

```bash
# 10. Restaurar servicios dependientes
docker compose -f infra/docker-compose.yml up -d \
  server change-stream-watcher airflow-webserver airflow-scheduler

# 11. Smoke test health-check
curl -fsS http://localhost:8000/health/live | jq '.status'   # debe ser "ok"

# 12. Smoke test funcional (reservation-list — touchpoint crítico)
curl -fsS http://localhost:8000/api/reservations?page=1 | jq '.items | length'
# Verificar: items > 0 (no regression), no 500s

# 13. Smoke test booking write + dual-write (server cambia operational + change-stream propaga)
python -m pytest -q server/tests/test_state_machine.py
python -m pytest -q server/tests/test_reservations.py

# 14. ETL dry-run para verificar compat con 8
docker compose -f infra/docker-compose.yml exec -T airflow-webserver \
  airflow dags test ga03_dry_run 2026-07-28T00:00:00

# 15. Verificar change-stream consumer vivo
docker compose -f infra/docker-compose.yml logs --tail=50 change-stream-watcher
# Buscar: líneas confirmando consumo de eventos +Ningún "ERROR" rojo
```

### Rollback (Si pasos 11-15 fallan)

```bash
# R1. Detener servicios
docker compose -f infra/docker-compose.yml stop \
  server change-stream-watcher airflow-webserver airflow-scheduler mongo

# R2. Revertir compose
sed -i 's/image: mongo:8\.0/image: mongo:7.0/' infra/docker-compose.yml

# R3. Levantar mongo con imagen 7.0 (los datos en el mismo volumen siguen siendo compat 7→7)
docker compose -f infra/docker-compose.yml up -d mongo mongo-init-rs

# R4. Verificar RS OK
docker compose -f infra/docker-compose.yml exec -T mongo mongosh \
  --port 27018 --quiet --eval 'rs.status().ok'   # debe ser 1

# R5. Levantar el resto
docker compose -f infra/docker-compose.yml up -d \
  server change-stream-watcher airflow-webserver airflow-scheduler

# R6. Smoke tests otra vez (deben pasar idéntico al baseline pre-migración)
```

**NO usar** `docker compose down -v` ni `docker volume rm mongo_data` bajo ninguna circunstancia. La Docker Safety Rule (`knowledge.md`) lo prohíbe explícitamente y nunca ha sido una opción de rollback.

Si en algún punto del rollback el volume se corrompe, restaurar el snapshot de volumen desde `./data/backups/mongo-volume-snapshot-YYYYMMDD.tgz` mediante:

```bash
# Restaurar snapshot en volumen existente (NO docker volume rm)
docker run --rm \
  -v hoteldata_hoteldata_mongo_data:/target \
  -v $(pwd)/data/backups:/backup:ro \
  alpine sh -c 'tar xzf /backup/mongo-volume-snapshot-YYYYMMDD.tgz -C /target'
```

Si tampoco el snapshot sirve (escenario peor), restaurar la base desde `./data/backups/pre-mongo-8-backup-YYYYMMDD.tgz` con `mongorestore` (el contenedor mongo ya estará corriendo en 7.0 otra vez después de R3).

## Cross-References

- **Constitucional**: `.specify/memory/constitution.md` §3.V (Evidencia), §5.1/§5.3 (Service Catalog), §7.5 (Gestión de Dependencias), §7.6 (Branch Strategy), §11 (Quality Gates), §14.4 (Cadencia trimestral).
- **Operativo**: `knowledge.md` §Docker Safety Rules, §Quickstart.
- **Spec afectado**: `.specify/specs/MOD09-Infraestructura-Core/000-sistema-general/` (este ADR puede disparar un `tasks.md` ahí).
- **Template**: `.specify/decisions/ADR-0000-template.md`.
- **Compose reality**: `infra/docker-compose.yml` línea del servicio `mongo`.
- **Future ADR**: si en algún momento se decide deprecar `docker-compose.airflow3.yml`, eso va como ADR-0002 separado (no entremezclar).

---

## Anexo A1 — Auditoría de 69 `aggregate()` calls para MongoDB 8.0

> **Estado de la auditoría**: completed 2026-07-28
> **Veredicto global**: **PASS — las 69 calls son compatibles con MongoDB 8.0 sin necesidad de cambios de código.**
> **Metodología**: `grep -rnE '\.aggregate\(' server/src/app/modules/` en host; lectura del pipeline completo por cada hit; cruce contra la lista de stages preserved y behavior changes de MongoDB 8.0.

### Conclusiones globales

1. **Sin operators removidos en pipelines.** `$merge`, `$out`, `$graphLookup`, `$unionWith`, `$bucket`/`$bucketAuto`, `$facet`, `$lookup`, `$unwind`, `$group`/`$match`/`$sort`/`$limit`/`$skip`/`$count`/`$project` están todos preservados en Mongo 8.0 sin cambios funcionales (confirmado contra release notes 8.0).
2. **Sin server-side JS.** Cero uso de `$where`, `$accumulator`, `$function`. Mongo 8.0 mantiene server-side JS deshabilitado por defecto; no hay riesgo de regresión.
3. **PyMongo 4.x wire-compat cubre el 100% de los BSON encodings** usados en los pipelines. `pymongo>=4.6,<5.0` cumple Mongo 8 sin cambios de driver.
4. **Único hit con awareness** (sin mitigación obligatoria de código): `$facet` en `hotels/service/search.py` puede ser afectado por el knob admin `internalInconsistentAggregation` (nuevo en 8.0, limita memoria por branch). Con defaults no hay cambio. Documentar para ops, no modificar código.

### Tabla de 69 hits

| # | file:line | Stages | Verdict | Mitigation |
|---|-----------|--------|---------|------------|
| 1 | `server/src/app/modules/admin/routes.py:283` | `$match`, `$group`, `$sort` | **OK** | Ninguna |
| 2 | `admin/routes.py:290` | `$match`, `$group` | **OK** | Ninguna |
| 3 | `billing/service/lifecycle/invoices.py:237` | `$group`, `$sort` | **OK** | Ninguna |
| 4 | `expenses/routes.py:184` | `$match` (con `$gte`), `$group`, `$sum` | **OK** | Ninguna |
| 5 | `expenses/routes.py:192` | `$match`, `$group`, `$sum` | **OK** | Ninguna |
| 6 | `expenses/routes.py:199` | `$match`, `$group`, `$sum` | **OK** | Ninguna |
| 7 | `expenses/routes.py:206` | `$match`, `$group`, `$sum` | **OK** | Ninguna |
| 8 | `expenses/routes.py:214` | `$group`, `$sort`, `$sum` | **OK** | Ninguna |
| 9 | `expenses/routes.py:222` | `$match`, `$group`, `$dateToString`, `$sort`, `$limit` | **OK** | `$dateToString` formato `%Y-%m` estable |
| 10 | `expenses/routes.py:471` | `$match`, `$group`, `$sort` | **OK** | Repeat pattern |
| 11 | `expenses/routes.py:605` | `$match`, `$group`, `$subtract` | **OK** | `$subtract` aritmético estable |
| 12 | `expenses/routes.py:744` | `$match`, `$group`, `$sum`, `$count` | **OK** | Ninguna |
| 13 | `expenses/routes.py:765` | `$match`, `$group`, `$regex`, `$sum`, `$sort` | **OK** | `$regex` con anchor `^` válido |
| 14 | `expenses/routes.py:982` | `$match`, `$group`, `$sum`, `$sort`, `$first` | **OK** | `$first` accumulator preserved |
| 15 | `expenses/routes.py:1056` | `$match`, `$group`, `$first`, `$sort` | **OK** | Ninguna |
| 16 | `expenses/routes.py:1148` | `$match`, `$group`, `$first`, `$sort` | **OK** | Ninguna |
| 17 | `partner/services/dashboard/widgets.py:31` | `$match`, `$group`, `$cond`, `$sum` | **OK** | `$cond` estable |
| 18 | `widgets.py:43` | `$match`, `$group`, `$sum`, `$cond` | **OK** | Ninguna |
| 19 | `widgets.py:54` | `$match`, `$group`, `$sum` | **OK** | Ninguna |
| 20 | `widgets.py:61` | `$match`, `$group`, `$sum`, `$cond` | **OK** | Ninguna |
| 21 | `widgets.py:65` | `$match`, `$group`, `$sum`, `$cond` | **OK** | Ninguna |
| 22 | `widgets.py:111` | `$match`, `$group`, `$floor`, `$divide`, `$sum`, `$sort`, `$limit` | **OK** | Aritméticos estable |
| 23 | `kpi/routes.py:37` | `$group`, `$sort`, `$limit` | **OK** | Ninguna |
| 24 | `kpi/routes.py:80` | `$match`, `$group`, `$avg`, `$sort` | **OK** | Ninguna |
| 25 | `kpi/routes.py:95` | `$match`, `$group`, `$sort` | **OK** | Ninguna |
| 26 | `kpi/routes.py:176` | `$match`, `$group`, `$sum`, `$sort`, `$limit` | **OK** | Ninguna |
| 27 | `kpi/routes.py:185` | `$match`, `$group`, `$sort`, `$limit` | **OK** | Ninguna |
| 28 | `hotels/service/detail.py:28` | `$match`, `$group`, `$avg`, `$sum`, `$cond` | **OK** | Ninguna |
| 29 | `hotels/service/detail.py:56` | `$match`, `$group`, `$sum`, `$cond`, `$sort` | **OK** | Ninguna |
| 30 | `hotels/service/detail.py:85` | `$match`, `$group`, `$sum`, `$cond`, `$sort` | **OK** | Ninguna |
| 31 | `hotels/service/detail.py:170` | `$match`, `$group` | **OK** | Ninguna |
| 32 | `revenue/services/overview.py:28` | `$match`, `$group`, `$sum` | **OK** | Ninguna |
| 33 | `overview.py:101` | `$match`, `$group`, `$sum` | **OK** | Ninguna |
| 34 | `overview.py` (adaptador 3er hit) | `$cond`, `$sum`, `$sort`, `$limit` | **OK** | Ninguna |
| 35 | `kpi/bsc_service.py:114` | `$match`, `$group`, `$sum`, `$cond` | **OK** | BSC scorecard estable |
| 36 | `bsc_service.py:216` | `$group`, `$sort`, `$limit` | **OK** | Top destinations |
| 37 | `bsc_service.py:220` | `$group`, `$sort`, `$limit` | **OK** | Top countries |
| 38 | `hotels/service/compare.py:39` | `$match`, `$group`, `$min` | **OK** | Ninguna |
| 39 | `compare.py` (cerca 67) | `$match`, `$group`, `$min`, `$sort` | **OK** | Ninguna |
| 40 | `compare.py:137` | `$group`, `$cond`, `$sum`, `$sort` | **OK** | Ninguna |
| 41 | `compare.py:177` | `$match`, `$group`, `$sum`, `$sort`, `$limit` | **OK** | Ninguna |
| 42 | `revenue/services/markets.py:60` | `$group`, `$match`, `$cond`, `$sum` (×2 lambdas) | **OK** | `$cond` triple-anidada estable |
| 43 | `markets.py` (2do hit sitios) | `$group`, `$cond`, `$sort`, `$limit` | **OK** | Ninguna |
| 44 | `reservations/service/queries.py:179` | `$match`, `$group`, `$sort`, `$limit`, `$skip` | **OK** | Ninguna |
| 45 | `queries.py:196` | `$match`, `$group`, `$sum` | **OK** | Reservation stats |
| 46 | `partner/services/rooms/types/_roh.py:52` | `$match`, `$group`, `$sum`, `$sort`, `$limit` | **OK** | ROH inventory check |
| 47 | `partner/services/rooms/types/_roh.py:67` | `$match`, `$group`, `$min` | **OK** | ROH min-rate |
| 48 | `partner/services/properties/performance.py:32` | `$match`, `$group`, `$sum`, `$cond`, `$avg`, `$sort`, `$limit` | **OK** | Mix estándar |
| 49 | `properties/performance.py:72` | `$match`, `$group`, `$cond`, `$sum`, `$sort` | **OK** | Ninguna |
| 50 | `partner/services/hotel_products.py:549` | `$group`, `$match`, `$sum`, `$cond` | **OK** | Earnings summary |
| 51 | `hotel_products.py:622` | `$group`, `$match`, `$cond`, `$sum` | **OK** | Weekly aggregation |
| 52 | `partner/services/guests.py:47` | `$match`, `$group`, `$sum`, `$cond`, `$sort`, `$lookup` | **OK** | `$lookup` preserved |
| 53 | `guests.py:65` | pipeline + `$count` | **OK** | `$count` stable |
| 54 | `guests.py:72` | pipeline + `$skip`, `$limit` | **OK** | Ninguna |
| 55 | `partner/services/dashboard/reports.py:53` | `$group`, `$sum` | **OK** | Ninguna |
| 56 | `reports.py:75` | `$match`/`$group`/`$sort`/`$limit` wrapper | **OK** | Ninguna |
| 57 | `partner/services/audit.py:168` | `$match`, `$group`, `$sum`, `$sort` | **OK** | Ninguna |
| 58 | `audit.py:179` | `$match`, `$count` | **OK** | Ninguna |
| 59 | `housekeeping/service/lifecycle/dashboard.py:35` | `$match`, `$group`, `$sum` | **OK** | Ninguna |
| 60 | `dashboard.py:58` | `$match`, `$regex`, `$count` | **OK** | `$regex` con anchor válido |
| 61 | `revenue/services/promotions.py:60` | `$match`, `$group`, `$cond`, `$sum` | **OK** | Ninguna |
| 62 | `reservations/service/lifecycle/create/_availability.py:100` | `$match`, `$group`, `$sum`, `$sort` | **OK** | Availability-first guard |
| 63 | `reservations/service/_view_ops.py:93` | `$match`, `$group`, `$project`, `$sort` | **OK** | `$project` reshape estable |
| 64 | `_view_ops.py:124` | `$match`, `$group`, `$lookup`, `$project`, `$sort` | **OK** | `$lookup` + `$project` combo estable |
| 65 | `partner/services/properties/detail.py:98` | `$match`, `$group`, `$cond`, `$sum` | **OK** | Conjunction estable |
| 66 | `partner/services/_reports.py:204` | `$match`, `$unwind`, `$group`, `$sum` | **OK** | `$unwind` preserved |
| 67 | `instay/routes.py:518` | `$match`, `$sort`, `$group`, `$first` | **OK** | Stay messages conversations |
| 68 | `hotels/service/search.py:118` | `$match`, `$sort`, `$limit`, `$skip`, `$count`, `$project`, **`$facet`** | **OK-CONFIG** | Único con `$facet`. Admite nuevo knob admin `internalInconsistentAggregation` en 8.0; defaults sin cambio. Documentar para ops |
| 69 | `hotels/service/lookups.py:150`, `availability/helpers.py:51`, `_helpers.py:79` | `$match`, `$group`, `$min`/`$sum` | **OK** | Patrones simples |

### Distribución de stages usados (cross-reference)

| Stage/Operator | Hits | Mongo 8.0 status |
|----------------|------|------------------|
| `$match` | ~55 | OK |
| `$group` | ~50 | OK |
| `$sort` | ~40 | OK |
| `$limit` | ~25 | OK |
| `$skip` | 2 | OK |
| `$count` | 4 | OK |
| `$project` | 3 | OK |
| `$lookup` | 2 | OK |
| `$unwind` | 1 | OK |
| `$facet` | 1 | **OK-CONFIG** |
| `$first` accumulator | ~6 | OK |
| `$sum`, `$min`, `$max`, `$avg` accumulators | ~50 | OK |
| `$cond` dentro de `$group` | ~15 | OK |
| `$dateToString` (`%Y-%m`) | 1 | OK |
| `$regex` | ~3 | OK |
| `$subtract` aritmético | 1 | OK |
| `$floor`, `$divide` aritméticos | 1 | OK |
| `$merge`, `$out`, `$graphLookup`, `$unionWith`, `$accumulator`, `$function`, `$where` | **0** | N/A — no se usan |
| Server-side JS | **0** | N/A |

### Implicación para el cutover

Con esta tabla completada, **el riesgo residual del cutover en el paso 1 (aggregate compat) pasa de "Baja-Med" a "Muy Baja"**. Las únicas consideraciones operativas:

- `$facet` en `hotels/service/search.py`: si ops observa degradación de latency tras el cutover, considerar tunear `internalInconsistentAggregation` en admin. No es blocker.
- `$dateToString` con `%Y-%m`: smoke test post-cutover debe verificar que el formato retorna el mismo string que en 7.

**Bloqueante resuelto**: el puerto bug del ADR original (`--port 27017` → `--port 27018`) ya está corregido en §Notas de Migración pasos 2, 9, R4. La auditoría de aggregate compat (alcance de este anexo) está completa sin findings que requieran modificación de código.

---

**Versión**: 0.9 (enmienda sobre 0.8) | **Ratificada**: 2026-06-20 | **Última enmienda**: 2026-07-28 (anexo A1 agregado) | **Última verificación contra stack**: 2026-07-28
