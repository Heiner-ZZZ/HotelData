import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { RateCalendarItem } from '../../models/rates.model';

@Component({
  selector: 'app-rate-calendar-table',
  standalone: true,
  imports: [StatusBadgeComponent],
  templateUrl: './rate-calendar-table.html',
  styleUrl: './rate-calendar-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RateCalendarTableComponent {
  readonly items = input.required<RateCalendarItem[]>();
}
