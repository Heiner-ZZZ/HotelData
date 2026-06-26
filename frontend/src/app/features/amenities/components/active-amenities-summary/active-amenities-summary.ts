import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { amenityIcon } from '../../utils/amenity-icons';

@Component({
  selector: 'app-active-amenities-summary',
  templateUrl: './active-amenities-summary.html',
  styleUrl: './active-amenities-summary.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ActiveAmenitiesSummaryComponent {
  readonly items = input.required<string[]>();

  getIcon(label: string): string {
    return amenityIcon(label);
  }
}
