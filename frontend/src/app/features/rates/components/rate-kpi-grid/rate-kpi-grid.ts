import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { InfoTooltipComponent } from '../../../../shared/ui/info-tooltip/info-tooltip.component';

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
  imports: [InfoTooltipComponent],
  templateUrl: './rate-kpi-grid.html',
  styleUrl: './rate-kpi-grid.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RateKpiGridComponent {
  readonly data = input.required<KpiData>();
}
