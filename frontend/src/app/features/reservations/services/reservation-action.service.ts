import { inject, Injectable } from '@angular/core';
import { Observable, from, map, of, switchMap, throwError } from 'rxjs';

import { ConfirmDialogService } from '../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ReservationsApiService } from './reservations-api.service';

export interface ReservationActionOptions {
  bookingId: string;
  /** Guest name shown in the confirmation dialog. If omitted, no dialog is shown. */
  guestName?: string;
}

@Injectable({ providedIn: 'root' })
export class ReservationActionService {
  private readonly api = inject(ReservationsApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);

  /**
   * Confirm a reservation.
   * If `guestName` is provided, shows a confirmation dialog first.
   * Returns an Observable that emits on success or errors on failure.
   */
  confirm(options: ReservationActionOptions): Observable<void> {
    return this.runWithOptionalDialog({
      options,
      dialogTitle: 'Confirmar reserva',
      dialogMessage: (name) => `¿Confirmar la reserva de "${name}"?`,
      confirmLabel: 'Confirmar',
      variant: 'default',
      apiCall: (id) => this.api.confirmReservation(id),
    });
  }

  /**
   * Reject a reservation.
   * If `guestName` is provided, shows a confirmation dialog first.
   * Returns an Observable that emits on success or errors on failure.
   */
  reject(options: ReservationActionOptions): Observable<void> {
    return this.runWithOptionalDialog({
      options,
      dialogTitle: 'Rechazar reserva',
      dialogMessage: (name) => `¿Rechazar la reserva de "${name}"?`,
      confirmLabel: 'Rechazar',
      variant: 'danger',
      apiCall: (id) => this.api.rejectReservation(id),
    });
  }

  private runWithOptionalDialog(args: {
    options: ReservationActionOptions;
    dialogTitle: string;
    dialogMessage: (name: string) => string;
    confirmLabel: string;
    variant: 'default' | 'danger' | 'warning';
    apiCall: (bookingId: string) => Observable<unknown>;
  }): Observable<void> {
    const preflight: Observable<boolean> = args.options.guestName
      ? from(
          this.confirmDialog.open({
            title: args.dialogTitle,
            message: args.dialogMessage(args.options.guestName),
            confirmLabel: args.confirmLabel,
            variant: args.variant,
          })
        )
      : of(true);

    return preflight.pipe(
      switchMap((ok) => {
        if (!ok) return throwError(() => new Error('Cancelled'));
        return args.apiCall(args.options.bookingId).pipe(map(() => undefined));
      })
    );
  }
}
