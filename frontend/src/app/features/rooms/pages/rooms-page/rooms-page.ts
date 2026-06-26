import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
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
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { FeatureCategory, RoomTypeItem, RoomsViewModel } from '../../models/rooms.model';
import { RoomsApiService } from '../../services/rooms-api.service';
import { RoomTypeTableComponent } from '../../components/room-type-table/room-type-table';
import { AiSuggestDirective } from '../../../../core/directives/ai-suggest.directive';

@Component({
  selector: 'app-rooms-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
    RoomTypeTableComponent,
    RouterLink,
    AiSuggestDirective
  ],
  templateUrl: './rooms-page.html',
  styleUrl: './rooms-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RoomsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(RoomsApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly propertyCtx = inject(PropertyContextService);

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
  readonly editingRoomTypeName = signal('');
  readonly editingRoomTypeId = signal('');
  readonly featurePanelOpen = signal(true);
  readonly featureSearchQuery = signal('');

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
    this.route.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '0')),
        distinctUntilChanged(),
        switchMap((propId) => {
          this.viewState.set('loading');
          this.message.set('');
          this.errorMessage.set('');
          return propId > 0 ? this.api.getRooms(propId) : of(null);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
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
        error: () => this.viewState.set('error')
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

  startEdit(roomType: RoomTypeItem) {
    const parts = roomType.capacityLabel.match(/(\d+)/g);
    this.editForm.setValue({
      roomTypeId: roomType.id,
      name: roomType.name,
      description: roomType.description === 'Sin descripción' ? '' : roomType.description,
      maxAdults: parts && parts.length >= 2 ? Number(parts[1]) : 2,
      maxChildren: parts && parts.length >= 3 ? Number(parts[2]) : 0,
      baseCapacity: parts ? Number(parts[0]) : 2,
      baseRate: 0,
      isActive: roomType.activeLabel === 'Sí',
      roomNumber: roomType.roomNumber,
      floor: roomType.floor,
    });
    this.editingRoomTypeName.set(roomType.name);
    this.editingRoomTypeId.set(roomType.id);
    this.selectedFeatures.set(new Set(roomType.features));
    this.featurePanelOpen.set(true);
    this.showEditModal.set(true);

    // Load feature catalog if not already loaded
    if (this.featureCatalog().length === 0) {
      this.api.getFeatureCatalog().pipe(
        takeUntilDestroyed(this.destroyRef)
      ).subscribe({
        next: (catalog) => this.featureCatalog.set(catalog),
        error: () => { /* silently fail, feature selector will be empty */ },
      });
    }
  }

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

  cancelEdit() {
    this.showEditModal.set(false);
    this.editForm.reset();
    this.selectedFeatures.set(new Set());
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
    ).subscribe({
      next: (rooms) => {
        this.viewModel.set(rooms);
        this.message.set('Tipo de habitación eliminado');
        this.errorMessage.set('');
        this.deleting.set(false);
        this.showDeleteConfirm.set(false);
      },
      error: (error: ApiError) => {
        this.errorMessage.set(error.message || 'No se pudo eliminar el tipo de habitación.');
        this.message.set('');
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
    const featuresArr = [...this.selectedFeatures()];
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
    ).subscribe({
      next: (rooms) => {
        this.viewModel.set(rooms);
        this.message.set('Tipo de habitación actualizado');
        this.errorMessage.set('');
        this.savingEdit.set(false);
        this.showEditModal.set(false);
      },
      error: (error: ApiError) => {
        this.errorMessage.set(error.message || 'No fue posible actualizar el tipo de habitación.');
        this.message.set('');
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
      })
      .pipe(
        switchMap(() => this.api.getRooms(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rooms) => {
          this.viewModel.set(rooms);
          this.message.set('Tipo de habitación registrado');
          this.errorMessage.set('');
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
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible registrar el tipo de habitación.');
          this.message.set('');
        }
      });
  }
}
