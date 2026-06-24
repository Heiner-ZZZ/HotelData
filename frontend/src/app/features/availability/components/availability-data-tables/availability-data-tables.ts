import { ChangeDetectionStrategy, Component, input, ViewEncapsulation } from '@angular/core';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';

import type { AvailabilityInventoryItem, AvailabilityBlackoutItem } from '../../models/availability.model';

@Component({
  selector: 'app-availability-data-tables',
  imports: [EmptyStateComponent],
  templateUrl: './availability-data-tables.html',
  styleUrl: '../../pages/availability-page/availability-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class AvailabilityDataTablesComponent {
  readonly inventoryItems = input<AvailabilityInventoryItem[]>([]);
  readonly availabilityBlocks = input<AvailabilityBlackoutItem[]>([]);
  readonly blackoutItems = input<AvailabilityBlackoutItem[]>([]);

  /** Return an occupancy badge class based on the percentage. */
  occupancyBadgeClass(pct: number): string {
    if (pct < 0) return 'badge';
    if (pct < 30) return 'badge badge-success';
    if (pct < 60) return 'badge badge-warning';
    return 'badge badge-danger';
  }
}
