# Diagnóstico de Herramientas de Calidad — HotelData

> **Fecha:** 2026-07-17
> **Alcance:** Backend Python (Ruff + Mypy) · Frontend Angular/TypeScript (ESLint)
> **Herramientas instaladas:** `ruff` 0.15.22, `mypy` 2.3.0, `@angular-eslint/schematics` 22.1.0
> **Propósito:** Documentar línea base de calidad de código antes de correcciones.

---

## Tabla Resumen

| Herramienta | Total errores | Archivos afectados | Auto-fixable | Prioridad |
|---|---|---|---|---|
| **Ruff** (Python lint) | **11,103** | 457 | 174 | 🟡 Medio |
| **Mypy** (Python types) | **120** | 66 (de 373) | — | 🔴 Crítico |
| **ESLint** (Angular/TS) | **1,012** | 228 | 207 | 🟡 Medio |

---

## 1. Ruff — Backend Python

### 1.1 Totales por regla

| Regla | Cantidad | Descripción | Auto-fix |
|---|---|---|---|
| `E501` | 3,053 | `line-too-long` (>88 cols) | — |
| `D103` | 939 | `undocumented-public-function` | — |
| `ANN201` | 642 | `missing-return-type-public-function` | — |
| `FAST002` | 552 | `fast-api-non-annotated-dependency` | — |
| `B008` | 436 | `function-call-in-default-argument` | — |
| `S101` | 428 | `assert` usado en código (no tests) | — |
| `COM812` | 375 | `missing-trailing-comma` | ✅ |
| `T201` | 324 | `print` en producción | — |
| `ANN001` | 314 | `missing-type-function-argument` | — |
| `I001` | 311 | `unsorted-imports` | ✅ |
| `PLC0415` | 254 | `import-outside-top-level` | — |
| `PLR2004` | 253 | `magic-value-comparison` | — |
| `D100` | 242 | `undocumented-public-module` | — |
| `F401` | 226 | `unused-import` | ✅ |
| `TRY003` | 212 | `raise-vanilla-args` | — |
| `BLE001` | 153 | `blind-except` (`except Exception`) | — |
| `ARG001` | 147 | `unused-function-argument` | — |
| `ANN401` | 140 | `any-type` usado en firma pública | — |
| `Q000` | 129 | `bad-quotes-inline-string` | ✅ |
| `EM101` | 128 | `raw-string-in-exception` | — |
| `D101` | 119 | `undocumented-public-class` | — |
| `PLR0913` | 104 | `too-many-arguments` (>5 args) | — |
| `D102` | 94 | `undocumented-public-method` | — |
| `INP001` | 94 | `implicit-namespace-package` (falta `__init__.py`) | — |
| `EM102` | 84 | `f-string-in-exception` | — |
| `TID252` | 60 | `relative-imports` | — |
| `C901` | 54 | `complex-structure` (muy anidado) | — |
| `E402` | 51 | `module-import-not-at-top-of-file` | — |
| `AIR001` | 48 | `airflow-variable-name-task-id-mismatch` | — |
| `D104` | 48 | `undocumented-public-package` | — |
| `S110` | 44 | `try-except-pass` | — |
| `W293` | 41 | `blank-line-with-whitespace` | ✅ |
| `PERF401` | 38 | `manual-list-comprehension` | — |
| `F541` | 34 | `f-string-missing-placeholders` | ✅ |
| `PLR0915` | 34 | `too-many-statements` | — |
| `ARG002` | 30 | `unused-method-argument` | — |
| `B904` | 29 | `raise-without-from-inside-except` | — |
| `PLR0912` | 28 | `too-many-branches` | — |
| `F405` | 26 | `undefined-local-with-import-star-usage` | — |
| `RUF022` | 25 | `unsorted-dunder-all` | ✅ |
| `F821` | 23 | `undefined-name` | — |
| `DTZ007` | 23 | `call-datetime-strptime-without-zone` | — |
| `E701` | 23 | `multiple-statements-on-one-line-colon` | — |
| `SLF001` | 23 | `private-member-access` | — |
| `PTH123` | 20 | `builtin-open` (usar `Path` en vez de `open`) | — |
| `SIM115` | 20 | `open-file-with-context-handler` | — |
| `TRIES` | 19 | varias reglas TRY | — |
| `RET504` | 18 | `unnecessary-assign` | — |
| `TC002` | 18 | `typing-only-third-party-import` | — |
| `FURB110` | 17 | `if-exp-instead-of-or-operator` | ✅ |
| Otras | ~120 | (S310, FBT, DTZ, RUF, etc.) | varias |

### 1.2 Archivos con más errores (top 15)

| Archivo | Errores |
|---|---|
| `tests/test_state_machine.py` | 395 |
| `tests/test_reservations.py` | 301 |
| `src/app/modules/housekeeping/routes.py` | 238 |
| `src/app/modules/instay/routes.py` | 208 |
| `src/app/modules/billing/routes.py` | 194 |
| `src/app/modules/expenses/routes.py` | 193 |
| `src/app/modules/admin/routes.py` | 171 |
| `src/app/modules/reservations/routes/reservations.py` | 171 |
| `scripts/validate_ga03_full_integrations.py` | 152 |
| `tests/test_billing.py` | 149 |
| `scripts/validate_manual_hotel_profile_enrichment.py` | 128 |
| `src/app/modules/geo_catalog/routes.py` | 123 |
| `src/app/modules/hr/routes.py` | 121 |
| `tests/test_settings.py` | 115 |
| `src/app/modules/reservations/routes/management.py` | 111 |

### 1.3 Auto-fix aplicable

**174 errores** tienen auto-fix con `ruff check --fix`:
- `COM812` — 375 trailing commas (pero no contados como fix porque son muchos más de 174, hay que ver)
- `I001` — unsorted imports
- `F401` — unused imports (226 ocasiones)
- `Q000` — bad quotes (129)
- `F541` — f-string sin placeholders (34)
- `W293` — blank line whitespace (41)
- `RUF022` — unsorted dunder-all (25)
- `FURB110` — if-exp en vez de or-operator (17)

---

## 2. Mypy — Backend Python (Tipado estático)

### 2.1 Totales por categoría

| Código de error | Cantidad | Descripción |
|---|---|---|
| `[union-attr]` | 20 | Acceder a `.isoformat()`, `.get()` sobre `dict \| None` sin verificar null |
| `[name-defined]` | 20 | Llamadas a funciones/variables que no existen |
| `[import-untyped]` | 17 | Librerías sin stubs de tipos (pandas, passlib, openpyxl) |
| `[assignment]` | 8 | Asignación de tipo incompatible |
| `[attr-defined]` | 7 | Atributo inexistente en objeto |
| `[index]` | 7 | Indexar `dict \| None` sin verificar |
| `[dict-item]` | 5 | Valor de diccionario con tipo incorrecto |
| `[list-item]` | 5 | Item de lista con tipo incorrecto |
| `[operator]` | 4 | Operación aritmética con `None` |
| `[arg-type]` | 2 | Argumento con tipo incompatible |
| `[var-annotated]` | 2 | Variable sin type hint |
| `[misc]` | 2 | Varios misceláneos |
| `[import-not-found]` | 2 | Módulo no encontrado (weasyprint, backports.zoneinfo) |
| `[type-var]` | 1 | Type variable incompatibe |

### 2.2 Funciones y variables **undefined** (runtime crash seguro)

| Archivo | Línea | Símbolo faltante |
|---|---|---|
| `src/app/modules/admin/routes.py` | 236 | `Any` (no importado de typing) |
| `src/app/modules/admin/routes.py` | 272 | `Any` (no importado de typing) |
| `src/app/modules/admin/routes.py` | 280 | `Any` (no importado de typing) |
| `src/app/modules/reviews/routes.py` | 155 | `update_review` (no existe) |
| `src/app/modules/reviews/routes.py` | 185 | `create_review_report` (no existe) |
| `src/app/modules/reviews/routes.py` | 215 | `list_review_reports` (no existe) |
| `src/app/modules/reviews/service/collections.py` | 34 | `ModuleStatus` (no importado) |
| `src/app/modules/lost_and_found/service/collections.py` | 22 | `ModuleStatus` (no importado) |
| `src/app/modules/hr/service/collections.py` | 42 | `ModuleStatus` (no importado) |
| `src/app/modules/housekeeping/service/collections.py` | 58 | `ModuleStatus` (no importado) |
| `src/app/modules/expenses/service/collections.py` | 53 | `ModuleStatus` (no importado) |
| `src/app/modules/billing/service/collections.py` | 40 | `ModuleStatus` (no importado) |
| `src/app/modules/partner/services/rates/plans.py` | 185 | `clean_name` (no existe) |
| `src/app/modules/partner/services/rates/plans.py` | 187 | `clean_name` (no existe) |
| `src/app/modules/settings/routes.py` | 163 | `settings` (no importado) |
| `src/app/modules/account/routes.py` | 180 | `settings` (no importado) |
| `src/etl/ga03_airflow/load.py` | 21 | `Path` (no importado) |
| `src/etl/ga03_airflow/load.py` | 55 | `Path` (no importado) |
| `src/app/modules/partner/routes/rooms.py` | 218 | `UploadFile` (no importado) |
| `src/app/modules/partner/routes/rooms.py` | 230 | `uuid` (no importado) |

### 2.3 Archivos con más errores de tipos (top 10)

| Archivo | Errores |
|---|---|
| `src/app/modules/reception/routes.py` | 8 |
| `src/app/modules/admin/routes.py` | 8 |
| `src/etl/ta02_load_mongodb.py` | 6 |
| `src/app/modules/reservations/routes/management.py` | 6 |
| `src/app/modules/auth/routes/_helpers.py` | 6 |
| `src/app/modules/reviews/routes.py` | 5 |
| `src/app/modules/hotels/service/availability/search.py` | 5 |
| `src/app/modules/revenue/services/common.py` | 5 |
| `src/app/features/etl_status/services/_common.py` | 5 |
| `src/app/modules/reports/excel_service.py` | 4 |

### 2.4 Librerías sin stubs de tipos

| Librería | Archivos afectados |
|---|---|
| `pandas` | 8 archivos |
| `passlib.context` | 3 archivos |
| `openpyxl`, `openpyxl.styles`, `openpyxl.utils` | 1 archivo |
| `weasyprint` | 1 archivo |
| `backports.zoneinfo` | 1 archivo |

Solución: `pip install pandas-stubs types-passlib types-openpyxl`

---

## 3. ESLint — Frontend Angular/TypeScript

### 3.1 Totales por regla

| Regla | Cantidad | Descripción | Auto-fix |
|---|---|---|---|
| `@typescript-eslint/no-explicit-any` | 299 | Uso de `any` sin tipar | — |
| `@typescript-eslint/array-type` | 168 | Usar `Array<T>` en vez de `T[]` | ✅ |
| `@angular-eslint/template/click-events-have-key-events` | 140 | `(click)` sin evento de teclado (accesibilidad) | — |
| `@angular-eslint/template/interactive-supports-focus` | 132 | Elementos interactivos sin `tabindex`/focus | — |
| `@typescript-eslint/no-unused-vars` | 103 | Variables importadas/no usadas | — |
| `@angular-eslint/template/label-has-associated-control` | 88 | `<label>` sin `for`/control asociado | — |
| `@typescript-eslint/no-inferrable-types` | 22 | Type trivial inferible (ej: `x: number = 5`) | ✅ |
| `prefer-const` | 12 | Usar `const` en vez de `let` | ✅ |
| `@angular-eslint/template/eqeqeq` | 10 | Usar `!=` en vez de `!==` | ✅ |
| `@angular-eslint/no-output-native` | 9 | Outputs nombrados como eventos DOM (`click`, `close`) | — |
| `@typescript-eslint/no-empty-function` | 9 | Funciones vacías | — |
| `@angular-eslint/no-output-on-prefix` | 8 | Output con prefijo `on` (ej: `@Output() onClick`) | ✅ |
| `no-useless-assignment` | 3 | Asignación sin uso posterior | — |
| `@angular-eslint/component-selector` | 2 | Selector de componente no sigue convención | — |
| `@typescript-eslint/consistent-type-assertions` | 2 | Type assertion innecesario | ✅ |
| `@angular-eslint/template/no-autofocus` | 2 | `autofocus` en template | — |
| `@angular-eslint/template/valid-aria` | 1 | Valor `aria-*` inválido | — |
| `@typescript-eslint/consistent-type-definitions` | 1 | Usar `type` vs `interface` inconsistente | ✅ |

### 3.2 Archivos TS con más errores (top 15)

| Archivo | Errores |
|---|---|
| `src/app/features/system-admin/pages/monitoring-page/monitoring-page.html` | 20 |
| `src/app/features/reservations/pages/reservation-detail-page/partials/rd-product-modal.ts` | 11 |
| `src/app/features/reviews/pages/reputation-dashboard-page/reputation-dashboard-page.ts` | 11 |
| `src/app/features/shifts/pages/control-turnos-caja-page/control-turnos-caja-page.html` | 11 |
| `src/app/features/reservations/pages/reservations-list-page/reservations-list-page.columns.ts` | 10 |
| `src/app/features/billing/pages/billing-preview-page/billing-preview-page.html` | 9 |
| `src/app/features/billing/pages/billing-invoice-page/billing-invoice-page.html` | 9 |
| `src/app/features/rooms/pages/rooms-page/partials/rp-edit-modal.ts` | 9 |
| `src/app/features/housekeeping/pages/housekeeping-dashboard-page/housekeeping-dashboard-page.html` | 8 |
| `src/app/features/reservations/pages/rates-page/rates-page.ts` | 7 |
| `src/app/features/reservations/pages/reservation-detail-page/reservation-detail-page.ts` | 7 |
| `src/app/features/reservations/pages/reservations-list-page/reservations-list-page.ts` | 7 |
| `src/app/features/system-admin/pages/currencies-page/currencies-page.html` | 6 |
| `src/app/features/reservations/pages/reservation-new-page/reservation-new-page.ts` | 6 |
| `src/app/features/housekeeping/pages/housekeeping-dashboard-page/housekeeping-dashboard-page.ts` | 6 |

---

## 4. Priorización de Correcciones

### 🔴 Prioridad 1 — Mypy: Undefined names (20 errores)

Son funciones/variables que se referencian pero **no existen** o no están importadas. Van a explotar en runtime.

| Archivo | Símbolo | Acción |
|---|---|---|
| `src/app/modules/reviews/routes.py:155` | `update_review` | Implementar o importar |
| `src/app/modules/reviews/routes.py:185` | `create_review_report` | Implementar o importar |
| `src/app/modules/reviews/routes.py:215` | `list_review_reports` | Implementar o importar |
| `src/app/modules/partner/services/rates/plans.py:185` | `clean_name` | Implementar o importar |
| `src/app/modules/reviews/service/collections.py:34` | `ModuleStatus` | Importar faltante |
| `src/app/modules/lost_and_found/service/collections.py:22` | `ModuleStatus` | Importar faltante |
| Módulos HR, Housekeeping, Expenses, Billing | `ModuleStatus` | Importar faltante |
| `src/app/modules/settings/routes.py:163` | `settings` | Importar faltante |
| `src/app/modules/account/routes.py:180` | `settings` | Importar faltante |
| `src/etl/ga03_airflow/load.py:21,55` | `Path` | Importar faltante |
| `src/app/modules/admin/routes.py:236,272,280` | `Any` | Importar de typing |
| `src/app/modules/partner/routes/rooms.py:218` | `UploadFile` | Importar faltante |
| `src/app/modules/partner/routes/rooms.py:230` | `uuid` | Importar faltante |

### 🟡 Prioridad 2 — Ruff: Auto-fix + Mypy stubs

- Ejecutar `ruff check --fix` para corregir 174 errores automáticos (imports sin usar, trailing commas, quotes, etc.)
- Instalar stubs: `pip install pandas-stubs types-passlib types-openpyxl`

### 🟢 Prioridad 3 — ESLint: Auto-fix

- Ejecutar `eslint --fix` para corregir 207 errores automáticos (`array-type`, `no-inferrable-types`, `prefer-const`, `eqeqeq`, `no-output-on-prefix`)

### 🔵 Prioridad 4 — Correcciones masivas manuales

- `@typescript-eslint/no-explicit-any` (299): Tipar con tipos concretos
- `E501` line-too-long (3,053): Cortar líneas >88 caracteres
- `D103` / `ANN201` / `ANN001` / `D100`: Agregar docstrings y type hints
- `@angular-eslint/template/*` (accesibilidad): Agregar key events, focus, labels

---

## 5. Comandos Útiles

```bash
# Backend — Auto-fix Ruff
ruff check --fix server/src server/config server/tests server/scripts server/dags

# Backend — Instalar stubs de tipos
pip install pandas-stubs types-passlib types-openpyxl

# Backend — Verificar Mypy
mypy server/src/app server/src/database server/src/etl

# Frontend — Auto-fix ESLint
npx eslint --fix src/

# Frontend — Verificar ESLint
npx eslint src/
```
