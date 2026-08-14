import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { STAY_CHECKED_IN, STAY_CHECKED_OUT, STAY_NO_SHOW } from '../../../../reservations/utils/reservation-status.util';

@Component({
  selector: 'app-co-header',
  standalone: true,
  imports: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="co-header">
      <div>
        <div class="co-eyebrow">
          @if (stayStatus() === STAY_CHECKED_OUT) {
            <span class="co-badge completed">Check-Out Completado</span>
          } @else if (stayStatus() === STAY_NO_SHOW) {
            <span class="co-badge noshow">No-show</span>
          } @else if (stayStatus() !== STAY_CHECKED_IN) {
            <span class="co-badge blocked">Sin check-in</span>
          } @else {
            <span class="co-badge in-house">In House</span>
          }
          @if (folio()) { <span class="co-folio-code">Folio #{{ folio() }}</span> }
        </div>
        <h1>Check-Out &middot; {{ guestName() }}</h1>
        <p class="co-subtitle">
          Hab. {{ roomLabel() }} &mdash;
          {{ totalNights() }} noche{{ totalNights() !== 1 ? 's' : '' }} &mdash;
          {{ checkInDate() }} &rarr; {{ checkOutDate() }}
        </p>
      </div>
    </div>
  `
})
export class CoHeaderComponent {
  readonly stayStatus = input<string>('');
  readonly folio = input<string>('');
  readonly guestName = input<string>('');
  readonly roomLabel = input<string>('');
  readonly totalNights = input(0);
  readonly checkInDate = input<string>('');
  readonly checkOutDate = input<string>('');
  protected readonly STAY_CHECKED_OUT = STAY_CHECKED_OUT;
  protected readonly STAY_CHECKED_IN = STAY_CHECKED_IN;
  protected readonly STAY_NO_SHOW = STAY_NO_SHOW;
}
