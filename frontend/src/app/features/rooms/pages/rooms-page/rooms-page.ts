import { ChangeDetectionStrategy, ChangeDetectorRef, Component, computed, DestroyRef, effect, inject, NgZone, signal, ViewEncapsulation } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { FeatureCategory, RoomTypeItem, RoomsViewModel } from '../../models/rooms.model';
import { RoomsApiService } from '../../services/rooms-api.service';
import { RoomTypeTableComponent } from '../../components/room-type-table/room-type-table';
import { AiSuggestDirective } from '../../../../core/directives/ai-suggest.directive';
import { KpiApiService, type TopHotelRoomsItem } from '../../../../shared/services/kpi-api.service';
import { RpKpiGridComponent } from './partials/rp-kpi-grid';
import { RpCreateFormComponent } from './partials/rp-create-form';
import { RpTablesComponent } from './partials/rp-tables';
import { RpDeleteModalComponent } from './partials/rp-delete-modal';
import { RpEditModalComponent } from './partials/rp-edit-modal';

@Component({
  selector: 'app-rooms-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    KpiChartComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
    RpKpiGridComponent,
    RpCreateFormComponent,
    RpTablesComponent,
    RpDeleteModalComponent,
    RpEditModalComponent
  ],
  templateUrl: './rooms-page.html',
  styleUrl: './rooms-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class RoomsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(RoomsApiService);
  private readonly kpiApi = inject(KpiApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  readonly propertyCtx = inject(PropertyContextService);
  private readonly toast = inject(ToastService);
  private readonly ngZone = inject(NgZone);
  private readonly cdr = inject(ChangeDetectorRef);

  // ── KPI data (top 5 hotels by rooms) ──
  readonly topHotels = signal<TopHotelRoomsItem[]>([]);
  readonly topHotelsState = signal<'loading' | 'success' | 'error'>('loading');

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<RoomsViewModel | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  /** 'existing' = seleccionar tipo existente, 'new' = escribir nuevo */
  readonly createMode = signal<'existing' | 'new'>('new');
  readonly selectedExistingRoomTypeId = signal('');

  readonly existingRoomTypes = computed(() => {
    const vm = this.viewModel();
    return vm?.roomTypes ?? [];
  });

  readonly createForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    maxAdults: [2, [Validators.required, Validators.min(1)]],
    maxChildren: [0, [Validators.required, Validators.min(0)]],
    baseCapacity: [2, [Validators.required, Validators.min(1)]],
    baseRate: [0, [Validators.min(0)]],
    isActive: [true],
    roomNumber: [''],
    floor: [''],
    view: [''],
    smoking: [false],
    accessible: [false],
  });

  onExistingTypeSelected(roomTypeId: string) {
    this.selectedExistingRoomTypeId.set(roomTypeId);
    const types = this.existingRoomTypes();
    const selected = types.find(t => t.id === roomTypeId);
    if (selected) {
      const parts = selected.capacityLabel.match(/(\d+)/g);
      this.createForm.patchValue({
        name: selected.name,
        description: selected.description === 'Sin descripción' ? '' : selected.description,
        maxAdults: parts && parts.length >= 2 ? Number(parts[1]) : 2,
        maxChildren: parts && parts.length >= 3 ? Number(parts[2]) : 0,
        baseCapacity: parts ? Number(parts[0]) : 2,
        isActive: true,
        view: selected.view || '',
        smoking: selected.smoking ?? false,
        accessible: selected.accessible ?? false,
      });
    }
  }

  setCreateMode(mode: 'existing' | 'new') {
    this.createMode.set(mode);
    if (mode === 'new') {
      this.selectedExistingRoomTypeId.set('');
      this.createForm.patchValue({
        name: '',
        description: '',
        maxAdults: 2,
        maxChildren: 0,
        baseCapacity: 2,
        baseRate: 0,
        isActive: true,
        roomNumber: '',
        floor: '',
        view: '',
        smoking: false,
        accessible: false,
      });
    }
  }

  readonly editForm = this.formBuilder.nonNullable.group({
    roomTypeId: ['', [Validators.required]],
    name: ['', [Validators.required]],
    description: [''],
    maxAdults: [2, [Validators.required, Validators.min(1)]],
    maxChildren: [0, [Validators.required, Validators.min(0)]],
    baseCapacity: [2, [Validators.required, Validators.min(1)]],
    baseRate: [0, [Validators.min(0)]],
    isActive: [true],
    roomNumber: [''],
    floor: [''],
    view: [''],
    smoking: [false],
    accessible: [false],
  });

  readonly showEditModal = signal(false);
  readonly savingEdit = signal(false);
  readonly showDeleteConfirm = signal(false);
  readonly deleteTargetId = signal('');
  readonly deleteTargetName = signal('');
  readonly deleting = signal(false);

  /* ── Room Features ── */
  readonly featureCatalog = signal<FeatureCategory[]>([]);
  readonly selectedFeatures = signal<Set<string>>(new Set());
  readonly featurePrices = signal<Map<string, number>>(new Map());
  readonly editingRoomTypeName = signal('');
  readonly editingRoomTypeId = signal('');
  readonly featurePanelOpen = signal(true);
  readonly featureSearchQuery = signal('');

  /** Bound function references for passing to partial components */
  readonly isFeatureSelectedFn = (label: string) => this.isFeatureSelected(label);
  readonly getFeaturePriceFn = (label: string) => this.getFeaturePrice(label);

  /** Filtered feature catalog based on search query (matches by label or category). */
  readonly filteredFeatureCatalog = computed(() => {
    const query = this.featureSearchQuery().toLowerCase().trim();
    const catalog = this.featureCatalog();
    if (!query) return catalog;
    return catalog
      .map((cat) => ({
        ...cat,
        items: cat.items.filter(
          (feat) =>
            feat.label.toLowerCase().includes(query) ||
            cat.category.toLowerCase().includes(query),
        ),
      }))
      .filter((cat) => cat.items.length > 0);
  });

  constructor() {
    // Carga por query param (navegación manual con prop_id en URL)
    this.route.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '0')),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe((propId) => this.loadRooms(propId));

    // Auto-carga en modo single-hotel
    effect(() => {
      if (this.propertyCtx.ready() && this.propertyCtx.singleHotelMode()) {
        const propId = this.propertyCtx.currentPropId();
        if (propId && this.selectedPropId() !== propId) {
          this.loadRooms(propId);
        }
      }
    });

    // Load top hotels KPI
    this.kpiApi.getTopHotelsByRooms(5).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res) => { this.topHotels.set(res.items); this.topHotelsState.set('success'); },
      error: (err) => { console.error('[Rooms] Failed to load top hotels KPI', err); this.topHotelsState.set('error'); },
    });
  }

  private loadRooms(propId: number) {
    this.viewState.set('loading');
    this.message.set('');
    this.errorMessage.set('');

    if (propId > 0) {
      this.api.getRooms(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (rooms) => {
          if (rooms) {
            this.viewModel.set(rooms);
            this.selectedPropId.set(rooms.propId);
            this.selectedLabel.set(rooms.hotelName);
            this.viewState.set('success');
            this.propertyCtx.setProperty(rooms.propId, rooms.hotelName);
          } else {
            this.viewModel.set(null);
            this.viewState.set('empty');
            this.propertyCtx.clear();
          }
        },
        error: (err) => { console.error('[Rooms] Failed to load rooms', err); this.viewState.set('error'); },
      });
    } else {
      this.viewModel.set(null);
      this.viewState.set('empty');
      this.propertyCtx.clear();
    }
  }

  onPropSelected(event: { propId: number; label: string }) {
    if (!event.propId) this.propertyCtx.clear();
    else this.propertyCtx.setProperty(event.propId, event.label || `Propiedad #${event.propId}`);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null }
    });
  }

  startEdit(roomType: RoomTypeItem) {
    // Defer form manipulation to next VM turn to avoid NG01002
    this.ngZone.runOutsideAngular(() => {
      setTimeout(() => {
        const parts = roomType.capacityLabel.match(/(\d+)/g);
        this.editForm.setValue({
          roomTypeId: roomType.id,
          name: roomType.name,
          description: roomType.description === 'Sin descripción' ? '' : roomType.description,
          maxAdults: parts && parts.length >= 2 ? Number(parts[1]) : 2,
          maxChildren: parts && parts.length >= 3 ? Number(parts[2]) : 0,
          baseCapacity: parts ? Number(parts[0]) : 2,
          baseRate: (roomType as any).baseRate ?? 0,
          isActive: roomType.activeLabel === 'Sí',
          roomNumber: roomType.roomNumber,
          floor: roomType.floor,
          view: roomType.view,
          smoking: roomType.smoking,
          accessible: roomType.accessible,
        });
        this.ngZone.run(() => {
          this.editingRoomTypeName.set(roomType.name);
          this.editingRoomTypeId.set(roomType.id);
          this.selectedFeatures.set(new Set(roomType.features.map(f => f.label)));
          const prices = new Map<string, number>();
          for (const f of roomType.features) {
            prices.set(f.label, f.unitPrice);
          }
          for (const cat of this.featureCatalog()) {
            for (const feat of cat.items) {
              if (!prices.has(feat.label) && feat.unitPrice) {
                prices.set(feat.label, feat.unitPrice);
              }
            }
          }
          this.featurePrices.set(prices);
          this.featurePanelOpen.set(true);
          this.showEditModal.set(true);
          this.cdr.markForCheck();
        });
      });
    });

    // Load feature catalog if not already loaded
    if (this.featureCatalog().length === 0) {
      this.api.getFeatureCatalog().pipe(
        takeUntilDestroyed(this.destroyRef)
      ).subscribe({
        next: (catalog) => this.featureCatalog.set(catalog),
        error: (err) => { console.error('[Rooms] Failed to load feature catalog', err); },
      });
    }
  }

  /** Sum of unit prices for all selected features (uses editable prices). */
  readonly selectedFeaturesTotal = computed(() => {
    const prices = this.featurePrices();
    const selected = this.selectedFeatures();
    let total = 0;
    for (const label of selected) {
      total += prices.get(label) ?? 0;
    }
    return total;
  });

  /** Toggle a feature on/off in the selected set. */
  toggleFeature(feature: string) {
    const current = new Set(this.selectedFeatures());
    if (current.has(feature)) {
      current.delete(feature);
    } else {
      current.add(feature);
    }
    this.selectedFeatures.set(current);
  }

  /** Check if a feature is selected. */
  isFeatureSelected(feature: string): boolean {
    return this.selectedFeatures().has(feature);
  }

  /** Count selected features. */
  readonly selectedFeatureCount = computed(() => this.selectedFeatures().size);

  updateFeaturePrice(label: string, value: string) {
    const num = parseFloat(value);
    const prices = new Map(this.featurePrices());
    prices.set(label, isNaN(num) ? 0 : num);
    this.featurePrices.set(prices);
  }

  /** Get current price for a feature label, falling back to catalog default. */
  getFeaturePrice(label: string): number {
    const prices = this.featurePrices();
    if (prices.has(label)) return prices.get(label)!;
    // Fall back to catalog default
    for (const cat of this.featureCatalog()) {
      const found = cat.items.find((f) => f.label === label);
      if (found?.unitPrice) return found.unitPrice;
    }
    return 0;
  }

  cancelEdit() {
    this.showEditModal.set(false);
    this.editForm.reset();
    this.selectedFeatures.set(new Set());
    this.featurePrices.set(new Map());
  }

  requestDelete(roomTypeId: string, name: string) {
    this.deleteTargetId.set(roomTypeId);
    this.deleteTargetName.set(name);
    this.showDeleteConfirm.set(true);
  }

  cancelDelete() {
    this.showDeleteConfirm.set(false);
    this.deleteTargetId.set('');
    this.deleteTargetName.set('');
  }

  confirmDelete() {
    const roomTypeId = this.deleteTargetId();
    if (!roomTypeId) return;
    this.deleting.set(true);
    this.errorMessage.set('');
    this.api.deleteRoomType(roomTypeId).pipe(
      switchMap(() => {
        const current = this.viewModel();
        return current ? this.api.getRooms(current.propId) : of(null);
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({        next: (rooms) => {
        this.viewModel.set(rooms);
        this.toast.success('Tipo de habitación eliminado');
        this.deleting.set(false);
        this.showDeleteConfirm.set(false);
      },        error: (error: ApiError) => {
        this.toast.error(error.message || 'No se pudo eliminar el tipo de habitación.');
        this.deleting.set(false);
      }
    });
  }

  saveEdit() {
    if (this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    const value = this.editForm.getRawValue();
    const propId = this.selectedPropId();
    this.savingEdit.set(true);

    // Update room type basic fields + features in parallel
    const prices = this.featurePrices();
    const featuresArr = [...this.selectedFeatures()].map((label) => ({
      label,
      unitPrice: prices.get(label) ?? 0,
    }));
    const roomTypeId = value.roomTypeId;

    this.api.updateRoomType(roomTypeId, {
      name: value.name,
      description: value.description,
      maxAdults: value.maxAdults,
      maxChildren: value.maxChildren,
      baseCapacity: value.baseCapacity,
      baseRate: value.baseRate || undefined,
      isActive: value.isActive,
      roomNumber: value.roomNumber,
      floor: value.floor,
      view: value.view,
      smoking: value.smoking,
      accessible: value.accessible,
    }).pipe(
      switchMap(() => {
        // Always update features (even empty array = clear all)
        if (propId > 0) {
          return this.api.updateRoomTypeFeatures(propId, roomTypeId, featuresArr);
        }
        return of(null);
      }),
      switchMap(() => {
        const current = this.viewModel();
        return current ? this.api.getRooms(current.propId) : of(null);
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({        next: (rooms) => {
        this.viewModel.set(rooms);
        this.toast.success('Tipo de habitación actualizado');
        this.savingEdit.set(false);
        this.showEditModal.set(false);
      },        error: (error: ApiError) => {
        this.toast.error(error.message || 'No fue posible actualizar el tipo de habitación.');
        this.savingEdit.set(false);
      }
    });
  }

  createRoomType() {
    const current = this.viewModel();
    if (!current || this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }

    const value = this.createForm.getRawValue();
    this.api
      .createRoomType({
        propId: current.propId,
        name: value.name,
        description: value.description,
        maxAdults: value.maxAdults,
        maxChildren: value.maxChildren,
        baseCapacity: value.baseCapacity,
        baseRate: value.baseRate || undefined,
        isActive: value.isActive,
        roomNumber: value.roomNumber,
        floor: value.floor,
        view: value.view,
        smoking: value.smoking,
        accessible: value.accessible,
      })
      .pipe(
        switchMap(() => this.api.getRooms(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rooms) => {
          this.viewModel.set(rooms);
          this.toast.success('Tipo de habitación registrado');
          this.createForm.reset({
            name: '',
            description: '',
            maxAdults: 2,
            maxChildren: 0,
            baseCapacity: 2,
            baseRate: 0,
            isActive: true,
            roomNumber: '',
            floor: '',
            view: '',
            smoking: false,
            accessible: false,
          });
        },
        error: (error: ApiError) => {
          this.toast.error(error.message || 'No fue posible registrar el tipo de habitación.');
        }
      });
  }
}
