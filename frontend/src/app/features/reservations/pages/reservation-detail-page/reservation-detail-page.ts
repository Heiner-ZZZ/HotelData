import { httpResource, HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal, ViewEncapsulation } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import type { ApiError } from '../../../../core/api/api-error.model';
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
import type { ReservationDetailViewModel } from '../../models/reservations.model';
import type { ReservationDetailDto } from '../../models/reservations.dto';
import { mapReservationDetail } from '../../mappers/reservations.mapper';
import { ReservationsApiService } from '../../services/reservations-api.service';
import { ReservationActionService } from '../../services/reservation-action.service';
import { ProductsApiService } from '../../../admin/services/products-api.service';
import type { BookingLineItem, HotelProduct } from '../../../admin/models/products.model';
import { InStayApiService } from '../../../in-stay/services/in-stay-api.service';
import { canAssignRooms, canEditBooking } from '../../utils/reservation-status.util';

interface EditForm {
  checkInDate: string;
  checkOutDate: string;
  rooms: number;
  comment: string;
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
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly productsApi = inject(ProductsApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly instayApi = inject(InStayApiService);
  private readonly actionService = inject(ReservationActionService);
  private readonly router = inject(Router);

  readonly cancelPending = signal(false);
  readonly confirmPending = signal(false);
  readonly rejectPending = signal(false);
  readonly successMessage = signal('');

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

  readonly viewState = computed<ViewState>(() => {
    if (this.detailResource.isLoading()) return 'loading';
    const err = this.detailResource.error();
    if (err) {
      const status = err instanceof HttpErrorResponse ? err.status : undefined;
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
  readonly productsResource = httpResource<HotelProduct[]>(() => {
    const vm = this.detailResource.value();
    return vm ? `/admin/products?prop_id=${vm.propId}` : undefined;
  });

  readonly lineItemsResource = httpResource<BookingLineItem[]>(() => {
    const vm = this.detailResource.value();
    return vm ? `/admin/bookings/${vm.bookingId}/line-items` : undefined;
  });

  readonly hotelProducts = computed(() => this.productsResource.value() ?? []);
  readonly productsState = computed<ViewState>(() => {
    if (this.productsResource.isLoading()) return 'loading';
    if (this.productsResource.error()) return 'error';
    return this.productsResource.value()?.length ? 'success' : 'empty';
  });
  readonly lineItems = computed(() => this.lineItemsResource.value() ?? []);
  readonly lineItemsState = computed<ViewState>(() => {
    if (this.lineItemsResource.isLoading()) return 'loading';
    if (this.lineItemsResource.error()) return 'error';
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
  readonly availableRoomsResource = httpResource<any>(() => {
    const id = this.availableRoomsTrigger();
    return id ? `/reservations/${id}/available-rooms` : undefined;
  });

  // Room assignment modal
  readonly showRoomModal = signal(false);
  readonly roomAssignmentState = signal<'loading' | 'success' | 'error' | 'idle'>('idle');
  readonly availableRooms = signal<Array<{ hotel_room_id: string; room_number: string; room_label: string; floor: string; room_status: string }>>([]);
  readonly assignedRoomIds = signal<string[]>([]);
  readonly selectedRoomIds = signal<Set<string>>(new Set());
  readonly roomAssignmentSaving = signal(false);
  readonly roomAssignmentMessage = signal('');
  readonly roomsRequired = signal(0);

  readonly isStaff = computed(() => {
    const role = this.authService.currentUser()?.primaryRole;
    return role ? ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'].includes(role) : false;
  });

  readonly canConfirm = computed(() => {
    const vm = this.detailResource.value();
    return vm && vm.status === 'pending' && this.isStaff();
  });

  readonly canReject = computed(() => this.canConfirm());

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
    }).pipe(
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
    });
    if (!ok) return;
    this.productError.set('');
    this.removeItemSaving.set(itemId);
    this.productsApi.removeLineItem(vm.bookingId, itemId).pipe(
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
          this.successMessage.set('Reserva modificada exitosamente.');
          setTimeout(() => this.successMessage.set(''), 4000);
        },
        error: (err: unknown) => {
          const message = err instanceof HttpErrorResponse
            ? err.error?.message ?? err.message
            : (err as { message?: string }).message;
          this.editError.set(message || 'Error al modificar la reserva');
          this.editSaving.set(false);
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
    });
    if (!ok) return;
    this.executeCancel(bookingId);
  }

  private executeCancel(bookingId: string) {
    this.cancelPending.set(true);
    this.reservationsApi
      .cancelReservation(bookingId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => { this.detailResource.reload(); this.cancelPending.set(false); },
        error: () => { this.cancelPending.set(false); }
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
    this.instayApi.getMyStaySession(bookingId).subscribe({
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
