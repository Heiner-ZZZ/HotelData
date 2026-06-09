import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import type { PolicySummaryItem } from '../../models/policies.model';

@Component({
  selector: 'app-policy-summary-cards',
  templateUrl: './policy-summary-cards.html',
  styleUrl: './policy-summary-cards.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PolicySummaryCardsComponent {
  readonly items = input.required<PolicySummaryItem[]>();
}
