import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-rd-info-panels',
  standalone: true,
  imports: [CurrencyPipe],
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
              <tr><th>Ocupación</th><td>{{ vm()?.occupancyLabel }}</td></tr>
              <tr><th>Comentario</th><td>{{ vm()?.comment }}</td></tr>
              @if (vm()?.specialRequests?.length > 0) {
                <tr><th>Peticiones</th><td>
                  <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    @for (req of vm()?.specialRequests; track req) {
                      <span style="background: var(--surface-2); padding: 4px 8px; border-radius: 4px; font-size: 0.85em; color: var(--text-2);">{{ req }}</span>
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
}
