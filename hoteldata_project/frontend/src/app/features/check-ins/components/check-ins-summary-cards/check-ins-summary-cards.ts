import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-check-ins-summary-cards',
  templateUrl: './check-ins-summary-cards.html',
  styleUrl: './check-ins-summary-cards.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckInsSummaryCardsComponent {
  readonly arrivalsToday = input.required<number>();
  readonly pendingCount = input.required<number>();
  readonly completedCount = input.required<number>();
  readonly cancelledOrNoShowCount = input.required<number>();
}
