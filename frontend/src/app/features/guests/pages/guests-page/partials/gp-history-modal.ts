import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import type { GuestBookingItem, GuestBookingsResponse } from '../../../services/guests-api.service';

@Component({
  selector: 'app-gp-history-modal',
  standalone: true,
  imports: [CurrencyPipe, DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './gp-history-modal.scss',
  template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="modal-panel gp-history-modal" (click)="$event.stopPropagation()">
        <div class="modal-head">
          <span class="material-symbols-outlined modal-head-icon">contact_page</span>
          <div>
            <h2>Historial de {{ data()?.guest_name || '—' }}</h2>
            <p>{{ data()?.guest_email }} · {{ data()?.total_bookings }} reserva(s)</p>
          </div>
          <button type="button" class="modal-close" (click)="close.emit()" aria-label="Cerrar">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        @if (loading()) {
          <div class="gp-history-loading">
            <span class="material-symbols-outlined spin">progress_activity</span>
            <span>Cargando historial...</span>
          </div>
        } @else if (error()) {
          <div class="gp-history-error">
            <span class="material-symbols-outlined">error</span>
            <span>{{ error() }}</span>
          </div>
        } @else if (bookings().length === 0) {
          <div class="gp-history-empty">
            <span class="material-symbols-outlined">calendar_month</span>
            <span>Sin reservas registradas.</span>
          </div>
        } @else {
          <div class="gp-history-table-wrap">
            <table class="gp-history-table">
              <thead>
                <tr>
                  <th>Folio</th>
                  <th>Entrada</th>
                  <th>Salida</th>
                  <th>Huéspedes</th>
                  <th>Total</th>
                  <th>Estado</th>
                  <th>Pago</th>
                  <th>Origen</th>
                </tr>
              </thead>
              <tbody>
                @for (b of bookings(); track b.booking_id) {
                  <tr>
                    <td><code>{{ b.booking_id.slice(-8) }}</code></td>
                    <td>{{ b.check_in_date | date:'dd/MM/yyyy' }}</td>
                    <td>{{ b.check_out_date | date:'dd/MM/yyyy' }}</td>
                    <td>{{ b.adults }}A · {{ b.children }}N · {{ b.rooms }}H</td>
                    <td class="gp-cell-money">{{ (b.total_price ?? 0) | currency:b.currency }}</td>
                    <td>
                      <span class="gp-status-badge" [class.active]="b.status === 'confirmed' || b.status === 'checked_in'"
                        [class.warn]="b.status === 'pending'"
                        [class.danger]="b.status === 'cancelled' || b.status === 'rejected'">
                        {{ b.status }}
                      </span>
                    </td>
                    <td>
                      <span class="gp-status-badge" [class.active]="b.payment_status === 'paid'"
                        [class.warn]="b.payment_status === 'pending' || b.payment_status === 'partial'"
                        [class.danger]="b.payment_status === 'failed' || b.payment_status === 'refunded'">
                        {{ b.payment_status || '—' }}
                      </span>
                    </td>
                    <td class="gp-cell-source">{{ b.booking_source || '—' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }

        <div class="modal-actions">
          <button type="button" class="btn-secondary" (click)="close.emit()">Cerrar</button>
        </div>
      </div>
    </div>
  `,
})
export class GpHistoryModalComponent {
  readonly data = input<GuestBookingsResponse | null>(null);
  readonly bookings = input<GuestBookingItem[]>([]);
  readonly loading = input(false);
  readonly error = input('');
  readonly close = output<void>();
}
