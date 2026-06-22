# Especificación: Solicitudes de Reserva (CU-O09)

## Descripción
El recepcionista consulta las solicitudes de reserva pendientes generadas por clientes a través del portal público. El sistema muestra una lista de solicitudes no procesadas, permitiendo al recepcionista revisar los detalles de cada una y decidir si aprueba o rechaza la solicitud.

## Actor(es)
- Recepcionista (autenticado via CU-O01)

## Precondiciones
- Recepcionista ha iniciado sesión con rol válido

## Flujo Principal
1. Recepcionista accede a la sección "Solicitudes de Reserva" del panel
2. Sistema lista las solicitudes pendientes con: nombre del cliente, fechas, tipo de habitación solicitada, estado
3. Recepcionista selecciona una solicitud para ver detalle
4. Sistema muestra información completa: datos del cliente, preferencias, fechas, mensaje adicional
5. Recepcionista puede:
   - Aprobar la solicitud → genera una reserva oficial (deriva a CU-O08)
   - Rechazar la solicitud → envía notificación al cliente con motivo opcional
   - Poner en espera → mantiene la solicitud para revisión posterior
6. Sistema registra la acción en el historial de la solicitud

## Postcondiciones
- La solicitud cambia de estado: aprobada, rechazada, o pendiente
- Si se aprueba, se crea una reserva en `booking_orders`
- Se notifica al cliente del resultado

## Flujos Alternativos
- **FA01**: Recepcionista filtra solicitudes por hotel/fecha/estado
- **FA02**: Recepcionista ordena solicitudes por urgencia (fecha de check-in próxima)
- **FA03**: Cliente cancela su solicitud antes de ser procesada → la solicitud aparece como "cancelada por cliente"

## Validaciones
- El recepcionista solo ve solicitudes de los hoteles que tiene asignados
- No se puede aprobar una solicitud si no hay disponibilidad en el inventario
- Las solicitudes expiran automáticamente después de 48 horas si no se procesan

## Reglas de Negocio
- RN01: Una solicitud de reserva no consume inventario hasta que es aprobada
- RN02: El recepcionista puede agregar notas internas visibles solo para staff
- RN03: Las solicitudes rechazadas deben mantener un registro de la razón para auditoría
