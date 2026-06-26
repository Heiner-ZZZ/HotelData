import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { mapAmenities, mapAmenitiesPayload } from '../../mappers/amenities.mapper';
import type { AmenitiesDto } from '../../models/amenities.dto';
import { AmenitiesApiService } from '../../services/amenities-api.service';
import { ActiveAmenitiesSummaryComponent } from '../../components/active-amenities-summary/active-amenities-summary';
import { AmenityCategoryPanelComponent } from '../../components/amenity-category-panel/amenity-category-panel';

@Component({
  selector: 'app-amenities-page',
  imports: [
    ActiveAmenitiesSummaryComponent,
    AmenityCategoryPanelComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
  ],
  templateUrl: './amenities-page.html',
  styleUrl: './amenities-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AmenitiesPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(AmenitiesApiService);
  private readonly propertyCtx = inject(PropertyContextService);

  // ── Route params as signals ──
  readonly selectedPropId = toSignal(
    this.route.queryParamMap.pipe(
      map((params) => Number(params.get('prop_id') ?? '0')),
      distinctUntilChanged(),
    ),
    { initialValue: 0 }
  );

  readonly selectedRoomTypeId = signal('');

  // ── Declarative data fetching with httpResource ──
  // Auto-fetches when prop_id or room_type changes.
  // Returns undefined URL = skip fetch (empty state).
  private readonly amenitiesResource = httpResource<AmenitiesDto>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    return `/api/management/amenities?prop_id=${propId}&room_type_id=${this.selectedRoomTypeId()}`;
  });

  // ── Derived state ──
  readonly viewState = computed(() => {
    if (!this.selectedPropId()) return 'empty' as const;
    if (this.amenitiesResource.isLoading()) return 'loading' as const;
    if (this.amenitiesResource.error()) return 'error' as const;
    if (!this.amenitiesResource.hasValue()) return 'loading' as const;
    return 'success' as const;
  });

  readonly viewModel = computed(() => {
    const dto = this.amenitiesResource.value();
    return dto ? mapAmenities(dto) : null;
  });

  readonly selectedLabel = computed(() => this.viewModel()?.hotelName ?? '');

  // ── Mutable state ──
  readonly selectedAmenities = signal<string[]>([]);
  readonly amenityPrices = signal<Map<string, number>>(new Map());
  readonly message = signal('');
  readonly errorMessage = signal('');

  /** Initialize prices map from catalog when amenities data loads. */
  private _initPricesFromCatalog() {
    const vm = this.viewModel();
    if (!vm) return;
    const prices = new Map<string, number>();
    for (const cat of vm.categories) {
      for (const item of cat.items) {
        if (item.unitPrice && item.unitPrice > 0) {
          prices.set(item.label, item.unitPrice);
        }
      }
    }
    this.amenityPrices.set(prices);
  }

  /** Update price for an amenity label. $0 = incluido en tarifa. */
  updateAmenityPrice(label: string, value: string) {
    const num = parseFloat(value);
    const prices = new Map(this.amenityPrices());
    prices.set(label, isNaN(num) ? 0 : num);
    this.amenityPrices.set(prices);
  }

  /** Get price for an amenity, returns 0 if not in price map (incluido). */
  getAmenityPrice(label: string): number {
    return this.amenityPrices().get(label) ?? 0;
  }

  // ── Form fields as plain signals (no FormBuilder) ──
  readonly search = signal('');
  readonly manualAmenity = signal('');

  // ── Derived computations ──
  readonly selectedLookup = computed(() => new Set(this.selectedAmenities().map((item) => item.toLowerCase())));

  readonly filteredCategories = computed(() => {
    const vm = this.viewModel();
    const q = this.search().trim().toLowerCase();
    if (!vm) return [];
    const categories = vm.categories;
    if (!q) return categories;
    return categories
      .map((cat) => ({
        ...cat,
        items: cat.items.filter((item) => item.label.toLowerCase().includes(q))
      }))
      .filter((cat) => cat.items.length);
  });

  readonly selectedRoomName = computed(() => {
    const vm = this.viewModel();
    const rtId = this.selectedRoomTypeId();
    if (!vm || !rtId) return '';
    return vm.roomTypes.find((rt) => rt.roomTypeId === rtId)?.name ?? rtId;
  });

  constructor() {
    // Sync active amenities when fresh data arrives from httpResource
    effect(() => {
      const dto = this.amenitiesResource.value();
      if (dto) {
        this.selectedAmenities.set(dto.amenities.active_amenities ?? []);
        this.message.set('');
        this.errorMessage.set('');
        const label = this.selectedLabel();
        if (label) this.propertyCtx.setProperty(this.selectedPropId(), label);
        this._initPricesFromCatalog();
      }
    });
    effect(() => {
      if (!this.selectedPropId()) this.propertyCtx.clear();
    });
  }

  onPropSelected(event: { propId: number; label: string }) {
    if (!event.propId) this.propertyCtx.clear();
    else this.propertyCtx.setProperty(event.propId, event.label || `Propiedad #${event.propId}`);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null }
    });
  }

  onRoomTypeChange(event: Event): void {
    this.selectedRoomTypeId.set((event.target as HTMLSelectElement).value);
  }

  toggleAmenity(label: string) {
    const normalized = label.trim();
    if (!normalized) {
      return;
    }
    const current = this.selectedAmenities();
    const lookup = new Set(current.map((item) => item.toLowerCase()));
    if (lookup.has(normalized.toLowerCase())) {
      this.selectedAmenities.set(current.filter((item) => item.toLowerCase() !== normalized.toLowerCase()));
    } else {
      this.selectedAmenities.set([...current, normalized]);
    }
  }

  addManualAmenity(): void {
    const value = this.manualAmenity().trim();
    if (!value) return;
    this.toggleAmenity(value);
    this.manualAmenity.set('');
  }

  saveAmenities(): void {
    const current = this.viewModel();
    if (!current) return;
    this.api
      .saveAmenities(mapAmenitiesPayload(
        current.propId,
        this.selectedAmenities(),
        this.selectedRoomTypeId(),
        this.amenityPrices(),
      ))
      .subscribe({
        next: (fresh) => {
          this.selectedAmenities.set(fresh.activeAmenities);
          this.selectedRoomTypeId.set('');
          this.message.set('Servicios actualizados');
          this.errorMessage.set('');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible guardar los servicios.');
          this.message.set('');
        }
      });
  }
}