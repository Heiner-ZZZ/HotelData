📊 Auditoría Completa de Estados del Sistema — HotelData PMS
Resumen: 17 entidades con estado, 6 en el StateMachine, 11 fuera
────────────────────────────────────────────────────────────────────────────────
🔵 ENTIDADES EN EL STATEMACHINE CENTRALIZADO ( core/state_machine.py )
┌─────┬──────────┬────────────┬───────┬────────────────────────────────────┬────────────────┐
│ #   │ Entidad  │ Colección  │ Campo │ Estados                            │ Transiciones   │
├─────┼──────────┼────────────┼───────┼────────────────────────────────────┼────────────────┤
│ 1   │ Reserva  │ booking_or │ statu │ pending → confirmed → checked_in → │ 6 estados, 6   │
│     │ (Booking │ ders       │ s     │ checked_out / rejected / cancelled │ transiciones   │
│     │ )        │            │       │                                    │                │
│ 2   │ Estancia │ booking_or │ stay_ │ pending → checked_in → checked_out │ 4 estados, 4   │
│     │ (Stay)   │ ders       │ statu │ / no_show → pending (reapertura    │ transiciones   │
│     │          │            │ s     │ gerencial con check-ins.no_show_  │                │
│     │          │            │       │ reopen)                            │                │
│ 3   │ Habitaci │ room_statu │ statu │ Ciclo completo housekeeping (10    │ 10 estados,    │
│     │ ón       │ s_log      │ s     │ estados)                           │ ~20            │
│     │ (Room)   │            │       │                                    │ transiciones   │
│ 4   │ Factura  │ reservatio │ statu │ issued → paid → refunded /         │ 4 estados, 3   │
│     │ (Invoice │ n_invoices │ s     │ cancelled                          │ transiciones   │
│     │ )        │            │       │                                    │                │
│ 5   │ Pago (Pa │ reservatio │ statu │ pending → confirmed → refunded     │ 3 estados, 2   │
│     │ yment)   │ n_payments │ s     │                                    │ transiciones   │
│ 6   │ Tarea    │ housekeepi │ statu │ pending → in_progress → completed  │ 4 estados, 3   │
│     │ (Task)   │ ng_tasks   │ s     │ / cancelled                        │ transiciones   │
└─────┴──────────┴────────────┴───────┴────────────────────────────────────┴────────────────┘
────────────────────────────────────────────────────────────────────────────────
🟡 ENTIDADES CON ESTADOS FUERA DEL STATEMACHINE
┌─────┬─────────────────┬───────────┬─────────────┬─────────────────────────┬───────────────┐
│ #   │ Entidad         │ Colección │ Campo       │ Valores                 │ ¿Tiene        │
│     │                 │           │             │                         │ validación?   │
├─────┼─────────────────┼───────────┼─────────────┼─────────────────────────┼───────────────┤
│ 7   │ Solicitud de    │ service_r │ status      │ pending → in_progress → │ ❌ No         │
│     │ Servicio        │ equests   │             │ completed / cancelled   │               │
│     │ (In-Stay)       │           │             │                         │               │
│ 8   │ Gasto (Expense  │ expense_i │ status      │ pending → approved /    │ ❌ No         │
│     │ Invoice)        │ nvoices   │             │ rejected → paid         │               │
│ 9   │ Reseña (Review) │ reviews   │ moderation_ │ pending → approved /    │ ✅ Parcial    │
│     │                 │           │ status      │ rejected                │ (edit.py      │
│     │                 │           │             │                         │ valida)       │
│ 10  │ Reporte de      │ review_re │ status      │ pending → reviewed /    │ ✅ REPORT_STA │
│     │ Reseña          │ ports     │             │ dismissed               │ TUSES set     │
│ 11  │ Objeto Perdido  │ lost_item │ status      │ pending → claimed /     │ ❌ No         │
│     │                 │ s         │             │ disposed / returned     │               │
│ 12  │ Tarea de        │ maintenan │ status      │ scheduled → in_progress │ ❌ No         │
│     │ Mantenimiento   │ ce_tasks  │             │ → completed / cancelled │               │
│ 13  │ Folio           │ guest_fol │ status      │ open → closed           │ ❌ No (solo   │
│     │                 │ ios       │             │                         │ close_folio)  │
│ 14  │ Usuario         │ users     │ is_active   │ true / false (binario)  │ ❌ No         │
│ 15  │ Sesión QR       │ stay_sess │ active      │ true / false (binario)  │ ❌ No         │
│     │ (In-Stay)       │ ions      │             │                         │               │
│ 16  │ Campaña         │ promotion │ (pendiente  │ —                       │ ❓ Sin        │
│     │ Promocional     │ _campaign │ de          │                         │ auditar       │
│     │                 │ s         │ verificar)  │                         │               │
│ 17  │ Cupón           │ coupon_co │ (pendiente  │ —                       │ ❓ Sin        │
│     │                 │ des       │ de          │                         │ auditar       │
│     │                 │           │ verificar)  │                         │               │
└─────┴─────────────────┴───────────┴─────────────┴─────────────────────────┴───────────────┘
────────────────────────────────────────────────────────────────────────────────
🔴 ESTADOS CON LÓGICA AD-HOC (candidatos a migrar al StateMachine)
// mermaid
flowchart TB
    subgraph "Booking (booking_orders.status)"
        pending --> confirmed
        pending --> rejected
        pending --> cancelled
        confirmed --> checked_in
        confirmed --> cancelled
        checked_in --> checked_out
    end
 
    subgraph "Stay (booking_orders.stay_status)"
        stay_pending["pending"] --> checked_in
        stay_pending --> no_show
        checked_in --> checked_out
        no_show -- "reapertura gerencial (check-ins.no_show_reopen)" --> stay_pending
    end
 
    subgraph "Room (room_status_log.status)"
        vacant_dirty --> cleaning_in_progress
        vacant_dirty --> maintenance_requested
        vacant_clean --> occupied_clean
        vacant_clean --> cleaning_in_progress
        occupied_clean --> occupied_dirty
        occupied_clean --> vacant_dirty
        occupied_dirty --> cleaning_in_progress
        occupied_dirty --> vacant_dirty
        cleaning_in_progress --> cleaning_completed
        cleaning_in_progress --> maintenance_requested
        cleaning_completed --> inspected
        cleaning_completed --> cleaning_in_progress
        cleaning_completed --> maintenance_requested
        inspected --> vacant_clean
        inspected --> occupied_clean
        inspected --> maintenance_requested
        out_of_service --> inspected
        out_of_service --> cleaning_in_progress
        out_of_order --> inspected
        out_of_order --> maintenance_requested
        maintenance_requested --> out_of_service
        maintenance_requested --> out_of_order
        maintenance_requested --> inspected
    end
 
    subgraph "Invoice (reservation_invoices.status)"
        issued --> paid
        issued --> cancelled
        paid --> refunded
    end
 
    subgraph "Payment (reservation_payments.status)"
        pay_pending["pending"] --> confirmed
        confirmed --> refunded
    end
 
    subgraph "Task (housekeeping_tasks.status)"
        task_pending["pending"] --> in_progress
        task_pending --> cancelled
        in_progress --> completed
        in_progress --> cancelled
    end
────────────────────────────────────────────────────────────────────────────────
🟠 ENTIDADES SIN STATEMACHINE (diagrama completo)
// mermaid
flowchart TB
    subgraph "Service Request (instay.service_requests.status)"
        sr_pending["pending"] --> sr_in_progress["in_progress"]
        sr_pending --> sr_cancelled["cancelled"]
        sr_in_progress --> sr_completed["completed"]
        sr_in_progress --> sr_cancelled
    end
 
    subgraph "Expense Invoice (expense_invoices.status)"
        ei_pending["pending"] --> ei_approved["approved"]
        ei_pending --> ei_rejected["rejected"]
        ei_approved --> ei_paid["paid"]
    end
 
    subgraph "Review Moderation (reviews.moderation_status)"
        mod_pending["pending"] --> mod_approved["approved"]
        mod_pending --> mod_rejected["rejected"]
    end
 
    subgraph "Review Report (review_reports.status)"
        rep_pending["pending"] --> reviewed
        rep_pending --> dismissed
    end
 
    subgraph "Lost Item (lost_items.status)"
        li_pending["pending"] --> claimed
        li_pending --> disposed
        li_pending --> returned
    end
 
    subgraph "Maintenance Task (maintenance_tasks.status)"
        mt_scheduled["scheduled"] --> mt_in_progress["in_progress"]
        mt_scheduled --> mt_cancelled["cancelled"]
        mt_in_progress --> mt_completed["completed"]
        mt_in_progress --> mt_cancelled
    end
 
    subgraph "Folio (guest_folios.status)"
        open --> closed
    end
────────────────────────────────────────────────────────────────────────────────
📋 ESTADOS TRANSVERSALES (colecciones con  status: "active"  como flag)
Todas las colecciones de módulos tienen un documento de  ModuleStatus  para reportar health-check:
┌──────────────┬────────────────────────────────────────────┐
│ Módulo       │ Colección de estado                        │
├──────────────┼────────────────────────────────────────────┤
│ Billing      │ reservation_invoices, reservation_payments │
│ Housekeeping │ room_status_log, housekeeping_tasks        │
│ HR           │ employees                                  │
│ Expenses     │ expense_invoices                           │
│ Reviews      │ reviews, review_reports                    │
│ Lost & Found │ lost_items                                 │
│ Instay       │ service_requests                           │
└──────────────┴────────────────────────────────────────────┘
────────────────────────────────────────────────────────────────────────────────
⚠️ HALLAZGOS CRÍTICOS
┌─────┬────────────────────────────────────────────────────────────────┬─────────────────────┐
│ #   │ Hallazgo                                                       │ Impacto             │
├─────┼────────────────────────────────────────────────────────────────┼─────────────────────┤
│ 1   │ 11 entidades con estado fuera del StateMachine — Service       │ Alto — cualquier    │
│     │ Request, Expense, Review, Lost Item, Maintenance Task tienen   │ estado inválido     │
│     │ transiciones definidas en strings pero sin validación          │ pasa                │
│     │ centralizada                                                   │ silenciosamente a   │
│     │                                                                │ BD                  │
│ 2   │ No hay transiciones validadas para Expense Invoice — pending → │ Medio               │
│     │ approved no verifica que sea válido, puede saltar de rejected  │                     │
│     │ → paid                                                         │                     │
│ 3   │ Review moderation tiene validación parcial: edit.py solo       │ Medio               │
│     │ permite editar si moderation_status == "pending", pero         │                     │
│     │ moderate_review() escribe cualquier valor sin chequear         │                     │
│     │ transición                                                     │                     │
│ 4   │ Folio open → closed — close_folio() busca status: "open" y no  │ Bajo                │
│     │ permite cerrar lo ya cerrado, pero no hay validación de que el │                     │
│     │ folio tenga saldo cero antes de cerrar                         │                     │
│ 5   │ Service Request tiene definición de SERVICE_REQUEST_STATUSES   │ Alto — similar a    │
│     │ en schemas.py como dict de labels, pero no se usa para validar │ task_sm             │
│     │ transiciones en el backend                                     │                     │
│ 6   │ Maintenance Task tiene status: str = "scheduled" como default, │ Medio —             │
│     │ pero scheduled no está en task_sm (solo pending)               │ inconsistencia      │
│     │                                                                │ semántica           │
└─────┴────────────────────────────────────────────────────────────────┴─────────────────────┘
