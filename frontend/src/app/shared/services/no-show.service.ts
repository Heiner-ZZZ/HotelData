import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom, Observable } from 'rxjs';

import { catchAuthError } from '../utils/catch-auth-error';
import { ConfirmDialogService } from '../ui/confirm-dialog/confirm-dialog.service';

/** Respuesta de `POST /management/bookings/{id}/no-show`. */
export interface NoShowResult {
  ok: boolean;
  booking_id: string;
  penalty_amount: number;
  check_in_date: string;
  folio_number: string | null;
}

/**
 * Flujo compartido de "Marcar no-show" — usado por el detalle de reserva,
 * el detalle de check-in y el detalle de check-out. Centraliza:
 *
 * 1. El POST único `POST /management/bookings/{id}/no-show` (requiere el
 *    permiso `reservations.update`, que valida el backend).
 * 2. El diálogo de confirmación en modo terminal (penalización de la
 *    primera noche) antes de ejecutar la acción.
 * 3. El mensaje de éxito con el monto de la penalización formateado.
 *
 * Cada página conserva su propio gate (`canMarkNoShow`) porque las
 * condiciones difieren (estado, fechas, permisos), y sus señales de UI
 * (pending, mensajes, folio mostrado en el panel).
 */
@Injectable({ providedIn: 'root' })
export class NoShowService {
  private readonly http = inject(HttpClient);
  private readonly confirmDialog = inject(ConfirmDialogService);

  /** Marca la reserva como no-show (penalización de la primera noche). */
  markNoShow(bookingId: string): Observable<NoShowResult> {
    return this.http.post<NoShowResult>(`/management/bookings/${bookingId}/no-show`, {}).pipe(catchAuthError());
  }

  /**
   * Flujo completo con confirmación: pide confirmación al operador, ejecuta
   * el POST y devuelve el resultado (folio + penalización). Devuelve `null`
   * si el operador canceló; LANZA si el POST falla.
   */
  async markNoShowWithConfirm(bookingId: string, guestName: string): Promise<NoShowResult | null> {
    const ok = await this.confirmDialog.open({
      title: 'Marcar no-show',
      message: `¿Confirmar que ${guestName} no se presentó al check-in? Se cobrará la penalización de la primera noche.`,
      confirmLabel: 'Marcar no-show',
      variant: 'danger',
      mode: 'delete',
      modeDetail: `Reserva ${bookingId}`,
    });
    if (!ok) return null;
    return await firstValueFrom(this.markNoShow(bookingId));
  }

  /** Mensaje de éxito con la penalización formateada (si aplica). */
  successMessage(result: NoShowResult): string {
    const penalty = result.penalty_amount > 0
      ? ` Se cobró $${result.penalty_amount.toFixed(2)} como penalización.`
      : '';
    return `No-show registrado.${penalty}`;
  }
}
