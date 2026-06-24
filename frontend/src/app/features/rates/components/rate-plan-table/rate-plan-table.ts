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

  readonly editPlan = output<RatePlanItem>();
  readonly deletePlan = output<string>();
}