import { httpResource, HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal, ViewEncapsulation } from '@angular/core';
import { getErrorStatus, getErrorMessage } from '../../../../shared/utils/http-error.util';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import { ReservationsAuthService } from '../../services/reservations-auth.service';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { NoShowService } from '../../../../shared/services/no-show.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';

import { ReservationTimelineComponent } from './components/reservation-timeline';
import { RdHeroComponent } from './partials/rd-hero';
import { RdInfoPanelsComponent } from './partials/rd-info-panels';
import { RdFinancialPanelsComponent } from './partials/rd-financial-panels';
import { RdEditFormComponent } from './partials/rd-edit-form';
import { RdInvoicePanelComponent } from './partials/rd-invoice-panel';
import { RdProductsSectionComponent } from './partials/rd-products-section';
import { RdAssignedRoomsComponent } from './partials/rd-assigned-rooms';
import { RdHistoryPanelComponent } from './partials/rd-history-panel';
import { RdProductModalComponent } from './partials/rd-product-modal';
import { RdRoomModalComponent } from './partials/rd-room-modal';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { FulfillmentItem, ReservationDetailViewModel } from '../../models/reservations.model';
import type { ReservationDetailDto } from '../../models/reservations.dto';
import { mapReservationDetail } from '../../mappers/reservations.mapper';
import { ReservationsApiService } from '../../services/reservations-api.service';
import { ReservationActionService } from '../../services/reservation-action.service';
import { ProductsApiService, mapProduct, mapLineItem } from '../../../products/services/products-api.service';
import type { BookingLineItem, HotelProduct } from '../../../products/models/products.model';
import { InStayApiService } from '../../../in-stay/services/in-stay-api.service';
import { canAssignRooms, canEditBooking } from '../../utils/reservation-status.util';

interface EditForm {
  checkInDate: string;
  checkOutDate: string;
  rooms: number;
  comment: string;
}

interface AvailableRoomsResponse {
  prop_id: number;
  room_type: { name: string; base_capacity: number; max_adults: number } | null;
  rooms_required: number;
  rooms_available: number;
  available_rooms: { hotel_room_id: string; room_number: string; room_label: string; floor: string; room_status: string }[];
  assigned_rooms: string[];
}

@Component({
  selector: 'app-reservation-detail-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReservationTimelineComponent,
    RdHeroComponent, RdInfoPanelsComponent, RdFinancialPanelsComponent, RdEditFormComponent,
    RdInvoicePanelComponent, RdProductsSectionComponent, RdAssignedRoomsComponent,
    RdHistoryPanelComponent, RdProductModalComponent, RdRoomModalComponent],
  templateUrl: './reservation-detail-page.html',
  styleUrl: './reservation-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class ReservationDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly reservationsAuth = inject(ReservationsAuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly productsApi = inject(ProductsApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly noShow = inject(NoShowService);
  private readonly instayApi = inject(InStayApiService);
  private readonly actionService = inject(ReservationActionService);
  private readonly router = inject(Router);
  private readonly operationMode = inject(OperationModeService);

  readonly cancelPending = signal(false);
  readonly confirmPending = signal(false);
  readonly rejectPending = signal(false);
  readonly noShowPending = signal(false);
  readonly successMessage = signal('');
  readonly errorMessage = signal('');

  // ─── Reactive route param ───
  private readonly paramMap = toSignal(this.activatedRoute.paramMap, {
    initialValue: this.activatedRoute.snapshot.paramMap,
  });
  readonly bookingId = computed(() => this.paramMap().get('bookingId') ?? '');

  // ─── Reservation detail — httpResource nativo ───
  readonly detailResource = httpResource<ReservationDetailViewModel>(() => {
    const id = this.bookingId();
    if (!id) return undefined;
    return `/reservations/${id}`;
  }, {
    parse: (dto) => mapReservationDetail(dto as ReservationDetailDto),
  });

  /** Fulfillment checklists (pending/fulfilled) — local copies of the
   *  detail's ``specialRequestFulfillment`` / ``amenityFulfillment`` so
   *  toggles update without refetching. */
  readonly requestFulfillment = signal<FulfillmentItem[]>([]);
  readonly amenityFulfillment = signal<FulfillmentItem[]>([]);
  readonly fulfillmentUpdating = signal(false);

  toggleFulfillment(kind: 'special_request' | 'amenity', label: string, status: 'pending' | 'fulfilled'): void {
    const vm = this.detailResource.value();
    if (!vm || this.fulfillmentUpdating()) return;
    this.fulfillmentUpdating.set(true);
    this.errorMessage.set('');
    this.reservationsApi.updateSpecialRequestStatus(vm.bookingId, label, status, kind)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          const mapped: FulfillmentItem[] = res.fulfillment.map((f) => ({
            label: f.label,
            status: f.status === 'fulfilled' ? ('fulfilled' as const) : ('pending' as const),
            fulfilledAt: f.fulfilled_at ?? null,
          }));
          if (kind === 'amenity') {
            this.amenityFulfillment.set(mapped);
          } else {
            this.requestFulfillment.set(mapped);
          }
          const noun = kind === 'amenity' ? 'Servicio' : 'Petición';
          this.successMessage.set(`${noun} "${label}" ${status === 'fulfilled' ? 'marcado como cumplido' : 'reabierto'}.`);
          this.fulfillmentUpdating.set(false);
        },
        error: (err) => {
          this.errorMessage.set(err?.error?.detail || 'No se pudo actualizar el checklist.');
          this.fulfillmentUpdating.set(false);
        },
      });
  }

  readonly viewState = computed<ViewState>(() => {
    if (this.detailResource.isLoading()) return 'loading';
    const err = this.detailResource.error();
    if (err) {
      // getErrorStatus cubre HttpErrorResponse (tests) y ApiError del interceptor (vivo).
      const status = getErrorStatus(err);
      return status === 404 ? 'empty' : 'error';
    }
    return this.detailResource.value() ? 'success' : 'loading';
  });


  // Edit booking
  readonly editMode = signal(false);
  readonly editForm = signal<EditForm>({ checkInDate: '', checkOutDate: '', rooms: 1, comment: '' });
  readonly editSaving = signal(false);
  readonly editError = signal('');

  // Products (add-on services) — httpResource (auto-fire when detailResource changes)
  readonly Math = Math;
  // Products + line items via httpResource. Backend wraps responses in
  // `{ items: [...] }`; the `parse` function unwraps and reuses the
  // existing `mapProduct` / `mapLineItem` mappers from ProductsApiService.
  readonly productsResource = httpResource<HotelProduct[]>(() => {
    const vm = this.detailResource.value();
    // Los huéspedes (cliente/anónimo) no ven ni agregan productos: evitar
    // disparar el request y el 403 properties.read en su detalle.
    if (!vm || this.reservationsAuth.isClient()) return undefined;
    return `/management/products/hotels/${vm.propId}`;
  }, {
    parse: (raw: any) => (raw?.items ?? []).map(mapProduct),
  });

  readonly lineItemsResource = httpResource<BookingLineItem[]>(() => {
    const vm = this.detailResource.value();
    if (!vm || this.reservationsAuth.isClient()) return undefined;
    return `/management/products/bookings/${vm.bookingId}/line-items`;
  }, {
    parse: (raw: any) => (raw?.items ?? []).map(mapLineItem),
  });

  readonly hotelProducts = computed(() => {
    // httpResource.value() LANZA cuando el request falló (ej. 403 properties.read):
    // devolver [] degrada con gracia en vez de relanzar el error en cada
    // recomputación (spam de consola en el detalle visto por roles sin permiso).
    if (this.productsResource.error()) return [];
    return this.productsResource.value() ?? [];
  });
  readonly productsState = computed<ViewState>(() => {
    // Huéspedes: el request nunca se dispara (ver productsResource) → el
    // recurso queda idle; reportar 'forbidden' para mostrar el estado
    // "sin permiso" en la sección en vez de "no hay productos".
    if (this.reservationsAuth.isClient()) return 'forbidden';
    if (this.productsResource.isLoading()) return 'loading';
    const err = this.productsResource.error();
    if (err) {
      // 403 properties.read → el usuario no tiene permiso, no es un error del server.
      // getErrorStatus cubre HttpErrorResponse (tests) y ApiError del interceptor (vivo).
      if (getErrorStatus(err) === 403) return 'forbidden';
      return 'error';
    }
    return this.productsResource.value()?.length ? 'success' : 'empty';
  });
  readonly lineItems = computed(() => {
    if (this.lineItemsResource.error()) return [];
    return this.lineItemsResource.value() ?? [];
  });
  readonly lineItemsState = computed<ViewState>(() => {
    if (this.reservationsAuth.isClient()) return 'forbidden';
    if (this.lineItemsResource.isLoading()) return 'loading';
    const err = this.lineItemsResource.error();
    if (err) {
      if (getErrorStatus(err) === 403) return 'forbidden';
      return 'error';
    }
    return this.lineItemsResource.value()?.length ? 'success' : 'empty';
  });
  readonly lineItemsTotal = computed(() => this.lineItems().reduce((sum, li) => sum + li.total, 0));
  /** Exclude 'Daños' from sellable products — damages are handled at checkout */
  readonly productsGrouped = computed(() => {
    const groups = new Map<string, HotelProduct[]>();
    for (const p of this.hotelProducts()) {
      if (p.category === 'Daños') continue;
      if (!groups.has(p.category)) groups.set(p.category, []);
      groups.get(p.category)!.push(p);
    }
    return [...groups.entries()].map(([category, items]) => ({ category, items }));
  });
  readonly productCategories = computed(() => this.productsGrouped().map(g => g.category));
  readonly selectedProductCategory = signal<string>('');
  readonly filteredProducts = computed(() => {
    const cat = this.selectedProductCategory();
    return cat ? this.productsGrouped().find(g => g.category === cat)?.items ?? [] : [];
  });
  readonly addProductId = signal('');
  readonly addProductQty = signal(1);
  readonly addProductSaving = signal(false);
  readonly removeItemSaving = signal<string | null>(null);
  readonly productError = signal('');
  readonly showProductModal = signal(false);

  readonly selectedProduct = computed(() => {
    const pid = this.addProductId();
    if (!pid) return null;
    return this.hotelProducts().find((p) => p.productId === pid) ?? null;
  });

  readonly canAddProducts = computed(() => {
    const vm = this.detailResource.value();
    return vm && canAssignRooms(vm.status) && this.isStaff();
  });

  // Cancel preview — on-demand httpResource via trigger signal
  readonly cancelPreviewTrigger = signal('');
  readonly cancelPreviewResource = httpResource<any>(() => {
    const id = this.cancelPreviewTrigger();
    return id ? `/reservations/${id}/cancel-preview` : undefined;
  });

  // Available rooms for assignment — on-demand httpResource via trigger signal
  readonly availableRoomsTrigger = signal('');
  readonly availableRoomsResource = httpResource<AvailableRoomsResponse>(() => {
    const id = this.availableRoomsTrigger();
    return id ? `/management/bookings/${id}/available-rooms` : undefined;
  });

  // Room assignment modal
  readonly showRoomModal = signal(false);
  readonly roomAssignmentState = signal<'loading' | 'success' | 'error' | 'idle'>('idle');
  readonly availableRooms = signal<{ hotel_room_id: string; room_number: string; room_label: string; floor: string; room_status: string }[]>([]);
  readonly assignedRoomIds = signal<string[]>([]);
  readonly selectedRoomIds = signal<Set<string>>(new Set());
  readonly roomAssignmentSaving = signal(false);
  readonly roomAssignmentMessage = signal('');
  readonly roomsRequired = signal(0);

  readonly isStaff = this.reservationsAuth.isStaff;
  readonly isClient = this.reservationsAuth.isClient;

  readonly canConfirm = computed(() => {
    const vm = this.detailResource.value();
    return vm && vm.status === 'pending' && this.isStaff();
  });

  readonly canReject = computed(() => this.canConfirm());

  /**
   * No-show manual: aplica a reservas confirmadas cuyo check-in ya pasó y que
   * NO tienen estancia activa/terminal. Incluye `stay_status` ausente (reservas
   * legacy sin check-in registrado) y `pending` — el backend (process_no_show)
   * acepta ambos; checked_in/checked_out/no_show quedan excluidos.
   */
  readonly canMarkNoShow = computed(() => {
    const vm = this.detailResource.value();
    if (!vm || !this.isStaff()) return false;
    if (vm.status !== 'confirmed' || vm.checkInDate > this.todayStr()) return false;
    return !['checked_in', 'checked_out', 'no_show'].includes(vm.stayStatus ?? '');
  });

  readonly todayStr = computed(() => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  });

  readonly canEdit = computed(() => {
    const vm = this.detailResource.value();
    if (!vm) return false;
    return canEditBooking(vm.status, vm.stayStatus, this.todayStr(), vm.checkOutDate);
  });

  constructor() {
    // Seed the fulfillment checklists when the detail loads (and on booking changes).
    effect(() => {
      const vm = this.detailResource.value();
      if (vm?.specialRequestFulfillment) {
        this.requestFulfillment.set(vm.specialRequestFulfillment);
      }
      if (vm?.amenityFulfillment) {
        this.amenityFulfillment.set(vm.amenityFulfillment);
      }
    });

    // Sync cancel preview result to cancelPenalty signal
    effect(() => {
      const preview = this.cancelPreviewResource.value();
      const err = this.cancelPreviewResource.error();
      if (!this.cancelPreviewTrigger()) return;

      if (preview) {
        this.cancelPenalty.set({
          free: preview.free_cancellation,
          amount: preview.penalty_amount,
          percent: preview.penalty_percent,
          hours: preview.hours_until_checkin,
          policyHours: preview.cancellation_hours,
          oneNightPrice: (preview as any).one_night_price ?? 0,
          totalNights: (preview as any).total_nights ?? 1,
        });
        const current = this.detailResource.value();
        if (current) {
          this.confirmCancellation(current.bookingId, current.guestName);
        }
        this.cancelPending.set(false);
        this.cancelPreviewTrigger.set('');
      } else if (err && !this.cancelPreviewResource.isLoading()) {
        // Fallback: show basic confirm dialog
        this.cancelPending.set(false);
        this.cancelPreviewTrigger.set('');
        const current = this.detailResource.value();
        if (current) {
          this.confirmDialog.open({
            title: 'Cancelar reserva',
            message: `Cancelar la reserva de ${current.guestName}?`,
            confirmLabel: 'Cancelar reserva',
            variant: 'danger',
            mode: 'delete',
            modeDetail: `Reserva ${current.bookingId}`,
          }).then((ok) => { if (ok) this.executeCancel(current.bookingId); });
        }
      }
    });

    // Sync available rooms result
    effect(() => {
      const result = this.availableRoomsResource.value();
      const err = this.availableRoomsResource.error();
      if (!this.availableRoomsTrigger()) return;

      if (result) {
        this.availableRooms.set(result.available_rooms);
        this.assignedRoomIds.set(result.assigned_rooms || []);
        this.roomsRequired.set(result.rooms_required);
        if (result.assigned_rooms && result.assigned_rooms.length > 0) {
          this.selectedRoomIds.set(new Set(result.assigned_rooms));
        }
        this.roomAssignmentState.set('success');
        this.availableRoomsTrigger.set('');
      } else if (err && !this.availableRoomsResource.isLoading()) {
        this.roomAssignmentState.set('error');
        this.availableRoomsTrigger.set('');
      }
    });
  }

  // ── Products (Add-on Services) ──

  loadProducts() {
    this.productsResource.reload();
    this.lineItemsResource.reload();
  }

  openProductModal() {
    this.showProductModal.set(true);
    this.addProductId.set('');
    this.addProductQty.set(1);
    // Auto-select first category
    const cats = this.productCategories();
    if (cats.length > 0) {
      this.selectedProductCategory.set(cats[0]);
    }
  }

  closeProductModal() {
    this.showProductModal.set(false);
    this.selectedProductCategory.set('');
  }

  selectProduct(product: HotelProduct) {
    this.addProductId.set(product.productId);
    this.addProductQty.set(1);
  }

  addProductToBooking() {
    const vm = this.detailResource.value();
    const product = this.selectedProduct();
    if (!vm || !product || this.addProductSaving()) return;

    this.productError.set('');
    this.addProductSaving.set(true);
    this.productsApi.addLineItem(vm.bookingId, {
      product_id: product.productId,
      name: product.name,
      unit_price: product.unitPrice,
      quantity: this.addProductQty(),
    }, vm.propId).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        this.addProductSaving.set(false);
        this.closeProductModal();
        this.onTimelineMessage('Producto agregado a la reserva.');
        this.loadProducts();
      },
      error: () => {
        this.addProductSaving.set(false);
        this.productError.set('Error al agregar el producto.');
      },
    });
  }

  async removeLineItem(itemId: string, itemName: string) {
    const vm = this.detailResource.value();
    if (!vm) return;
    const ok = await this.confirmDialog.open({
      title: 'Eliminar producto',
      message: `¿Eliminar "${itemName}" de la reserva?`,
      confirmLabel: 'Eliminar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: itemName,
    });
    if (!ok) return;
    this.productError.set('');
    this.removeItemSaving.set(itemId);
    this.productsApi.removeLineItem(vm.bookingId, itemId, vm.propId).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        this.removeItemSaving.set(null);
        this.onTimelineMessage('Producto eliminado de la reserva.');
        this.loadProducts();
      },
      error: () => {
        this.removeItemSaving.set(null);
        this.productError.set('Error al eliminar el producto.');
      },
    });
  }

  toggleEdit() {
    if (this.editMode()) {
      this.editMode.set(false);
      this.operationMode.reset();
      return;
    }
    const vm = this.detailResource.value();
    if (vm) {
      this.editForm.set({
        checkInDate: vm.checkInDate,
        checkOutDate: vm.checkOutDate,
        rooms: vm.rooms,
        comment: vm.comment === 'N/D' ? '' : vm.comment,
      });
      this.editError.set('');
      this.editMode.set(true);
      // Modo edición → UPDATE en el nav (naranja: sobrescribe estado existente)
      this.operationMode.setMode('update', vm.bookingId);
    }
  }

  /** Handle field changes from the edit form partial */
  handleFieldChange(data: { field: 'checkInDate' | 'checkOutDate' | 'rooms' | 'comment'; value: string | number }) {
    this.editForm.update(f => ({ ...f, [data.field]: data.value }));
  }

  saveEdit() {
    const vm = this.detailResource.value();
    if (!vm || this.editSaving()) return;
    const f = this.editForm();
    this.editSaving.set(true);
    this.editError.set('');

    const payload: Record<string, unknown> = {};
    if (f.checkInDate !== vm.checkInDate) payload['check_in_date'] = f.checkInDate;
    if (f.checkOutDate !== vm.checkOutDate) payload['check_out_date'] = f.checkOutDate;
    if (f.rooms !== vm.rooms) payload['rooms'] = f.rooms;
    if (f.comment !== vm.comment) payload['comment'] = f.comment;

    if (Object.keys(payload).length === 0) {
      this.editMode.set(false);
      this.editSaving.set(false);
      return;
    }

    this.reservationsApi.modifyBooking(vm.bookingId, payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.detailResource.reload();
          this.editMode.set(false);
          this.editSaving.set(false);
          this.operationMode.reset();
          this.successMessage.set('Reserva modificada exitosamente.');
          setTimeout(() => this.successMessage.set(''), 4000);
        },
        error: (err: unknown) => {
          // getErrorMessage cubre HttpErrorResponse y ApiError del interceptor.
          this.editError.set(getErrorMessage(err) || 'Error al modificar la reserva');
          this.editSaving.set(false);
          this.operationMode.reset();
        },
      });
  }

  readonly cancelPenalty = signal<{free: boolean; amount: number; percent: number; hours: number | null; policyHours: number; oneNightPrice: number; totalNights: number} | null>(null);

  async cancelReservation() {
    const current = this.detailResource.value();
    if (!current || !current.canCancel || this.cancelPending()) return;

    this.cancelPending.set(true);
    // Trigger the cancel preview resource (result handled in effect)
    this.cancelPreviewTrigger.set(current.bookingId);
  }

  private async confirmCancellation(bookingId: string, guestName: string) {
    const p = this.cancelPenalty();
    if (!p) return;

    // If penalty amount is zero, always treat as free cancellation (backend safety net)
    const isEffectivelyFree = p.free || p.amount <= 0;

    let message = '';
    let details: string[] | undefined;
    if (isEffectivelyFree) {
      message = `Cancelación gratuita. Quedan ${p.hours}h antes del check-in (límite: ${p.policyHours}h). ¿Confirmar cancelación de ${guestName}?`;
    } else {
      const oneNight = p.oneNightPrice > 0 ? `$${p.oneNightPrice.toFixed(2)}` : 'N/D';
      message = `⚠️ Cancelación tardía — solo quedan ${p.hours}h para el check-in (límite gratuito: ${p.policyHours}h). ¿Cancelar la reserva de ${guestName}?`;
      details = [
        `1 noche = ${oneNight} (${p.totalNights} noche(s) en total)`,
        `Penalización = ${p.percent}% de 1 noche`,
        `Total a pagar = $${p.amount.toFixed(2)}`,
      ];
    }

    const ok = await this.confirmDialog.open({
      title: 'Cancelar reserva',
      message,
      details,
      confirmLabel: isEffectivelyFree ? 'Cancelar sin costo' : `Pagar $${p.amount.toFixed(2)} y cancelar`,
      variant: isEffectivelyFree ? 'warning' : 'danger',
      // Cancelación = borrado lógico → mostrar modo delete mientras se confirma.
      mode: 'delete',
      modeDetail: `Reserva ${bookingId}`,
    });
    if (!ok) return;
    this.executeCancel(bookingId);
  }

  private executeCancel(bookingId: string) {
    this.cancelPending.set(true);
    // Cancelación = borrado lógico → modo DELETE en el nav (rojo)
    this.operationMode.setMode('delete', bookingId);
    this.reservationsApi
      .cancelReservation(bookingId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => { this.detailResource.reload(); this.cancelPending.set(false); this.operationMode.reset(); },
        error: () => { this.cancelPending.set(false); this.operationMode.reset(); }
      });
  }

  confirmReservation() {
    const current = this.detailResource.value();
    if (!current || !this.canConfirm() || this.confirmPending()) return;
    this.confirmPending.set(true);
    this.successMessage.set('');

    this.actionService.confirm({ bookingId: current.bookingId }).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.detailResource.reload();
        this.confirmPending.set(false);
        this.successMessage.set('Reserva confirmada exitosamente.');
        setTimeout(() => this.successMessage.set(''), 4000);
      },
      error: () => { this.confirmPending.set(false); }
    });
  }

  rejectReservation() {
    const current = this.detailResource.value();
    if (!current || !this.canReject() || this.rejectPending()) return;
    this.rejectPending.set(true);
    this.successMessage.set('');

    this.actionService.reject({ bookingId: current.bookingId }).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.detailResource.reload();
        this.rejectPending.set(false);
        this.successMessage.set('Reserva rechazada.');
        setTimeout(() => this.successMessage.set(''), 4000);
      },
      error: () => { this.rejectPending.set(false); }
    });
  }

  /**
   * Marca la reserva como no-show (penalización de la primera noche). El
   * huésped no llegó al check-in: se restaura inventario, se crea el folio
   * con la penalización y se notifica por email. Flujo compartido con
   * confirmación previa + modo delete en el nav (acción terminal).
   */
  async markNoShow() {
    const current = this.detailResource.value();
    if (!current || !this.canMarkNoShow() || this.noShowPending()) return;

    this.noShowPending.set(true);
    this.successMessage.set('');
    this.errorMessage.set('');
    this.operationMode.setMode('delete', current.bookingId);
    try {
      const result = await this.noShow.markNoShowWithConfirm(current.bookingId, current.guestName, current.propId);
      if (!result) return; // cancelado — el finally libera pending + opMode
      this.successMessage.set(this.noShow.successMessage(result));
      this.detailResource.reload();
      setTimeout(() => this.successMessage.set(''), 5000);
    } catch (err) {
      this.errorMessage.set(getErrorMessage(err) || 'No fue posible marcar el no-show.');
      setTimeout(() => this.errorMessage.set(''), 6000);
    } finally {
      this.noShowPending.set(false);
      this.operationMode.reset();
    }
  }

  // ── Room Assignment ──

  openRoomModal() {
    const vm = this.detailResource.value();
    if (!vm) return;
    this.showRoomModal.set(true);
    this.roomAssignmentState.set('loading');
    this.roomAssignmentMessage.set('');
    this.selectedRoomIds.set(new Set());
    // Trigger the available rooms resource (result handled in effect)
    this.availableRoomsTrigger.set(vm.bookingId);
  }

  closeRoomModal() {
    this.showRoomModal.set(false);
    this.roomAssignmentState.set('idle');
  }

  toggleRoomSelection(roomId: string) {
    const current = new Set(this.selectedRoomIds());
    if (current.has(roomId)) {
      current.delete(roomId);
    } else {
      current.add(roomId);
    }
    this.selectedRoomIds.set(current);
  }

  saveRoomAssignment() {
    const vm = this.detailResource.value();
    if (!vm) return;
    const selected = [...this.selectedRoomIds()];
    if (selected.length === 0) return;

    this.roomAssignmentSaving.set(true);
    this.roomAssignmentMessage.set('');

    this.reservationsApi.assignRooms(vm.bookingId, selected).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.detailResource.reload();
        this.roomAssignmentSaving.set(false);
        this.showRoomModal.set(false);
        this.successMessage.set('Habitaciones asignadas correctamente.');
        setTimeout(() => this.successMessage.set(''), 4000);
      },
      error: () => {
        this.roomAssignmentSaving.set(false);
        this.roomAssignmentMessage.set('Error al asignar habitaciones');
      }
    });
  }

  goToInStay(bookingId: string) {
    const vm = this.detailResource.value();
    this.instayApi.getMyStaySession(bookingId, vm?.propId ?? 0).subscribe({
      next: (session) => {
        if (session.token) {
          this.router.navigate(['/stay', session.token]);
        }
      },
      error: () => {
        this.successMessage.set('No se pudo acceder a Mi Estancia. ¿Ya hiciste check-in?');
        setTimeout(() => this.successMessage.set(''), 5000);
      },
    });
  }

  goToInvoice(invoiceId: string) {
    if (this.isStaff()) {
      this.router.navigate(['/management/billing/invoices', invoiceId]);
    } else {
      this.router.navigate(['/account/billing', invoiceId]);
    }
  }

  onTimelineMessage(message: string) {
    this.successMessage.set(message);
    setTimeout(() => this.successMessage.set(''), 4000);
  }

}
