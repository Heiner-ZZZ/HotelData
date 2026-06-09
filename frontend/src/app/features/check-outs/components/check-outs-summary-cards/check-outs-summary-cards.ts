import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-check-outs-summary-cards',
  templateUrl: './check-outs-summary-cards.html',
  styleUrl: './check-outs-summary-cards.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckOutsSummaryCardsComponent {
  readonly departuresToday = input.required<number>();
  readonly pendingCount = input.required<number>();
  readonly completedCount = input.required<number>();
  readonly cancelledOrNoShowCount = input.required<number>();
}
