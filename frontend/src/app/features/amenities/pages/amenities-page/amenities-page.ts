import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { HttpClient } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { ModeHighlightDirective } from '../../../../core/directives/mode-highlight.directive';
import { ToastService } from '../../../../shared/services/toast.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { mapAmenities, mapAmenitiesPayload } from '../../mappers/amenities.mapper';
import type { AmenitiesDto } from '../../models/amenities.dto';
import type { AmenitiesViewModel, SpecialRequestOptionView } from '../../models/amenities.model';
import { AmenitiesApiService } from '../../services/amenities-api.service';
import { ActiveAmenitiesSummaryComponent } from '../../components/active-amenities-summary/active-amenities-summary';
import { AmenityCategoryPanelComponent } from '../../components/amenity-category-panel/amenity-category-panel';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { DestroyRef } from '@angular/core';

// ─── Reglas de negocio implícitas por el nombre ───
// Una petición cuyo label ya nombra la regla no necesita toggle: el flag
// aplica automáticamente (ej. "Piso alto" → high_floor). Evita los toggles
// circulares del catálogo y mantiene la consistencia al guardar.

export function impliesPetRelated(label: string): boolean {
  return /mascota|pet/i.test(label);
}

export function impliesHighFloor(label: string): boolean {
  return /piso\s*alt|planta\s*alta|piso\s*elevad|high\s*floor/i.test(label);
}

export function impliesLateArrival(label: string): boolean {
  return /llegada\s*tard|llegada\s*noct|late\s*(arrival|check)/i.test(label);
}

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
    ModeHighlightDirective,
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
  private readonly toast = inject(ToastService);
  private readonly opMode = inject(OperationModeService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly destroyRef = inject(DestroyRef);

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

  // ═══ Explicit editing mode (mode-aware UI) ═══
  /** True while the user is actively editing services/prices. */
  readonly editing = signal(false);
  /** True while the "Nuevo servicio" composer is open (insert mode). */
  readonly composerOpen = signal(false);
  readonly manualPrice = signal('');
  /** Snapshot of the persisted state when the edit session began — used for dirty tracking and cancel. */
  private baseAmenities = signal<string[]>([]);
  private basePrices = signal<Map<string, number>>(new Map());

  /** Any pending change vs. the snapshot taken when editing began. */
  readonly dirty = computed(() => {
    const cur = new Set(this.selectedAmenities().map((s) => s.toLowerCase()));
    const base = new Set(this.baseAmenities().map((s) => s.toLowerCase()));
    if (cur.size !== base.size) return true;
    for (const s of base) if (!cur.has(s)) return true;
    const curPrices = this.amenityPrices();
    const basePrices = this.basePrices();
    if (curPrices.size !== basePrices.size) return true;
    for (const [k, v] of basePrices) if (curPrices.get(k) !== v) return true;
    return false;
  });

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

  /** Last resource payload we seeded the editable state from — prevents a
   *  save (which flips editing flags and re-runs the effect below) from
   *  clobbering freshly-persisted values with stale resource data. */
  private lastSeededVm: unknown = null;

  constructor() {
    // Sync active amenities when fresh data arrives from httpResource.
    // Only reseeds when the resource actually delivers a NEW payload; the
    // editing flags are read so the effect re-runs on edit/save transitions,
    // but a save must not overwrite its own fresh result with stale data.
    effect(() => {
      const vm = this.amenitiesResource.value();
      if (vm && vm !== this.lastSeededVm && !this.editing() && !this.requestsEditing()) {
        this.lastSeededVm = vm;
        this.selectedAmenities.set(vm.activeAmenities ?? []);
        this._seedRequestsFromCatalog();
        const label = this.selectedLabel();
        if (label) this.propertyCtx.setProperty(this.selectedPropId(), label);
        this._initPricesFromCatalog();
      }
    });
    effect(() => {
      if (!this.selectedPropId()) this.propertyCtx.clear();
    });
    // Clean up the transient mode when leaving the page.
    this.destroyRef.onDestroy(() => this.opMode.reset());
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
    this.cancelEditing();
    if (!event.propId) this.propertyCtx.clear();
    else this.propertyCtx.setProperty(event.propId, event.label || `Propiedad #${event.propId}`);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null }
    });
  }

  onRoomTypeChange(event: Event): void {
    this.cancelEditing();
    this.selectedRoomTypeId.set((event.target as HTMLSelectElement).value);
  }

  // ═══ Mode-aware interactions ═══

  /** Start an edit session: snapshot current state and switch the nav chip to "update". */
  startEditing(): void {
    if (this.editing()) return;
    this.baseAmenities.set([...this.selectedAmenities()]);
    this.basePrices.set(new Map(this.amenityPrices()));
    this.editing.set(true);
    this.opMode.setMode('update', 'Servicios');
  }

  /** Discard pending changes and return to read mode. */
  cancelEditing(): void {
    if (!this.editing()) {
      this.composerOpen.set(false);
      this.opMode.reset();
      return;
    }
    this.selectedAmenities.set([...this.baseAmenities()]);
    this.amenityPrices.set(new Map(this.basePrices()));
    this.editing.set(false);
    this.composerOpen.set(false);
    this.manualAmenity.set('');
    this.manualPrice.set('');
    this.opMode.reset();
  }

  /** Open the composer for a brand-new custom service → insert mode (ámbar). */
  openComposer(): void {
    this.composerOpen.set(true);
    this.manualPrice.set('');
    this.opMode.setMode('insert', 'Nuevo servicio');
  }

  /** Close the composer without adding → back to update (or read). */
  closeComposer(): void {
    this.composerOpen.set(false);
    this.manualPrice.set('');
    if (this.editing()) this.opMode.setMode('update', 'Servicios');
    else this.opMode.reset();
  }

  /**
   * Toggle a catalog service on/off. Removing a previously-persisted service
   * asks for confirmation and flips the chip to "delete" while the dialog is
   * open; newly-added (unsaved) services remove silently.
   */
  async toggleAmenity(label: string): Promise<void> {
    const normalized = label.trim();
    if (!normalized) return;

    const current = this.selectedAmenities();
    const lookup = new Set(current.map((item) => item.toLowerCase()));
    const wasSelected = lookup.has(normalized.toLowerCase());

    if (!wasSelected) {
      this.selectedAmenities.set([...current, normalized]);
      if (this.editing()) this.opMode.setMode('update', 'Servicios');
      return;
    }

    // Removing a service that exists in the persisted snapshot → confirm.
    const isPersisted = new Set(this.baseAmenities().map((s) => s.toLowerCase())).has(normalized.toLowerCase());
    if (isPersisted && this.editing()) {
      const ok = await this.confirmDialog.open({
        title: 'Quitar servicio',
        message: `¿Quitar «${normalized}» de los servicios activos?`,
        details: isPersisted
          ? ['Se eliminará de la oferta del hotel una vez guardes los cambios.', 'Puedes volver a seleccionarlo en cualquier momento.']
          : undefined,
        confirmLabel: 'Quitar',
        cancelLabel: 'Cancelar',
        variant: 'danger',
        mode: 'delete',
        modeDetail: normalized,
      });
      // The dialog clears its own transient mode on close (falling back to
      // route mode = read), so always re-assert the edit session mode — even
      // when the user cancels — or the chip would mismatch the UI state.
      if (this.editing()) this.opMode.setMode('update', 'Servicios');
      if (!ok) return;
    }

    this.selectedAmenities.set(current.filter((item) => item.toLowerCase() !== normalized.toLowerCase()));
    if (this.editing()) this.opMode.setMode('update', 'Servicios');
  }

  /** Add the typed custom service (insert mode) then return to update. */
  addManualAmenity(): void {
    const value = this.manualAmenity().trim();
    if (!value) return;
    const price = parseFloat(this.manualPrice());
    if (!Number.isNaN(price) && price > 0) {
      this.updateAmenityPrice(value, String(price));
    }
    this.toggleAmenity(value);
    this.manualAmenity.set('');
    this.manualPrice.set('');
    this.composerOpen.set(false);
    if (this.editing()) this.opMode.setMode('update', 'Servicios');
  }

  /** Remove an active service from the summary pill (delete confirm). */
  async removeActiveAmenity(label: string): Promise<void> {
    const ok = await this.confirmDialog.open({
      title: 'Quitar servicio',
      message: `¿Quitar «${label}» de los servicios activos?`,
      details: ['Se eliminará de la oferta del hotel una vez guardes los cambios.', 'Puedes volver a seleccionarlo en cualquier momento.'],
      confirmLabel: 'Quitar',
      cancelLabel: 'Cancelar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: label,
    });
    // Same re-assert as toggleAmenity: the dialog clears the transient slot on
    // close, so restore the edit-session mode regardless of the result.
    if (this.editing()) this.opMode.setMode('update', 'Servicios');
    if (!ok) return;
    this.selectedAmenities.set(this.selectedAmenities().filter((item) => item.toLowerCase() !== label.toLowerCase()));
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
          this.toast.success('Servicios actualizados');
          // End the edit session: snapshot becomes the new persisted state.
          this.baseAmenities.set([...fresh.activeAmenities]);
          this.basePrices.set(new Map(this.amenityPrices()));
          this.editing.set(false);
          this.composerOpen.set(false);
          this.manualPrice.set('');
          this.opMode.reset();
        },
        error: (error: ApiError) => {
          this.toast.error(error.message || 'No fue posible guardar los servicios.');
        }
      });
  }

  // ═══ Peticiones especiales tab ═══
  /** The route parameter is the source of truth and changes without recreating this page. */
  private readonly activeSection = toSignal(
    this.route.paramMap.pipe(map((params) => params.get('section') ?? 'servicios')),
    {
      initialValue:
        this.route.snapshot.paramMap.get('section')
        ?? this.route.snapshot.url[0]?.path
        ?? 'servicios',
    },
  );

  readonly activeTab = computed<'amenities' | 'requests'>(() =>
    this.activeSection() === 'especialsPeticions' ? 'requests' : 'amenities',
  );

  /** Navigate instead of only changing local state, so the browser URL identifies the section. */
  setActiveTab(tab: 'amenities' | 'requests'): void {
    if (this.activeTab() === tab) return;

    const path = tab === 'requests' ? 'especialsPeticions' : 'servicios';
    void this.router.navigate(['/management/amenities', path], {
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  /** Editable copy of the per-hotel special-requests catalog. */
  readonly requestOptions = signal<SpecialRequestOptionView[]>([]);
  readonly highFloorFrom = signal(3);
  readonly requestsEditing = signal(false);
  /** Helpers de reglas implícitas expuestos para el template. */
  readonly impliesPetRelated = impliesPetRelated;
  readonly impliesHighFloor = impliesHighFloor;
  readonly impliesLateArrival = impliesLateArrival;
  /** Labels con el panel "Reglas de negocio" expandido (colapsado por defecto). */
  readonly expandedRules = signal<Set<string>>(new Set());
  readonly requestsSaving = signal(false);
  readonly newRequestLabel = signal('');
  readonly newRequestPrice = signal('');
  private baseRequestOptions = signal<SpecialRequestOptionView[]>([]);
  private baseHighFloorFrom = signal(3);

  /** Seed the requests tab from the catalog when the resource loads. */
  private _seedRequestsFromCatalog() {
    const vm = this.amenitiesResource.value();
    if (!vm) return;
    const opts = vm.specialRequests.map((r) => ({ ...r }));
    this.requestOptions.set(opts);
    this.highFloorFrom.set(vm.highFloorFrom);
    // Keep the base snapshot in sync while in read mode so the dirty hint
    // only appears once the user actually edits the catalog.
    if (!this.requestsEditing()) {
      this.baseRequestOptions.set(opts.map((r) => ({ ...r })));
      this.baseHighFloorFrom.set(vm.highFloorFrom);
    }
  }

  readonly requestsDirty = computed(() => {
    const cur = this.requestOptions();
    const base = this.baseRequestOptions();
    if (cur.length !== base.length || this.highFloorFrom() !== this.baseHighFloorFrom()) return true;
    return cur.some((r, i) => {
      const b = base[i];
      return !b || r.label !== b.label || r.unitPrice !== b.unitPrice
        || r.petRelated !== b.petRelated || r.highFloor !== b.highFloor || r.lateArrival !== b.lateArrival;
    });
  });

  startRequestsEditing(): void {
    if (this.requestsEditing()) return;
    this.baseRequestOptions.set(this.requestOptions().map((r) => ({ ...r })));
    this.baseHighFloorFrom.set(this.highFloorFrom());
    this.requestsEditing.set(true);
    this.opMode.setMode('update', 'Peticiones especiales');
  }

  cancelRequestsEditing(): void {
    if (!this.requestsEditing()) {
      this.opMode.reset();
      return;
    }
    this.requestOptions.set(this.baseRequestOptions().map((r) => ({ ...r })));
    this.highFloorFrom.set(this.baseHighFloorFrom());
    this.requestsEditing.set(false);
    this.opMode.reset();
  }

  updateRequestPrice(label: string, value: string): void {
    const num = parseFloat(value);
    this.requestOptions.set(this.requestOptions().map((r) =>
      r.label === label ? { ...r, unitPrice: Number.isNaN(num) ? 0 : Math.max(0, num) } : r
    ));
  }

  toggleRequestFlag(label: string, flag: 'petRelated' | 'highFloor' | 'lateArrival'): void {
    this.requestOptions.set(this.requestOptions().map((r) =>
      r.label === label ? { ...r, [flag]: !r[flag] } : r
    ));
  }

  toggleRulesExpanded(label: string): void {
    this.expandedRules.update((s) => {
      const next = new Set(s);
      if (next.has(label)) { next.delete(label); } else { next.add(label); }
      return next;
    });
  }

  isRulesExpanded(label: string): boolean {
    return this.expandedRules().has(label);
  }

  removeRequest(label: string): void {
    this.requestOptions.set(this.requestOptions().filter((r) => r.label !== label));
  }

  addRequest(): void {
    const label = this.newRequestLabel().trim();
    if (!label) return;
    const price = parseFloat(this.newRequestPrice());
    if (this.requestOptions().some((r) => r.label.toLowerCase() === label.toLowerCase())) return;
    this.requestOptions.set([
      ...this.requestOptions(),
      { label, unitPrice: Number.isNaN(price) ? 0 : Math.max(0, price), chargeable: !Number.isNaN(price) && price > 0, petRelated: false, highFloor: false, lateArrival: false },
    ]);
    this.newRequestLabel.set('');
    this.newRequestPrice.set('');
  }

  setHighFloorFrom(value: string): void {
    const num = parseInt(value, 10);
    this.highFloorFrom.set(Number.isNaN(num) ? 1 : Math.max(1, num));
  }

  saveRequests(): void {
    const current = this.amenitiesResource.value();
    if (!current) return;
    this.requestsSaving.set(true);
    this.api.saveSpecialRequests({
      prop_id: current.propId,
      special_requests: this.requestOptions().map((r) => ({
        label: r.label,
        unit_price: r.unitPrice,
        flags: [
          ...(r.petRelated || impliesPetRelated(r.label) ? ['pet_related'] : []),
          ...(r.highFloor || impliesHighFloor(r.label) ? ['high_floor'] : []),
          ...(r.lateArrival || impliesLateArrival(r.label) ? ['late_arrival'] : []),
          ...(r.chargeable ? ['chargeable'] : []),
        ],
      })),
      high_floor_from: this.highFloorFrom(),
    }).subscribe({
      next: (fresh) => {
        this.requestOptions.set((fresh.special_requests ?? []).map((r) => ({
          label: r.label, unitPrice: r.unit_price, chargeable: r.chargeable,
          petRelated: r.pet_related, highFloor: r.high_floor, lateArrival: r.late_arrival,
        })));
        this.highFloorFrom.set(fresh.high_floor_from ?? 3);
        this.baseRequestOptions.set(this.requestOptions().map((r) => ({ ...r })));
        this.baseHighFloorFrom.set(this.highFloorFrom());
        this.requestsEditing.set(false);
        this.requestsSaving.set(false);
        this.opMode.reset();
        this.toast.success('Peticiones especiales actualizadas');
      },
      error: (error: ApiError) => {
        this.requestsSaving.set(false);
        this.toast.error(error.message || 'No fue posible guardar las peticiones.');
      },
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