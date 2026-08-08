import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { amenityIcon } from '../../utils/amenity-icons';

@Component({
  selector: 'app-active-amenities-summary',
  templateUrl: './active-amenities-summary.html',
  styleUrl: './active-amenities-summary.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ActiveAmenitiesSummaryComponent {
  readonly items = input.required<string[]>();
  /** Price per amenity label (0 = included). */
  readonly prices = input<Map<string, number>>(new Map());
  /** When true each pill shows a remove button (edit mode). */
  readonly removable = input(false);
  readonly remove = output<string>();

  getIcon(label: string): string {
    return amenityIcon(label);
  }

  getPrice(label: string): number {
    return this.prices().get(label) ?? 0;
  }

  onRemove(label: string): void {
    this.remove.emit(label);
  }
}
