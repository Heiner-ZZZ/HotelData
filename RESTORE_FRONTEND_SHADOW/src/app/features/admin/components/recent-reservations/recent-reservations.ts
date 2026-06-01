import { Component, input } from '@angular/core';

import { formatDateTime } from '../../../../shared/utils/date-format.util';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';

@Component({
  selector: 'app-recent-reservations',
  standalone: true,
  imports: [StatusBadgeComponent],
  templateUrl: './recent-reservations.html',
  styleUrl: './recent-reservations.scss'
})
export class RecentReservationsComponent {
  readonly execution = input<{
    executionId: string;
    status: string;
    executedAt: string;
  } | null>(null);

  formatDate(value: string) {
    return formatDateTime(value);
  }
}
