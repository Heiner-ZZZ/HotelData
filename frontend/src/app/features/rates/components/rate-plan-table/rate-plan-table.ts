import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import type { RatePlanItem } from '../../models/rates.model';

@Component({
  selector: 'app-rate-plan-table',
  templateUrl: './rate-plan-table.html',
  styleUrl: './rate-plan-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RatePlanTableComponent {
  readonly items = input<RatePlanItem[]>([]);
  /** Map of room_type_id → short room number for display */
  readonly roomTypeNumbers = input<Record<string, string>>({});

  readonly editPlan = output<RatePlanItem>();
  readonly deletePlan = output<string>();
}