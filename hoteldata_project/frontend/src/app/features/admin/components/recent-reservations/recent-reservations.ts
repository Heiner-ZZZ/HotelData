import { Component, input } from '@angular/core';

import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { formatDateTime } from '../../../../shared/utils/date-format.util';

@Component({
  selector: 'app-recent-reservations',
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
