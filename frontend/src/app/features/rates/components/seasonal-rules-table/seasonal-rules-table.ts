import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export interface SeasonalRuleRow {
  ruleId: string;
  name: string;
  ratePlanId: string;
  startDate: string;
  endDate: string;
  rangeLabel: string;
  priceOverride: number;
}

@Component({
  selector: 'app-seasonal-rules-table',
  imports: [],
  templateUrl: './seasonal-rules-table.html',
  styleUrl: './seasonal-rules-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SeasonalRulesTableComponent {
  readonly rules = input<SeasonalRuleRow[]>([]);
  readonly editRule = output<SeasonalRuleRow>();
  readonly deleteRule = output<string>();
}
