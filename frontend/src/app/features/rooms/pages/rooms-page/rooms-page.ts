import { ChangeDetectionStrategy, ChangeDetectorRef, Component, computed, DestroyRef, effect, inject, NgZone, signal, ViewEncapsulation } from '@angular/core';
import { httpResource, HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
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
import type { FeatureCatalogDto, RoomsDto } from '../../models/rooms.dto';
import { RoomsApiService } from '../../services/rooms-api.service';
import { mapFeatureCatalog, mapRoomsResponse } from '../../mappers/rooms.mapper';
import type { TopHotelRoomsItem } from '../../../../shared/services/kpi-api.service';
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
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  readonly propertyCtx = inject(PropertyContextService);
  private readonly toast = inject(ToastService);
  private readonly ngZone = inject(NgZone);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly opMode = inject(OperationModeService);

  // ── KPI data (top 5 hotels by rooms) ──
  readonly topHotelsResource = httpResource<{ items: TopHotelRoomsItem[] }>(() => '/api/kpi/top-hotels/rooms?limit=5', {
    /**
     * Tolerant passthrough mapper. The wire `/api/kpi/top-hotels/rooms`
     * envelope is `{ items: [...] }`; each item shape is verified upstream
     * by `kpi-api.service` (`TopHotelRoomsItem` is the camelCase view-model).
     * If a future refactor factors `TopHotelRoomsItem` into a snake DTO,
     * replace this passthrough with an explicit snake→camel mapper.
     */
    parse: (dto) => dto as { items: TopHotelRoomsItem[] },
  });
  readonly topHotels = computed(() => this.topHotelsResource.value()?.items ?? []);

  readonly selectedPropId = signal(0);

  readonly roomsResource = httpResource<RoomsViewModel>(() => {
    const propId = this.selectedPropId();
    return propId > 0 ? `/api/management/rooms?prop_id=${propId}` : undefined;
  }, {
    parse: (dto) => mapRoomsResponse(dto as RoomsDto),
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.roomsResource.isLoading()) return 'loading';
    if (this.roomsResource.error()) return 'error';
    const vm = this.roomsResource.value();
    if (!vm) return 'empty';
    return 'success';
  });

  readonly selectedLabel = computed(() => this.roomsResource.value()?.hotelName ?? '');


  /** El formulario permanece oculto hasta que el usuario elige qué quiere crear. */
  readonly showCreateForm = signal(false);
  /** 'existing' = seleccionar tipo existente, 'new' = escribir nuevo */
  readonly createMode = signal<'existing' | 'new'>('new');
  readonly selectedExistingRoomTypeId = signal('');

  startCreate(mode: 'existing' | 'new'): void {
    this.createMode.set(mode);
    this.showCreateForm.set(true);
    this.opMode.setTransientMode(
      'insert',
      mode === 'new' ? 'Nueva habitación' : 'Habitación con tipo existente',
    );

    if (mode === 'new') {
      this.setCreateMode('new');
    }
  }

  cancelCreate(): void {
    this.showCreateForm.set(false);
    this.selectedExistingRoomTypeId.set('');
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
      imageUrl: '',
    });
    this.createImagePreviewUrl.set('');
    this.createSelectedFile.set(null);
    this.opMode.reset();
  }

  private resetCreateForm(): void {
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
      imageUrl: '',
    });
    this.createImagePreviewUrl.set('');
    this.createSelectedFile.set(null);
  }

  private closeCreateForm(): void {
    this.showCreateForm.set(false);
    this.resetCreateForm();
    this.opMode.reset();
  }

  readonly existingRoomTypes = computed(() => {
    return this.roomsResource.value()?.roomTypes ?? [];
  });
  readonly hasExistingRoomTypes = computed(() => this.existingRoomTypes().length > 0);

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
    imageUrl: [''],
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
    if (this.showCreateForm()) {
      this.opMode.setMode(
        'insert',
        mode === 'new' ? 'Nueva habitación' : 'Habitación con tipo existente',
      );
    }
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
    imageUrl: [''],
  });

  readonly showEditModal = signal(false);
  readonly savingEdit = signal(false);
  readonly showDeleteConfirm = signal(false);
  readonly deleteTargetId = signal('');
  readonly deleteTargetName = signal('');
  readonly deleting = signal(false);
  /** Error contextual mostrado dentro del modal de borrado (no es un banner). */
  readonly errorMessage = signal('');

  /* ── Room Features ── */
  readonly featureCatalogRequested = signal(false);
  readonly featureCatalogResource = httpResource<FeatureCategory[]>(() => {
    return this.featureCatalogRequested() ? '/api/management/room-features' : undefined;
  }, {
    parse: (raw) => mapFeatureCatalog(raw as FeatureCatalogDto),
  });
  readonly featureCatalog = computed(() => this.featureCatalogResource.value() ?? []);
  readonly selectedFeatures = signal<Set<string>>(new Set());
  readonly editingRoomTypeName = signal('');
  readonly editingRoomTypeId = signal('');
  readonly featurePanelOpen = signal(true);
  readonly featureSearchQuery = signal('');
  readonly editImagePreviewUrl = signal('');
  readonly editUploading = signal(false);
  readonly editSelectedFile = signal<File | null>(null);
  readonly createImagePreviewUrl = signal('');
  readonly createSelectedFile = signal<File | null>(null);

  // ── Fotos por tipo de habitación (migrado desde amenities/servicios) ──
  // Sube imágenes reales por room_type_id. Se muestran en hotel-card después de las fotos del hotel.
  readonly roomPhotoRoomType = signal('');
  readonly roomPhotoUploading = signal(false);
  readonly roomPhotoMessage = signal('');
  readonly roomPhotoMsgType = signal<'success' | 'error' | ''>('');
  readonly roomPhotoList = signal<{ image_url: string; title: string; room_type_id: string }[]>([]);

  private readonly http = inject(HttpClient);

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
    return this.roomPhotoList().filter((p) => p.room_type_id === rt);
  });

  readonly roomPhotoLoading = computed(() => this.roomPhotoListRes.isLoading());

  /** Bound function reference for passing to partial components */
  readonly isFeatureSelectedFn = (label: string) => this.isFeatureSelected(label);

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
      .subscribe((propId) => this.selectedPropId.set(propId));

    // Auto-carga en modo single-hotel
    effect(() => {
      if (this.propertyCtx.ready() && this.propertyCtx.singleHotelMode()) {
        const propId = this.propertyCtx.currentPropId();
        if (propId && this.selectedPropId() !== propId) {
          this.selectedPropId.set(propId);
        }
      }
    });

    // Sync property context when fresh data arrives
    effect(() => {
      const vm = this.roomsResource.value();
      if (vm) {
        this.propertyCtx.setProperty(vm.propId, vm.hotelName);
      } else if (this.selectedPropId() === 0) {
        this.propertyCtx.clear();
      }
    });

    // Top hotels KPI and feature catalog are now loaded declaratively via httpResource.
    // Sincroniza fotos por habitación desde httpResource → signal escribible (optimistic delete)
    effect(() => {
      const data = this.roomPhotoListRes.value();
      if (data?.images) {
        this.roomPhotoList.set(data.images);
      }
    });
    // Limpia selección y mensaje al cambiar de propiedad
    effect(() => {
      // track propId para invalidar selección obsoleta
      const _ = this.selectedPropId();
      this.roomPhotoRoomType.set('');
      this.roomPhotoMessage.set('');
      this.roomPhotoMsgType.set('');
    });
  }

  onCreateImageUrlChange(url: string) {
    this.createImagePreviewUrl.set(url);
    this.createForm.patchValue({ imageUrl: url });
    if (!url) this.createSelectedFile.set(null);
  }

  onCreateFileSelected(file: File) {
    this.createSelectedFile.set(file);
    const reader = new FileReader();
    reader.onload = () => {
      this.createImagePreviewUrl.set(reader.result as string);
    };
    reader.readAsDataURL(file);
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
    // Editar tipo de habitación existente → modo update en el nav.
    this.opMode.setTransientMode('update', roomType.name);
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
          imageUrl: roomType.imageUrl || '',
        });
        this.ngZone.run(() => {
          this.editingRoomTypeName.set(roomType.name);
          this.editingRoomTypeId.set(roomType.id);
          this.selectedFeatures.set(new Set(roomType.features.map(f => f.label)));
          this.featurePanelOpen.set(true);
          this.editImagePreviewUrl.set(roomType.imageUrl || '');
          this.editSelectedFile.set(null);
          this.editUploading.set(false);
          this.showEditModal.set(true);
          this.cdr.markForCheck();
        });
      });
    });

    // Trigger feature catalog load (idempotent via httpResource caching)
    this.featureCatalogRequested.set(true);
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

  onEditImageUrlChange(url: string) {
    this.editImagePreviewUrl.set(url);
    this.editForm.patchValue({ imageUrl: url });
  }

  onEditFileSelected(file: File) {
    this.editSelectedFile.set(file);
    // Show local preview
    const reader = new FileReader();
    reader.onload = () => {
      this.editImagePreviewUrl.set(reader.result as string);
    };
    reader.readAsDataURL(file);
  }

  uploadEditFile() {
    const file = this.editSelectedFile();
    const roomTypeId = this.editingRoomTypeId();
    if (!file || !roomTypeId) return;

    this.editUploading.set(true);
    this.api.uploadRoomImage(this.selectedPropId(), roomTypeId, file).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (result) => {
        this.editForm.patchValue({ imageUrl: result.image_url });
        this.editImagePreviewUrl.set(result.image_url);
        this.editSelectedFile.set(null);
        this.editUploading.set(false);
        this.toast.success('Imagen subida correctamente');
      },
      error: (err) => {
        console.error('[Rooms] Failed to upload image', err);
        this.toast.error('Error al subir la imagen');
        this.editUploading.set(false);
      }
    });
  }

  cancelEdit() {
    this.opMode.reset();
    this.showEditModal.set(false);
    this.editForm.reset();
    this.selectedFeatures.set(new Set());
    this.editImagePreviewUrl.set('');
    this.editSelectedFile.set(null);
    this.editUploading.set(false);
  }

  requestDelete(roomTypeId: string, name: string) {
    // Modo delete mientras el modal de confirmación está abierto.
    this.opMode.setTransientMode('delete', name);
    this.deleteTargetId.set(roomTypeId);
    this.deleteTargetName.set(name);
    this.showDeleteConfirm.set(true);
  }

  cancelDelete() {
    this.opMode.reset();
    this.showDeleteConfirm.set(false);
    this.deleteTargetId.set('');
    this.deleteTargetName.set('');
  }

  confirmDelete() {
    const roomTypeId = this.deleteTargetId();
    if (!roomTypeId) return;
    this.deleting.set(true);
    this.errorMessage.set('');
    this.api.deleteRoomType(this.selectedPropId(), roomTypeId).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.roomsResource.reload();
        this.toast.success('Tipo de habitación eliminado');
        this.deleting.set(false);
        this.showDeleteConfirm.set(false);
        this.opMode.reset();
      },
      error: (error: ApiError) => {
        this.toast.error(error.message || 'No se pudo eliminar el tipo de habitación.');
        this.deleting.set(false);
        this.opMode.reset();
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
    const featuresArr = [...this.selectedFeatures()].map((label) => ({ label }));
    const roomTypeId = value.roomTypeId;

    this.api.updateRoomType(propId, roomTypeId, {
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
      imageUrl: value.imageUrl,
    }).pipe(
      switchMap(() => {
        // Always update features (even empty array = clear all)
        if (propId > 0) {
          return this.api.updateRoomTypeFeatures(propId, roomTypeId, featuresArr);
        }
        return of(null);
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.roomsResource.reload();
        this.toast.success('Tipo de habitación actualizado');
        this.savingEdit.set(false);
        this.showEditModal.set(false);
        this.opMode.reset();
      },
      error: (error: ApiError) => {
        // El modal sigue abierto con el error → se mantiene el modo update.
        this.toast.error(error.message || 'No fue posible actualizar el tipo de habitación.');
        this.savingEdit.set(false);
      }
    });
  }

  createRoomType() {
    const current = this.roomsResource.value();
    if (!current || this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }

    const value = this.createForm.getRawValue();
    const pendingFile = this.createSelectedFile();
    const mode = this.createMode();
    const existingTypeId = this.selectedExistingRoomTypeId();

    let request;

    if (mode === 'existing' && existingTypeId) {
      // En modo 'Usar existente': solo crear hotel_room ligado al tipo seleccionado
      request = this.api.createHotelRoomForType(current.propId, existingTypeId, {
        roomNumber: value.roomNumber,
        floor: value.floor,
        view: value.view,
        smoking: value.smoking,
        accessible: value.accessible,
        isActive: value.isActive,
      });
    } else {
      // En modo 'Crear nuevo': crear room_type + hotel_room
      request = this.api
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
          imageUrl: value.imageUrl,
        })
        .pipe(
          switchMap((created: any) => {
            const roomTypeId = created?.room_type_id;
            // If there's a pending file, upload it after creation
            if (pendingFile && roomTypeId) {
              return this.api.uploadRoomImage(current.propId, roomTypeId, pendingFile).pipe(
                map(() => roomTypeId)
              );
            }
            return of(roomTypeId);
          })
        );
    }

    request.pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.roomsResource.reload();
        const msg = mode === 'existing' ? 'Habitación física registrada' : 'Tipo de habitación registrado';
        this.toast.success(msg);
        this.closeCreateForm();
      },
      error: (error: ApiError) => {
        this.toast.error(error.message || 'No fue posible registrar.');
      }
    });
  }

  // ── Fotos por tipo de habitación ──

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
          this.roomPhotoMessage.set(err.error?.message || err.error?.detail || 'Error al eliminar la foto.');
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
