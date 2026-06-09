import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-active-amenities-summary',
  templateUrl: './active-amenities-summary.html',
  styleUrl: './active-amenities-summary.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ActiveAmenitiesSummaryComponent {
  readonly items = input.required<string[]>();
}
