import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import type { AmenityCategoryViewModel } from '../../models/amenities.model';

@Component({
  selector: 'app-amenity-category-panel',
  templateUrl: './amenity-category-panel.html',
  styleUrl: './amenity-category-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AmenityCategoryPanelComponent {
  readonly category = input.required<AmenityCategoryViewModel>();
  readonly toggleAmenity = output<string>();
  readonly selectedLabels = input.required<Set<string>>();

  onToggle(label: string) {
    this.toggleAmenity.emit(label);
  }
}
