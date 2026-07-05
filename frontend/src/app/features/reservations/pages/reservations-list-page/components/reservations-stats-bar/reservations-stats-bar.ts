import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import type { ReservationStats } from '../../../../models/reservations.model';

@Component({
  selector: 'app-reservations-stats-bar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './reservations-stats-bar.html',
  styleUrl: './reservations-stats-bar.scss',
})
export class ReservationsStatsBarComponent {
  readonly stats = input<ReservationStats | null>(null);
  readonly statsLoading = input(false);
  readonly currentStatusFilter = input('');

  readonly filterPending = output<void>();
}
