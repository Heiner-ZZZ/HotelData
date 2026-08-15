import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import type { FulfillmentItem } from '../../../models/reservations.model';

@Component({
  selector: 'app-rd-info-panels',
  standalone: true,
  imports: [CurrencyPipe, DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="insight-grid">
      <article class="surface-card panel">
        <h2>Solicitud</h2>
        <div class="table-wrap">
          <table>
            <tbody>
              <tr><th>Prop ID</th><td>{{ vm()?.propId }}</td></tr>
              @if (vm()?.roomType; as rt) {
                <tr><th>Tipo de habitación</th><td>{{ rt.name }}</td></tr>
              }
              <tr class="date-row"><th>Fechas</th><td><span class="date-range">{{ vm()?.checkInDate }}</span> <span class="date-arrow">→</span> <span class="date-range">{{ vm()?.checkOutDate }}</span></td></tr>
              @if (isExtendedDeparture(vm()?.checkOutMode)) {
                <tr>
                  <th>Salida extendida</th>
                  <td>
                    <span class="rd-extended-departure">
                      <span class="material-symbols-outlined" aria-hidden="true">event_available</span>
                      {{ lateCheckoutModeLabel(vm()?.checkOutMode) }}
                      @if ((vm()?.lateCheckoutMinutes ?? 0) > 0) {
                        · {{ vm()?.lateCheckoutMinutes }} min tras las {{ vm()?.lateCheckoutPolicyTime || 'hora de política' }}
                      }
                    </span>
                  </td>
                </tr>
              }
              <tr>
                <th>Llegada estimada</th>
                <td>
                  @if (vm()?.estimatedArrivalTime) {
                    <span class="rd-arrival-time">{{ vm()?.estimatedArrivalTime }}</span>
                  } @else {
                    <span class="cell-muted">No declarada</span>
                  }
                  @if (vm()?.lateCheckin) {
                    <span class="rd-late-badge">
                      <span class="material-symbols-outlined" aria-hidden="true">nights_stay</span>
                      Late check-in
                    </span>
                  }
                </td>
              </tr>
              <tr><th>Ocupación</th><td>{{ vm()?.occupancyLabel }}</td></tr>
              <tr><th>Comentario</th><td>{{ vm()?.comment }}</td></tr>
              @if (vm()?.specialRequests?.length > 0) {
                <tr><th>Peticiones</th><td>
                  <div class="rd-request-list">
                    @for (req of vm()?.specialRequests; track req) {
                      @let done = fulfillment().find((f) => f.label === req)?.status === 'fulfilled';
                      @let item = fulfillment().find((f) => f.label === req);
                      <div class="rd-request-row" [class.is-done]="done">
                        <span class="material-symbols-outlined rd-request-icon" aria-hidden="true">{{ done ? 'check_circle' : 'radio_button_unchecked' }}</span>
                        <span class="rd-request-label">{{ req }}</span>
                        <span class="rd-request-status" [class.is-fulfilled]="done">{{ done ? 'Cumplida' : 'Pendiente' }}</span>
                        @if (done && item?.fulfilledAt) {
                          <span class="rd-request-date" title="Cumplida el {{ item!.fulfilledAt | date:'medium' }}">{{ item!.fulfilledAt | date:'dd MMM' }}</span>
                        }
                        @if (canToggle()) {
                          <button type="button" class="rd-request-toggle" (click)="toggleFulfillment.emit({ kind: 'special_request', label: req, status: done ? 'pending' : 'fulfilled' })">
                            <span class="material-symbols-outlined">{{ done ? 'replay' : 'check' }}</span>
                            {{ done ? 'Reabrir' : 'Marcar cumplida' }}
                          </button>
                        }
                      </div>
                    }
                  </div>
                </td></tr>
              }
              @if (vm()?.selectedAmenities?.length > 0) {
                <tr><th>Servicios (amenities)</th><td>
                  <div class="rd-request-list">
                    @for (amenity of vm()?.selectedAmenities; track amenity) {
                      @let done = amenityFulfillment().find((f) => f.label === amenity)?.status === 'fulfilled';
                      @let item = amenityFulfillment().find((f) => f.label === amenity);
                      <div class="rd-request-row" [class.is-done]="done">
                        <span class="material-symbols-outlined rd-request-icon" aria-hidden="true">{{ done ? 'check_circle' : 'radio_button_unchecked' }}</span>
                        <span class="rd-request-label">{{ amenity }}</span>
                        <span class="rd-request-status" [class.is-fulfilled]="done">{{ done ? 'Cumplida' : 'Pendiente' }}</span>
                        @if (done && item?.fulfilledAt) {
                          <span class="rd-request-date" title="Cumplida el {{ item!.fulfilledAt | date:'medium' }}">{{ item!.fulfilledAt | date:'dd MMM' }}</span>
                        }
                        @if (canToggle()) {
                          <button type="button" class="rd-request-toggle" (click)="toggleFulfillment.emit({ kind: 'amenity', label: amenity, status: done ? 'pending' : 'fulfilled' })">
                            <span class="material-symbols-outlined">{{ done ? 'replay' : 'check' }}</span>
                            {{ done ? 'Reabrir' : 'Marcar cumplida' }}
                          </button>
                        }
                      </div>
                    }
                  </div>
                </td></tr>
              }
              <tr><th>Creada</th><td>{{ vm()?.createdAt }}</td></tr>
            </tbody>
          </table>
        </div>
      </article>

      <article class="surface-card panel">
        <h2>Huésped principal</h2>
        <div class="table-wrap">
          <table>
            <tbody>
              <tr><th>Nombre</th><td>{{ vm()?.guestName }}</td></tr>
              <tr><th>Email</th><td>{{ vm()?.guestEmail }}</td></tr>
              @if (vm()?.guestPhone) {
                <tr><th>Teléfono</th><td>{{ vm()?.guestPhone }}</td></tr>
              }
              @if (vm()?.guestCedula) {
                <tr><th>Cédula</th><td><strong>{{ vm()?.guestCedula }}</strong></td></tr>
              }
              @if (vm()?.totalPrice !== null) {
                <tr>
                  <th>Total</th>
                  <td>
                    @if (vm()?.discountPercent) {
                      <span style="text-decoration: line-through; opacity: 0.7; margin-right: 4px;">{{ vm()?.originalTotalPrice | currency:vm()?.currency }}</span>
                      <strong>{{ vm()?.totalPrice | currency:vm()?.currency }}</strong>
                      <span style="color: var(--color-success); font-weight: bold;">(-{{ vm()?.discountPercent }}%)</span>
                    } @else {
                      {{ vm()?.totalPrice | currency:vm()?.currency }}
                    }
                    ({{ vm()?.totalNights }} {{ vm()?.totalNights === 1 ? 'noche' : 'noches' }})
                  </td>
                </tr>
              }
              <tr><th>Reserva manual</th><td>{{ vm()?.isManual ? 'Sí' : 'No' }}</td></tr>
              @if (vm()?.manualReservationId) {
                <tr><th>Manual ID</th><td>{{ vm()?.manualReservationId }}</td></tr>
              }
            </tbody>
          </table>
        </div>
      </article>
    </section>
  `
})
export class RdInfoPanelsComponent {
  readonly vm = input<any>(null);
  readonly fulfillment = input<FulfillmentItem[]>([]);
  readonly amenityFulfillment = input<FulfillmentItem[]>([]);
  /** Solo staff puede marcar/reabrir cumplimiento (huésped ve el checklist en solo lectura). */
  readonly canToggle = input<boolean>(true);
  readonly toggleFulfillment = output<{ kind: 'special_request' | 'amenity'; label: string; status: 'pending' | 'fulfilled' }>();

  /** Only persisted late modes render this row; normal departures stay unchanged. */
  isExtendedDeparture(mode: string | null | undefined): boolean {
    return mode === 'late_approved' || mode === 'late_courtesy';
  }

  lateCheckoutModeLabel(mode: string | null | undefined): string {
    return mode === 'late_approved' ? 'Aprobado' : 'Cortesía';
  }
}
