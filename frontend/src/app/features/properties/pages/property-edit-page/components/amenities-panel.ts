import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';

export interface AmenityCategory {
  category: string;
  items: { label: string }[];
}

@Component({
  selector: 'app-amenities-panel',
  templateUrl: './amenities-panel.html',
  styleUrl: './amenities-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AmenitiesPanelComponent {
  readonly amenities = input<string[]>([]);
  readonly amenityCatalog = input<AmenityCategory[]>([]);
  readonly amenitiesChange = output<string[]>();

  readonly showCatalog = signal(false);
  readonly catalogSearch = signal('');

  readonly catalogCount = computed(() => this.amenities().length);

  toggleCatalog() {
    this.showCatalog.set(!this.showCatalog());
    this.catalogSearch.set('');
  }

  removeAmenity(label: string) {
    this.amenitiesChange.emit(this.amenities().filter((a) => a !== label));
  }

  toggleAmenityFromCatalog(label: string) {
    const current = this.amenities();
    const normalized = label.trim();
    if (!normalized) return;
    const lookup = new Set(current.map((a) => a.toLowerCase()));
    if (lookup.has(normalized.toLowerCase())) {
      this.amenitiesChange.emit(current.filter((a) => a.toLowerCase() !== normalized.toLowerCase()));
    } else {
      this.amenitiesChange.emit([...current, normalized]);
    }
  }

  readonly filteredCatalog = computed(() => {
    const catalog = this.amenityCatalog();
    if (!catalog.length) return [];
    const search = this.catalogSearch().toLowerCase().trim();
    return catalog
      .map((cat) => ({
        ...cat,
        items: search ? cat.items.filter((item) => item.label.toLowerCase().includes(search)) : cat.items,
      }))
      .filter((cat) => cat.items.length > 0);
  });

  isAmenitySelected(label: string): boolean {
    return this.amenities().some((a) => a.toLowerCase() === label.toLowerCase());
  }
}
