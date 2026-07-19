import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { HttpClient } from '@angular/common/http';
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
import type { AmenitiesViewModel } from '../../models/amenities.model';
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
  private readonly http = inject(HttpClient);
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
  readonly amenitiesResource = httpResource<AmenitiesViewModel>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    return `/api/management/amenities?prop_id=${propId}&room_type_id=${this.selectedRoomTypeId()}`;
  }, {
    parse: (res) => mapAmenities(res as AmenitiesDto),
  });

  // ── Derived state ──
  readonly viewState = computed(() => {
    if (!this.selectedPropId()) return 'empty' as const;
    if (this.amenitiesResource.isLoading()) return 'loading' as const;
    if (this.amenitiesResource.error()) return 'error' as const;
    if (!this.amenitiesResource.hasValue()) return 'loading' as const;
    return 'success' as const;
  });

  readonly selectedLabel = computed(() => this.amenitiesResource.value()?.hotelName ?? '');

  // ── Mutable state ──
  readonly selectedAmenities = signal<string[]>([]);
  readonly amenityPrices = signal<Map<string, number>>(new Map());
  readonly message = signal('');
  readonly errorMessage = signal('');

  /** Initialize prices map from catalog when amenities data loads. */
  private _initPricesFromCatalog() {
    const vm = this.amenitiesResource.value();
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
    const vm = this.amenitiesResource.value();
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
    const vm = this.amenitiesResource.value();
    const rtId = this.selectedRoomTypeId();
    if (!vm || !rtId) return '';
    return vm.roomTypes.find((rt) => rt.roomTypeId === rtId)?.name ?? rtId;
  });

  constructor() {
    // Sync active amenities when fresh data arrives from httpResource
    effect(() => {
      const vm = this.amenitiesResource.value();
      if (vm) {
        this.selectedAmenities.set(vm.activeAmenities ?? []);
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
    // Sync httpResource → writable photoList signal (needed for optimistic delete)
    effect(() => {
      const data = this.photoListRes.value();
      if (data?.photos) {
        this.photoList.set(data.photos);
      }
    });
    // Clear photoList when amenity/prop selection becomes empty
    effect(() => {
      if (!this.photoAmenity() || !this.selectedPropId()) {
        this.photoList.set([]);
      }
    });
    // Sync room photo list from httpResource
    effect(() => {
      const data = this.roomPhotoListRes.value();
      if (data?.images) {
        this.roomPhotoList.set(data.images);
      }
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
    const current = this.amenitiesResource.value();
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

  // ═══ Photo upload ═══
  readonly photoAmenity = signal('');
  readonly photoUploading = signal(false);
  readonly photoMessage = signal('');
  readonly photoMsgType = signal<'success' | 'error' | ''>('');
  readonly photoList = signal<{ photo_id: string; amenity_label: string; url: string }[]>([]);

  /** httpResource for GET — reactive, auto-fetches when amenity/prop changes. */
  private readonly photoListRes = httpResource<
    { ok: boolean; photos: { photo_id: string; amenity_label: string; url: string }[] }
  >(() => {
    const label = this.photoAmenity();
    const propId = this.selectedPropId();
    if (!label || !propId) return undefined;
    return `/api/management/amenities/photos?prop_id=${propId}&amenity_label=${encodeURIComponent(label)}`;
  });

  readonly photoLoading = computed(() => this.photoListRes.isLoading());

  onPhotoAmenityChange(label: string): void {
    this.photoAmenity.set(label);
    this.photoMessage.set('');
    this.photoMsgType.set('');
  }

  deletePhoto(photoId: string): void {
    const prev = this.photoList();
    this.photoList.update((list) => list.filter((p) => p.photo_id !== photoId));
    this.http
      .delete(`/api/management/amenities/photos/${photoId}`, { withCredentials: true })
      .subscribe({
        error: (err) => {
          this.photoList.set(prev);
          this.photoMessage.set(err.error?.message || 'Error al eliminar la foto.');
          this.photoMsgType.set('error');
        },
      });
  }

  onPhotoFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !this.photoAmenity() || !this.selectedPropId()) return;

    const formData = new FormData();
    formData.append('file', file);
    this.photoUploading.set(true);
    this.photoMessage.set('');
    this.photoMsgType.set('');

    this.http
      .post<{ ok: boolean; photo_id: string; message: string }>(
        `/api/management/amenities/photos?prop_id=${this.selectedPropId()}&amenity_label=${encodeURIComponent(this.photoAmenity())}`,
        formData,
        { withCredentials: true },
      )
      .subscribe({
        next: (resp) => {
          const ok = resp.ok;
          this.photoMessage.set(ok ? 'Foto subida correctamente.' : (resp.message || 'Error.'));
          this.photoMsgType.set(ok ? 'success' : 'error');
          this.photoUploading.set(false);
          input.value = '';
          if (ok) this.photoListRes.reload();
        },
        error: (err) => {
          this.photoMessage.set(err.error?.message || 'Error al subir la foto.');
          this.photoMsgType.set('error');
          this.photoUploading.set(false);
          input.value = '';
        },
      });
  }

  // ═══ Room-type photo upload ═══
  readonly roomPhotoRoomType = signal('');
  readonly roomPhotoUploading = signal(false);
  readonly roomPhotoMessage = signal('');
  readonly roomPhotoMsgType = signal<'success' | 'error' | ''>('');
  readonly roomPhotoList = signal<{ image_url: string; title: string; room_type_id: string }[]>([]);

  private readonly roomPhotoListRes = httpResource<
    { ok: boolean; images: { image_url: string; title: string; room_type_id: string }[] }
  >(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    return `/api/public/hotels/${propId}/room-images`;
  });

  readonly filteredRoomPhotos = computed(() => {
    const rt = this.roomPhotoRoomType();
    if (!rt) return [];
    return this.roomPhotoList().filter(p => p.room_type_id === rt);
  });

  readonly roomPhotoLoading = computed(() => this.roomPhotoListRes.isLoading());

  onRoomPhotoRoomTypeChange(roomTypeId: string): void {
    this.roomPhotoRoomType.set(roomTypeId);
    this.roomPhotoMessage.set('');
    this.roomPhotoMsgType.set('');
  }

  deleteRoomPhoto(imageUrl: string): void {
    const prev = this.roomPhotoList();
    this.roomPhotoList.update((list) => list.filter((p) => p.image_url !== imageUrl));
    this.http
      .delete(`/api/management/properties/${this.selectedPropId()}/room-types/images?image_url=${encodeURIComponent(imageUrl)}`, { withCredentials: true })
      .subscribe({
        error: (err) => {
          this.roomPhotoList.set(prev);
          this.roomPhotoMessage.set(err.error?.message || 'Error al eliminar la foto.');
          this.roomPhotoMsgType.set('error');
        },
      });
  }

  onRoomPhotoFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !this.roomPhotoRoomType() || !this.selectedPropId()) return;

    const formData = new FormData();
    formData.append('file', file);
    this.roomPhotoUploading.set(true);
    this.roomPhotoMessage.set('');
    this.roomPhotoMsgType.set('');

    this.http
      .post<{ ok?: boolean; image_url?: string; detail?: string }>(
        `/api/management/properties/${this.selectedPropId()}/room-types/images/upload?room_type_id=${encodeURIComponent(this.roomPhotoRoomType())}`,
        formData,
        { withCredentials: true },
      )
      .subscribe({
        next: (resp) => {
          const ok = !resp.detail;
          this.roomPhotoMessage.set(ok ? 'Foto subida correctamente.' : (resp.detail || 'Error.'));
          this.roomPhotoMsgType.set(ok ? 'success' : 'error');
          this.roomPhotoUploading.set(false);
          input.value = '';
          if (ok) this.roomPhotoListRes.reload();
        },
        error: (err) => {
          this.roomPhotoMessage.set(err.error?.detail || err.error?.message || 'Error al subir la foto.');
          this.roomPhotoMsgType.set('error');
          this.roomPhotoUploading.set(false);
          input.value = '';
        },
      });
  }
}