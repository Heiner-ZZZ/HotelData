import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import type { DateHistoryEntry } from '../../../../services/reservations-api.service';

@Component({
  selector: 'app-reservations-history-modal',
  standalone: true,
  imports: [DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './reservations-history-modal.html',
  styleUrl: './reservations-history-modal.scss',
})
export class ReservationsHistoryModalComponent {
  readonly show = input(false);
  readonly dates = input<DateHistoryEntry[]>([]);
  readonly loading = input(false);

  readonly close = output<void>();
  readonly selectDate = output<string>();
}
