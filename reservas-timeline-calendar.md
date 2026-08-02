# Calendario de reservas — contrato operativo del Timeline

> Documento de referencia para la vista de recepción de HotelData.
> Mantener sincronizado con `ReceptionTimelineComponent` y con la API de recepción.
>
> Última actualización: 2026-08-01.

## 1. Entrada de la funcionalidad

La vista se encuentra en:

```text
/management/recepcion?prop_id=1&view=calendar
```

La página contenedora es `ReservationsListPageComponent`:

```text
frontend/src/app/features/reservations/pages/reservations-list-page/
```

La vista de recepción usa exclusivamente el Timeline de Syncfusion. El parámetro `calendar_engine` ya no forma parte del contrato y no existe una ruta alternativa de calendario.

| Parámetro | Valores | Comportamiento |
|---|---|---|
| `prop_id` | entero positivo | Hotel seleccionado para la vista operativa |
| `view` | `calendar` / ausente | `calendar` muestra el Timeline; por defecto se muestra la lista |

La página no muestra el calendario operativo a clientes finales; se requiere personal de staff y un hotel seleccionado. El permiso del endpoint es `reservations.read`.

## 2. Timeline de Syncfusion

Componente:

```text
frontend/src/app/features/reservations/components/reception-timeline/
```

Librería:

```text
@syncfusion/ej2-angular-schedule@34.1.29
```

Características activas:

- `TimelineWeek` como vista inicial.
- `TimelineMonth` disponible en el selector del Timeline.
- Una fila por habitación física, agrupada por piso y tipo de habitación.
- Reservas como eventos ubicados en la habitación correspondiente.
- Navegación anterior, siguiente y `Hoy`.
- Consulta al backend para el periodo visible de la vista activa.
- Estados visuales por color: vigente, próxima, finalizada y cancelada.
- Porcentaje de ocupación en las cabeceras de fecha.
- Diferenciación visual entre días pasados, actuales y días fuera del mes visible.
- Click en una reserva para abrir el detalle compartido.
- Accesos directos a Check-in y Check-out desde el detalle.
- Modo oscuro mediante `.e-dark-mode` y tokens del diseño global.
- Selección múltiple de celdas para preparar una reserva física.
- Panel propio de selección con fechas, horas, `Cancelar` e `Ir a reserva`.
- Selección de fechas pasadas bloqueada con notificación global.
- Reasignación de habitación mediante drag-and-drop para reservas vigentes o próximas.
- Conflictos de habitación con confirmación antes de escribir.
- Fechas, resize, creación y edición general permanecen desactivados.
- El editor nativo `New Event` de Syncfusion no se utiliza ni se prerenderiza.
- Mensaje de error y botón `Reintentar` sin ocultar la excepción HTTP.
- Indicador de estado operativo de housekeeping en cada fila, en modo lectura.
- La consulta de housekeeping requiere `housekeeping.read`; si falla, el Timeline permanece visible con una advertencia no bloqueante.

La clave `SYNCFUSION_LICENSE_KEY` se lee en runtime desde `.env`; nunca debe hardcodearse en TypeScript ni documentarse con su valor real.

## 3. Endpoint de datos

Ruta backend compartida por el Timeline:

```text
GET /api/management/reception/calendar
```

Desde Angular se solicita como `/management/reception/calendar`; el `baseUrlInterceptor` antepone `/api` automáticamente. No usar `/api/management/...` en el nuevo código si la petición pasa por `HttpClient`, salvo que se compruebe que ya está prefijada.

Parámetros:

| Parámetro | Obligatorio | Descripción |
|---|---:|---|
| `prop_id` | sí | Propiedad/hotel, entero mayor o igual a 1 |
| `start_date` | no | Inicio ISO `YYYY-MM-DD` |
| `end_date` | no | Fin ISO `YYYY-MM-DD` |

Los componentes del Timeline envían fechas explícitas. En `TimelineWeek` se consulta una ventana de siete días. En `TimelineMonth` se consulta la cuadrícula completa del mes visible, incluyendo los días de la primera y última semana que Syncfusion dibuja.

Permiso requerido:

```text
reservations.read
```

El backend carga todas las habitaciones activas de `hotel_rooms` y todas las reservas que se solapan con el rango. Una reserva sin `assigned_rooms` puede aparecer en la respuesta como `UNASSIGNED` para representación informativa, pero no se asigna a una fila física.

## 4. Forma de respuesta

Respuesta raíz:

```json
{
  "rooms": [],
  "start_date": "2026-08-03",
  "end_date": "2026-08-09",
  "today": "2026-08-01"
}
```

Cada elemento de `rooms`:

```json
{
  "room_number": "110",
  "hotel_room_id": "HR-1-110",
  "room_type_name": "Habitación Doble Premium",
  "room_type_id": "RT-1-habitacion-doble-premiun",
  "floor": "1",
  "reservations": []
}
```

Cada reserva contiene:

| Campo | Uso |
|---|---|
| `booking_id` | Identidad y navegación al detalle |
| `guest_name` | Texto del evento |
| `adults`, `children` | Resumen de ocupación |
| `check_in_date`, `check_out_date` | Rango de estancia |
| `check_in_time`, `check_out_time` | Hora del evento y del panel de selección |
| `check_in_fraction`, `check_out_fraction` | Compatibilidad del contrato; el Timeline usa fechas y horas |
| `total_nights` | Resumen de estancia |
| `status` | Estado de negocio original |
| `visual_status` | Estado normalizado: `active`, `upcoming`, `past`, `cancelled` |
| `assigned_rooms` | Habitaciones físicas asignadas |
| `hotel_room_id` | Fila física de la reserva |
| `room_number` | Etiqueta visible |
| `total_price` | Total, nullable |
| `currency` | Moneda, normalmente `USD` |

El mapper `mapReceptionCalendar` transforma snake case a camel case y es la entrada de datos del Timeline.

## 5. Recursos y estado operativo

El Timeline construye tres niveles de recursos:

```text
Piso
└── Tipo de habitación
    └── Habitación física
```

- Piso y tipo usan encabezados compactos, con icono y texto alineados al inicio.
- Las habitaciones conservan una fila funcional más amplia para mostrar número y estado operativo.
- El estado de housekeeping es de solo lectura.
- El Timeline reutiliza `GET /api/housekeeping/room-status?page_size=200` y requiere `housekeeping.read`.
- El Timeline no crea tareas, no cambia estados de housekeeping y no sustituye la interfaz de housekeeping.
- Para hoteles con más de 200 habitaciones se deberá incorporar paginación o un endpoint agregado antes de ampliar esta integración.

## 6. Reglas de estado visual

El backend calcula `visual_status` con la fecha local:

- `cancelled`: `status` es `cancelled` o `rejected`.
- `upcoming`: hoy es anterior al check-in.
- `past`: hoy es posterior al check-out.
- `active`: hoy está dentro del intervalo de la reserva.

El estado visual no sustituye al `status` original. Cualquier acción de negocio utiliza el estado de reserva y las validaciones del backend.

## 7. Interacciones y navegación

### Click en una reserva

1. El Timeline cancela el popup nativo.
2. Guarda el evento seleccionado.
3. El componente compartido consulta `GET /api/reservations/{booking_id}` mediante la ruta Angular `/reservations/{booking_id}` más el interceptor.
4. Se abre el panel compartido de detalle sin abandonar el contexto del Timeline.
5. `Escape`, backdrop y botón de cierre cierran el panel.
6. Los botones llevan a:
   - `/management/check-ins/{booking_id}`
   - `/management/check-outs/{booking_id}`

### Selección de celdas para reserva física

1. El usuario selecciona una o varias celdas futuras de una habitación.
2. La selección queda pintada en la cuadrícula.
3. El panel propio muestra habitación, fechas, horas y los botones `Cancelar` e `Ir a reserva`.
4. Seleccionar nuevamente la misma celda descarta el panel.
5. `Cancelar` descarta la selección sin navegar.
6. `Ir a reserva` navega a:

```text
/management/recepcion/new
```

En la navegación se transfieren `prop_id`, habitación, tipo de habitación, fechas y horas. La cantidad de huéspedes se completa en la pantalla de reserva física.

No se utiliza el editor nativo de eventos de Syncfusion para este flujo.

### Reasignación de habitación

Solo se pueden arrastrar reservas `upcoming` o `active` con habitación física asignada. La API es:

```text
POST /api/management/bookings/{booking_id}/assign-rooms
body: { "room_ids": ["HR-1-110"] }
```

La operación requiere `reservations.update`. Si la habitación destino tiene otra reserva vigente o próxima, se pide confirmación; después de éxito se recarga la fuente HTTP y no se muta la posición local de forma optimista.

## 8. Permisos y seguridad

- Visibilidad de la vista y endpoint: `reservations.read`.
- Consulta del estado operativo: `housekeeping.read`.
- Reasignación de habitaciones: `reservations.update`.
- Check-in y check-out tienen permisos y validaciones propios.
- El componente no consulta habitaciones ni reservas sin `prop_id` válido.
- La API mantiene la autorización; el frontend solo mejora la experiencia.
- `.env.example` contiene únicamente el placeholder de `SYNCFUSION_LICENSE_KEY`.
- Ningún commit debe incluir `.env` ni la clave real.

## 9. Decisiones de diseño actuales

- El Timeline de Syncfusion es la única vista de calendario de recepción.
- No existe fallback clásico ni selector `calendar_engine`.
- `rowAutoHeight` permanece desactivado para preservar la alineación entre la columna de recursos y la cuadrícula temporal.
- En `TimelineMonth`, `+N more` se conserva cuando Syncfusion necesita limitar eventos superpuestos; activar `rowAutoHeight` expandiría filas y rompería el diseño compacto.
- El endpoint de recepción y el modelo `reception-calendar.model.ts` se mantienen porque son el contrato compartido del Timeline.

## 10. Checklist de regresión

- [ ] `prop_id` inválido no provoca una consulta.
- [ ] La vista de recepción carga únicamente el Timeline.
- [ ] Una URL con `calendar_engine=classic` no muestra un calendario clásico.
- [ ] El endpoint devuelve habitaciones vacías y ocupadas correctamente.
- [ ] Una reserva se pinta en la habitación asignada.
- [ ] Las reservas canceladas no aparecen como vigentes.
- [ ] La ventana de fechas coincide con la vista activa.
- [ ] La vista semanal y mensual conservan alineación entre recursos y fechas.
- [ ] Click, Escape y cierre por backdrop funcionan.
- [ ] El panel de selección muestra fechas y horas seleccionadas.
- [ ] El panel conserva `Cancelar` e `Ir a reserva`.
- [ ] Las fechas pasadas no se pueden seleccionar.
- [ ] Los enlaces a Check-in y Check-out conservan el `booking_id`.
- [ ] El detalle muestra error visible si la API falla.
- [ ] El modo claro y oscuro tienen contraste suficiente.
- [ ] Piso y tipo muestran flecha/icono y texto juntos.
- [ ] El estado de housekeeping se consulta solo en modo lectura.
- [ ] Drag-and-drop solo reasigna reservas `active`/`upcoming`.
- [ ] La clave Syncfusion no aparece en código, logs, documentación ni Git.
- [ ] Typecheck, build, lint focalizado, pruebas y `git diff --check` pasan.
