import { ChangeDetectionStrategy, Component, input } from '@angular/core';

export interface KpiData {
  hotelLabel: string;
  profileBadge?: string;
  ratePlansCount: number;
  calendarCount: number;
  promotionsCount: number;
  couponsCount: number;
}

@Component({
  selector: 'app-rate-kpi-grid',
  imports: [],
  templateUrl: './rate-kpi-grid.html',
  styleUrl: './rate-kpi-grid.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RateKpiGridComponent {
  readonly data = input.required<KpiData>();
}
