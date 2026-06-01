import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { RatePlanItem } from '../../models/rates.model';

@Component({
  selector: 'app-rate-plan-table',
  standalone: true,
  imports: [StatusBadgeComponent],
  templateUrl: './rate-plan-table.html',
  styleUrl: './rate-plan-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RatePlanTableComponent {
  readonly items = input.required<RatePlanItem[]>();
}
