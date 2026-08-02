# Plan de Migración Completa a Angular 22

## Resumen Ejecutivo

Este documento describe la migración completa del frontend hacia Angular 22, abarcando no solo la eliminación de suscripciones manuales, sino también la adopción de patrones modernos del framework: señales, control flow, componentes standalone, detección de cambios sin `zone.js`, y APIs como `httpResource`/`rxResource`.

## Estado Actual del Frontend

- **Angular**: 22.0.0 / 22.0.2 instalado en `node_modules`.
- **Versión real verificada**: `@angular/core` **22.0.2** en `node_modules`.
- **Fecha de release**: Angular v22 fue anunciado el **3 de junio de 2026** ([Angular Blog](https://blog.angular.dev/announcing-angular-v22-c52bb83a4664)).
- **Router**: ya usa guards funcionales (`CanActivateFn`) y lazy loading.
- **Configuración**: ya usa `ApplicationConfig`, `provideRouter`, `provideHttpClient` con interceptores funcionales.
- **Componentes**: mayoría standalone, pero aún hay restos de APIs antiguas.
- **Suscripciones manuales**: ~183 `.subscribe(` en `src/app`.
- **`takeUntilDestroyed`**: ~157 ocurrencias.
- **RxJS Subject/BehaviorSubject**: usado para búsquedas y refrescos.
- **`NgZone` + `ChangeDetectorRef`**: aún usados en componentes complejos.
- **Renderer2**: aún usado en directivas.
- **Control flow antiguo**: `*ngIf`, `*ngFor`, `*ngSwitch` aún presentes en templates.

## Estado de APIs en Angular 22 (según documentación y comunidad)

| API | Estado en Angular 22 | Notas |
|---|---|---|
| Nuevo control flow (`@if`, `@for`, `@switch`) | **Estable** | Recomendado para todos los templates. |
| Componentes standalone | **Estable** | Default en Angular moderno. |
| Señales (`signal`, `computed`, `effect`) | **Estable** | Base de la reactividad moderna. |
| Zoneless change detection | **Estable** | Puede habilitarse como default en Angular 22. |
| `resource()` | **Estable** | API base para datos asíncronos. Production-ready en Angular v22. |
| `rxResource()` | **Estable** | API para datos asíncronos basada en RxJS. Production-ready al mismo nivel que `resource` y `httpResource`. Confirmado con fixes de memory leak en notas de v22. |
| `httpResource()` | **Estable** | Wrapper de `resource()` para HTTP. |
| `linkedSignal()` | **Estable** | Útil para estado derivado escribible. Graduó a estable en Angular 20. |
| Signal Forms | **Estable** | Angular v22 anuncia Signal Forms como production-ready. |
| `@boundary` / `@error` en templates | **No disponible aún** | No existe en Angular 22 estable. El equipo de Angular lo tiene "en progreso" y se espera para v22.1 o v23 (posiblemente Q3 2026). No se puede usar todavía. |

> **Nota**: En Angular 22, `resource`, `httpResource` y `rxResource` son APIs **estables y production-ready** según el anuncio oficial. Las tres forman parte del mismo grupo de "Asynchronous Reactivity APIs". No es necesario crear wrappers defensivos; pueden usarse directamente.

---

## Áreas de Migración

### 1. Capa de Datos: `httpResource` / `rxResource`

**Objetivo**: Reemplazar `switchMap` + `subscribe` manual por recursos declarativos. Usar las APIs directamente, sin wrappers genéricos.

**Sintaxis recomendada**:

```ts
import { httpResource } from '@angular/common/http';

readonly invoiceResource = httpResource<InvoiceViewModel>(() => {
  const id = this.invoiceId();
  return id ? `/api/billing/invoices/${id}` : undefined;
}, {
  parse: (res) => mapInvoiceDetail(res as InvoiceDetailDto),
});

readonly invoice = computed(() => this.invoiceResource.value() ?? null);
readonly invoiceError = computed(() => this.invoiceResource.error());
readonly invoiceLoading = computed(() => this.invoiceResource.isLoading());
```

**Consideraciones prácticas**:
- Usar `httpResource`/`rxResource` directamente en cada componente.
- Cuando cambian los parámetros, `value()` puede volverse `undefined` brevemente, causando "flickering".
- Soluciones:
  - Usar `defaultValue` si está disponible.
  - Usar `linkedSignal` para preservar el valor anterior.
  - Mostrar estado de carga/skeleton mientras `isLoading()` es true.
- No crear wrappers genéricos: las APIs son estables y usarlas directamente mantiene el código simple y aprovecha las optimizaciones del framework.

**Tareas**:
- Migrar todos los GETs de páginas y componentes.
- Reemplazar `takeUntilDestroyed` en carga de datos.
- Mutaciones deben refrescar con `resource.reload()`.
- Eliminar `DestroyRef` donde solo se usaba para `takeUntilDestroyed`.

---

### 2. Señales (`signals`) y Estado Reactivo

**Objetivo**: Reemplazar `BehaviorSubject`, `Subject`, y estado imperativo por señales.

**Casos encontrados**:
- Búsquedas con `Subject` + `debounceTime`.
- Refrescadores con `BehaviorSubject<void>`.
- Estado local compartido entre componentes.

**Patrón objetivo**:

```ts
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { debounceTime } from 'rxjs/operators';

readonly searchQuery = signal('');
readonly debouncedQuery = toSignal(
  toObservable(this.searchQuery).pipe(debounceTime(300)),
  { initialValue: '' }
);
```

**Tareas**:
- Convertir `Subject<string>` de búsqueda a `signal` + `toObservable`.
- Reemplazar `BehaviorSubject` de estado por `signal` o `linkedSignal`.
- Revisar stores basados en RxJS.

---

### 3. Nuevo Control Flow

**Objetivo**: Reemplazar `*ngIf`, `*ngFor`, `*ngSwitch` por `@if`, `@for`, `@switch`.

**Beneficios**:
- Mejor rendimiento.
- Sintaxis más legible.
- Mejor soporte de TypeScript en bloques.
- No requiere importar `NgIf`, `NgFor`, `NgSwitch`.

**Patrón objetivo**:

```html
@if (invoice(); as inv) {
  <app-invoice-detail [invoice]="inv" />
} @else if (invoiceLoading()) {
  <app-loading />
} @else {
  <app-error-state />
}

@for (item of lineItems(); track item.itemId) {
  <tr>...</tr>
} @empty {
  <tr><td>No hay items</td></tr>
}
```

**Tareas**:
- Migrar templates página por página.
- Reemplazar `trackBy` por `track`.
- Eliminar importaciones de `NgIf`, `NgFor`, `NgSwitch`.

---

### 4. Componentes Standalone y Limpieza de Módulos

**Objetivo**: Asegurar que todos los componentes sean standalone y eliminar `NgModule` residuales.

**Estado actual**:
- La mayoría de componentes ya son standalone.
- Pocos o ningún `NgModule` en el código propio.
- Algunos componentes aún usan `OnInit`/`OnChanges` innecesariamente.

**Tareas**:
- Verificar que no quede ningún `@NgModule` propio.
- Eliminar `OnInit`/`OnChanges` donde solo se usen para suscripciones.
- Revisar imports de componentes para evitar dependencias circulares.

---

### 5. Detección de Cambios sin `zone.js` (Zoneless)

**Objetivo**: Habilitar detección de cambios sin `zone.js` y eliminar `NgZone`.

**Historial y cambios en Angular 22**:
- **Desde Angular v21**: zoneless-by-default para proyectos nuevos (la API `provideZonelessChangeDetection()` es estable desde v21).
- **Novedad en Angular v22**: **OnPush pasa a ser el default** para componentes nuevos (antes solo zoneless lo era).
- `ChangeDetectionStrategy.Default` fue renombrado a `ChangeDetectionStrategy.Eager`.
- Ambas características (zoneless + OnPush default) ya no requieren flags experimentales en v22.

**Consideraciones**:
- En Angular 22, zoneless es **estable** y puede ser el default.
- Requiere que todos los componentes usen `ChangeDetectionStrategy.OnPush` o señales.
- Código que usa `NgZone.runOutsideAngular` necesita reescribirse.
- `ChangeDetectorRef.markForCheck()` debe reemplazarse por señales.

**Casos encontrados**:
- `rooms-page.ts`: usa `NgZone` + `ChangeDetectorRef`.
- `property-selector.ts`: usa `NgZone` indirectamente.

**Patrón objetivo**:

```ts
import { provideZonelessChangeDetection } from '@angular/core';

export const appConfig: ApplicationConfig = {
  providers: [
    // En Angular v22, zoneless es estable (default para apps nuevas desde v21).
    // Para apps legacy que aún usan zone.js, habilitar con:
    provideZonelessChangeDetection(),
    provideHttpClient(...),
    provideRouter(...),
  ],
};
```

**Tareas**:
- Reemplazar `NgZone.runOutsideAngular` por `requestAnimationFrame` o scheduler de RxJS.
- Reemplazar `markForCheck()` por señales.
- Habilitar zoneless progresivamente, feature por feature.

---

### 6. Manejo de Errores en Templates (`@boundary` / `@error`)

**Objetivo**: Prepararse para usar el nuevo manejo de errores en templates cuando esté disponible.

**Estado real**:
- `@boundary` / `@error` **no está disponible en Angular 22 estable**. No existe ni como Developer Preview.
- El equipo de Angular lo tiene "en progreso" y se espera para v22.1 o v23 (posiblemente Q3 2026).
- **No se puede usar todavía** en ningún proyecto con Angular 22.
- Alternativa actual: manejar errores en el componente con `resource.error()` y componentes `<app-error-state>`.

**Estrategia**:
- Mantener el patrón actual de `resource.error()` + componentes de error.
- Revisitar `@boundary`/`@error` cuando Angular 23 o v22.1 lo incluyan de forma estable.

**Tareas**:
- Evaluar si es viable usar `@error` blocks en templates.
- De lo contrario, mantener componentes `<app-error-state>` con `resource.error()`.

---

### 7. Modernización de RxJS

**Objetivo**: Reducir uso de RxJS donde las señales lo reemplacen.

**Tareas**:
- Reemplazar `Subject` de búsqueda por señales.
- Reemplazar `BehaviorSubject` de estado por señales.
- Mantener RxJS solo para:
  - Mutaciones HTTP.
  - Combinaciones complejas (`combineLatest`, `forkJoin`).
  - Eventos del DOM (`fromEvent`).
  - Lógica de negocio compleja.

---

### 8. Directivas y Servicios Core

**Objetivo**: Modernizar directivas y servicios compartidos.

**Casos encontrados**:
- `ai-suggest.directive.ts`: usa `Renderer2`.
- `property-context.service.ts`: usa suscripciones manuales.
- `version-check.service.ts`: usa `takeUntilDestroyed`.

**Tareas**:
- Reemplazar `Renderer2` por bindings nativos o señales.
- Migrar servicios de estado a señales.
- Usar `httpResource` en servicios que cargan datos.

---

### 9. Testing

**Objetivo**: Actualizar tests para Angular 22.

**Tareas**:
- Reemplazar `TestBed.configureTestingModule` por configuración con standalone components.
- Actualizar mocks de `HttpClient` por `HttpClientTestingModule`.
- Adaptar tests de componentes con señales.
- Verificar que `provideHttpClient` y `provideRouter` se usen en tests.
- Considerar migrar de Karma/Jasmine a Vitest si aplica.

---

### 10. Migración a Signal Forms

**Objetivo**: Evaluar y migrar formularios a Signal Forms donde aporte valor.

**Consideraciones**:
- Signal Forms es **estable y production-ready** en Angular v22.
- No es necesario migrar todos los formularios existentes de golpe.
- Priorizar formularios nuevos o muy complejos con Reactive Forms.
- Mantener Reactive Forms existentes si funcionan bien.

**Tareas**:
- Evaluar formularios candidatos para Signal Forms.
- Migrar formularios nuevos a Signal Forms.
- Documentar convenciones de validación con Signal Forms.

### 11. Nuevas APIs de Angular 22 a Considerar

**`@Service` decorator**:
- Reemplazo más intuitivo de `@Injectable({ providedIn: 'root' })`.
- Útil para stores y servicios globales.

**`injectAsync`**:
- Permite inyección de dependencias asíncrona y code splitting.
- Útil para dependencias grandes como exportadores PDF o librerías de mapas.
- **Requiere** que el servicio esté auto-provisto con `@Injectable({ providedIn: 'root' })` o `@Service()`.

**`withExperimentalAutoCleanupInjectors`**:
- Limpia inyectores de rutas inactivas para evitar memory leaks.
- Experimental en Angular 22.

### 12. Build y Tooling

**Objetivo**: Aprovechar el build system moderno.

**Cambios en Angular 22**:
- **Webpack está deprecado** en Angular v22.
- El build por defecto es el `application` builder basado en esbuild/vite.
- **TypeScript 6 es obligatorio** (v5.9 y anteriores no funcionan en Angular v22).

**Requisitos de toolchain (obligatorios)**:
- **Node.js**: 22.22+ o 26.x (Node 20 fue descontinuado para Angular v22).
- **TypeScript**: 6.x (v5.9 y anteriores no funcionan).

**Tareas**:
- Verificar que `@angular/build` y `@angular/cli` estén alineados.
- Revisar `angular.json` para usar `application` builder (reemplaza `@angular-devkit/build-angular:browser`).
- Eliminar configuraciones de Webpack si existen.
- Verificar que Node.js y TypeScript cumplen los requisitos mínimos en CI y entornos locales.

---

## Plan por Sprints

### Sprint 0: Auditoría y Preparación

**Objetivo**: Tener una línea base clara antes de tocar código.

| Tarea | Esfuerzo |
|---|---|
| Inventario completo de `.subscribe()`, `Subject`, `NgZone`, `ChangeDetectorRef`, `Renderer2`, `*ngIf`, `*ngFor` | 2 días |
| Definir convenciones de código para señales y recursos | 1 día |
| Crear utilidades compartidas para mapeo de DTOs y manejo de errores | 2 días |
| Setup de tests para validar migraciones | 1 día |

**Entregables**:
- Spreadsheet con todos los archivos a migrar.
- Guía de estilo para `httpResource` + señales.
- Helpers de mapeo y manejo de errores creados (sin wrappers genéricos).

---

### Sprint 1: Core y Shared

**Objetivo**: Modernizar la infraestructura base.

| Área | Archivos/Tareas | Esfuerzo |
|---|---|---|
| `core/auth` | Migrar login, register, recover, reset, verify-email a recursos/señales | 3 días |
| `core/services` | `version-check.service.ts`, `tracking.service.ts` | 1 día |
| `core/directives` | `ai-suggest.directive.ts`: eliminar `Renderer2` | 1 día |
| `shared/services` | `property-context.service.ts`: migrar a señales | 2 días |
| `shared/ui` | access-nav, top-nav, sidebar-nav, property-selector: migrar búsquedas a señales | 3 días |

**Criterios de aceptación**:
- Ningún componente de `core` o `shared` usa `.subscribe()` para carga de datos.
- No quedan `Subject` de búsqueda en shared UI.
- Templates de los componentes migrados usan `@if`/`@for`/`@switch`.
- Typecheck pasa.

---

### Sprint 2: Account y Admin

**Objetivo**: Migrar áreas de usuario y administración.

| Área | Archivos | Esfuerzo |
|---|---|---|
| `account` | `profile-page.ts`, `profile-security.ts` | 2 días |
| `admin/dashboard` | `dashboard-page.ts` | 1 día |
| `admin/global-settings` | `global-settings-page.ts` | 2 días |
| `admin/earnings` | `earnings-page.ts` | 1 día |

**Criterios de aceptación**:
- Admin y account usan recursos declarativos.
- Templates migrados a nuevo control flow.

---

### Sprint 3: Billing y Expenses

**Objetivo**: Migrar facturación, pagos, folios y gastos.

| Área | Archivos | Esfuerzo |
|---|---|---|
| `billing` | invoice-detail, client-invoice-detail, payments-list, client-invoices-list, folio-detail | 4 días |
| `expenses` | ledger-page, invoices-list, invoice-detail, invoice-form | 3 días |

**Criterios de aceptación**:
- Todos los GETs de billing/expenses usan `httpResource`/`rxResource`.
- Mutaciones refrescan con `resource.reload()`.
- Templates de billing/expenses migrados a `@if`/`@for`/`@switch`.

---

### Sprint 4: Check-ins, Check-outs y Reservations

**Objetivo**: Migrar flujo de llegadas, salidas y reservas.

| Área | Archivos | Esfuerzo |
|---|---|---|
| `check-ins` | check-ins-page, check-in-detail-page | 2 días |
| `check-outs` | check-outs-page, check-out-detail-page, co-step-invoice | 3 días |
| `reservations` | reservations-list, reservation-new, reservation-detail, reservation-timeline | 5 días |

**Criterios de aceptación**:
- Check-ins/check-outs usan recursos condicionales para modales.
- Reservation detail elimina carga manual de productos y line items.
- Templates de check-ins, check-outs y reservations migrados a `@if`/`@for`/`@switch`.

---

### Sprint 5: Properties, Rooms y Rates

**Objetivo**: Migrar propiedades, habitaciones y tarifas.

| Área | Archivos | Esfuerzo |
|---|---|---|
| `properties` | property-history, property-edit, image-gallery | 3 días |
| `rooms` | rooms-page (eliminar NgZone/CDR) | 3 días |
| `rates` | rates-page, promotion-form | 3 días |

**Criterios de aceptación**:
- `rooms-page` no usa `NgZone` ni `ChangeDetectorRef`.
- Properties y rates migrados a recursos.
- Templates de properties, rooms y rates migrados a `@if`/`@for`/`@switch`.

---

### Sprint 6: Housekeeping, Amenities, Geo y Map

**Objetivo**: Migrar limpieza, amenidades y catálogo geográfico.

| Área | Archivos | Esfuerzo |
|---|---|---|
| `housekeeping` | room-history, maintenance, additional-charges | 3 días |
| `amenities` | amenities-page, guest-amenity-catalog-page | 2 días |
| `geo-catalog` | geo-catalog-page | 2 días |
| `map` | world-map-page, destinations-list, destination-editor | 2 días |

**Criterios de aceptación**:
- GETs de housekeeping, amenities, geo y map usan `httpResource`/`rxResource`.
- Templates migrados a `@if`/`@for`/`@switch`.

---

### Sprint 7: HR y System Admin

**Objetivo**: Migrar recursos humanos y administración del sistema.

| Área | Archivos | Esfuerzo |
|---|---|---|
| `hr` | my-portal-redirect, employee-onboarding, employee-list, employee-detail, employee-dashboard | 4 días |
| `system-admin` | system-users, system-permissions, monitoring, notifications | 3 días |

**Criterios de aceptación**:
- GETs de HR y system-admin usan `httpResource`/`rxResource`.
- Templates migrados a `@if`/`@for`/`@switch`.

---

### Sprint 8: In-stay, Ownership y Manual Reservations

**Objetivo**: Migrar portal de huésped, ownership y reservas manuales.

| Área | Archivos | Esfuerzo |
|---|---|---|
| `in-stay` | staff-inbox-page, guest-portal-page, folio-transactions-modal | 4 días |
| `ownership` | ownership-user-detail, ownership-list, ownership-create | 2 días |
| `manual-reservations` | manual-reservations-list, manual-reservation-new | 2 días |

**Criterios de aceptación**:
- GETs de in-stay, ownership y manual-reservations usan `httpResource`/`rxResource`.
- Templates migrados a `@if`/`@for`/`@switch`.

---

### Sprint 9: Reviews, Notifications, Lost & Found y Otros

**Objetivo**: Migrar features restantes.

| Área | Archivos | Esfuerzo |
|---|---|---|
| `reviews` | reviews-list, review-detail, reputation-dashboard, review-form | 3 días |
| `notifications` | notifications-page, notification-bell | 1 día |
| `lost-and-found` | lost-and-found-page | 1 día |
| `hotel-search` | hotel-search-page | 1 día |
| `hotel-compare` | hotel-compare-page | 1 día |
| `shifts` | control-turnos-caja-page | 1 día |
| `management` | settings-page, audit-log-page | 2 días |

**Criterios de aceptación**:
- GETs de todas las features usan `httpResource`/`rxResource`.
- Templates migrados a `@if`/`@for`/`@switch`.

---

### Sprint 10: Availability y Stores Complejos

**Objetivo**: Migrar availability (la más compleja) y limpiar stores.

| Área | Archivos | Esfuerzo |
|---|---|---|
| `availability` | availability.store.ts, selection.service.ts, inventory.service.ts, blackout.service.ts | 5 días |
| Limpieza | Eliminar métodos de servicios no usados | 2 días |

**Criterios de aceptación**:
- Stores y servicios de availability migrados a señales donde aplique.
- Métodos no usados eliminados.
- Templates de componentes de availability migrados a `@if`/`@for`/`@switch` donde corresponda.

---

### Sprint 11: Limpieza de Control Flow Residual

**Objetivo**: Eliminar `*ngIf`/`*ngFor`/`*ngSwitch` remanentes en features que no se migraron completamente en Sprints 1–10.

| Tarea | Esfuerzo |
|---|---|
| Buscar y reemplazar `*ngIf`/`*ngFor`/`*ngSwitch` residuales en templates no tocados | 1 día |
| Eliminar importaciones huérfanas de `NgIf`, `NgFor`, `NgSwitch` | 0.5 día |
| Typecheck global post-limpieza | 0.5 día |

---

### Sprint 12: Zoneless Change Detection

**Objetivo**: Habilitar detección de cambios sin `zone.js`.

| Tarea | Esfuerzo |
|---|---|
| Reemplazar `NgZone.runOutsideAngular` | 2 días |
| Reemplazar `ChangeDetectorRef.markForCheck()` | 2 días |
| Habilitar `provideZonelessChangeDetection()` (API estable, sin prefijo "Experimental") | 1 día |
| Validar UI en todas las features críticas | 3 días |

---

### Sprint 13: Testing, Optimización y Rollout

**Objetivo**: Validar toda la migración y optimizar.

| Tarea | Esfuerzo |
|---|---|
| Typecheck completo del frontend | 1 día |
| Actualizar tests unitarios | 3 días |
| Pruebas de regresión manuales | 3 días |
| Optimización de re-fetches y caching | 2 días |
| Documentación final y handoff | 1 día |

---

## Pitfalls Reportados por la Comunidad

### 1. Flickering en `httpResource`/`rxResource`

Cuando cambian los parámetros de entrada, `value()` puede volverse `undefined` brevemente.

**Soluciones**:
- Usar `defaultValue` si está disponible.
- Usar `linkedSignal` para preservar el valor anterior.
- Mostrar skeleton/loading state mientras `isLoading()` es true.

### 2. Zoneless no detecta cambios

Código que dependía de `zone.js` para detectar cambios asíncronos puede dejar de funcionar.

**Soluciones**:
- Asegurar que todo el estado sea señal o input.
- Reemplazar `markForCheck()` por señales.
- Usar `effect()` para side effects.

### 3. RxJS no desaparece

Aunque las señales reemplazan mucho estado, RxJS sigue siendo necesario para:
- Mutaciones HTTP.
- Combinaciones de streams complejas.
- Eventos del DOM.
- Lógica de negocio con operadores.

### 4. `linkedSignal` puede confundir

`linkedSignal` es útil pero no siempre necesario. Usarlo solo cuando se necesita estado derivado que también sea escribible. Es estable en Angular 22.

---

## Riesgos y Mitigación

| Riesgo | Impacto | Mitigación |
|---|---|---|
| `withExperimentalAutoCleanupInjectors` o APIs futuras (`@boundary`) cambian antes de estabilizarse | Medio | No depender de APIs no estables en producción; usar solo las confirmadas estables (`resource`, `httpResource`, señales, Signal Forms). |
| Regresiones en availability/reservations | Alto | Migrar por partes; mantener tests; validar con QA. |
| Zoneless rompe UI | Alto | Habilitar al final; probar todas las features. |
| Flickering en recursos | Medio | Usar `linkedSignal` o `defaultValue`; mostrar loading states. |
| Tiempo subestimado | Medio | Reservar buffer en sprints grandes. |
| Inconsistencias durante transición | Medio | No mezclar patrones en el mismo componente. |

## Definición de Hecho

- Componente migrado a `httpResource`/`rxResource` para todos sus GETs.
- No quedan suscripciones manuales para carga de datos.
- No quedan `Subject`/`BehaviorSubject` para estado local.
- Templates usan `@if`/`@for`/`@switch`.
- Componentes son standalone sin `NgModule` propio.
- Mutaciones refrescan datos con `resource.reload()`.
- No hay imports ni inyecciones muertas.
- Typecheck pasa sin errores.
- Tests críticos pasan.

## Estimación Total

- **Sprints**: 14 sprints.
- **Duración total estimada**: 21–22 semanas con 1 desarrollador a tiempo completo (basado en la suma de esfuerzos: ~109 días ÷ 5 días/semana = ~21.8 semanas).
- **Complejidad alta**: availability, reservations, in-stay, billing, rooms (NgZone).
- **Complejidad media/baja**: account, admin, map, notifications.

## Recomendación Estratégica

La migración se organiza **feature por feature** (Sprints 1–10), no como fases globales separadas. Cada sprint debe migrar, idealmente, las tres áreas dentro de la misma feature:
- Datos (`httpResource`/`rxResource`)
- Estado (`signal`, `computed`, `linkedSignal`)
- Templates (`@if`/`@for`/`@switch`)

Esto evita tocar cada archivo dos veces (una para señales, otra para recursos) y mantiene cada feature consistente consigo misma desde el primer sprint. Los criterios de aceptación de cada sprint deben incluir explícitamente las tres áreas.

Las fases globales se reservan para el final:
1. **Sprints 1–10**: Migración feature por feature (datos + estado + templates simultáneamente).
2. **Sprint 11**: Limpieza global de control flow residual (`*ngIf`/`*ngFor` en features no migradas).
3. **Sprint 12**: Zoneless — solo cuando todo el estado ya es señal.
4. **Sprint 13**: Testing, optimización y rollout.

**Reglas**:
- **No migrar todo de golpe**: priorizar features críticas (billing, reservations, check-ins/outs) y dejar availability para cuando el equipo tenga experiencia.
- **Mantener RxJS** para mutaciones y lógica compleja; no forzar todo a señales.
- **`@boundary`/`@error` no está disponible en v22**; revisitar cuando Angular 23 lo incluya.
