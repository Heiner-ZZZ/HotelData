import { CurrencyPipe, DatePipe, PercentPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { distinctUntilChanged, map, switchMap, tap } from 'rxjs';
import { AuthService } from '../../../../core/auth/auth.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { ReservationTimelineComponent } from './components/reservation-timeline';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReservationDetailViewModel } from '../../models/reservations.model';
import { ReservationsApiService } from '../../services/reservations-api.service';
import { ProductsApiService } from '../../../admin/services/products-api.service';
import type { BookingLineItem, HotelProduct } from '../../../admin/models/products.model';

interface EditForm {
  checkInDate: string;
  checkOutDate: string;
  rooms: number;
  comment: string;
}

@Component({
  selector: 'app-reservation-detail-page',
  imports: [CurrencyPipe, DatePipe, PercentPipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReservationTimelineComponent, RouterLink, StatusBadgeComponent, FormsModule],
  templateUrl: './reservation-detail-page.html',
  styleUrl: './reservation-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReservationDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly productsApi = inject(ProductsApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<ReservationDetailViewModel | null>(null);
  readonly cancelPending = signal(false);
  readonly confirmPending = signal(false);
  readonly rejectPending = signal(false);
  readonly successMessage = signal('');

  // Edit booking
  readonly editMode = signal(false);
  readonly editForm = signal<EditForm>({ checkInDate: '', checkOutDate: '', rooms: 1, comment: '' });
  readonly editSaving = signal(false);
  readonly editError = signal('');

  // Products (add-on services)
  readonly Math = Math; // Expose Math for template expressions
  readonly productsState = signal<ViewState>('idle');
  readonly lineItemsState = signal<ViewState>('idle');
  readonly hotelProducts = signal<HotelProduct[]>([]);
  readonly lineItems = signal<BookingLineItem[]>([]);
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
    const vm = this.data();
    return vm && ['confirmed', 'checked_in'].includes(vm.status) && this.isStaff();
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
    const vm = this.data();
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
    const vm = this.data();
    if (!vm) return false;
    if (['cancelled', 'rejected', 'checked_in', 'checked_out'].includes(vm.status)) return false;
    const today = this.todayStr();
    return today < vm.checkOutDate;
  });

  constructor() {
    this.loadDetail();
  }

  // ── Products (Add-on Services) ──

  loadProducts() {
    const vm = this.data();
    if (!vm) return;
    this.productsState.set('loading');
    this.lineItemsState.set('loading');

    this.productsApi.listHotelProducts(vm.propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (products) => {
        this.hotelProducts.set(products);
        this.productsState.set(products.length ? 'success' : 'empty');
      },
      error: () => this.productsState.set('error'),
    });

    this.productsApi.getLineItems(vm.bookingId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (items) => {
        this.lineItems.set(items);
        this.lineItemsState.set(items.length ? 'success' : 'empty');
      },
      error: () => this.lineItemsState.set('error'),
    });
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
    const vm = this.data();
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

  removeLineItem(itemId: string) {
    const vm = this.data();
    if (!vm) return;
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
    const vm = this.data();
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

  saveEdit() {
    const vm = this.data();
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
      .pipe(
        switchMap(() => this.reservationsApi.getReservationDetail(vm.bookingId)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (detail) => {
          this.data.set(detail);
          this.editMode.set(false);
          this.editSaving.set(false);
          this.successMessage.set('Reserva modificada exitosamente.');
          setTimeout(() => this.successMessage.set(''), 4000);
        },
        error: (err: ApiError) => {
          this.editError.set(err.message || 'Error al modificar la reserva');
          this.editSaving.set(false);
        },
      });
  }

  cancelReservation() {
    const current = this.data();
    if (!current || !current.canCancel || this.cancelPending()) return;
    this.cancelPending.set(true);
    this.reservationsApi
      .cancelReservation(current.bookingId)
      .pipe(switchMap(() => this.reservationsApi.getReservationDetail(current.bookingId)), takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (detail) => { this.data.set(detail); this.cancelPending.set(false); },
        error: () => { this.viewState.set('error'); this.cancelPending.set(false); }
      });
  }

  confirmReservation() {
    const current = this.data();
    if (!current || !this.canConfirm() || this.confirmPending()) return;
    this.confirmPending.set(true);
    this.successMessage.set('');
    this.reservationsApi
      .confirmReservation(current.bookingId)
      .pipe(switchMap(() => this.reservationsApi.getReservationDetail(current.bookingId)), takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (detail) => {
          this.data.set(detail);
          this.confirmPending.set(false);
          this.successMessage.set('Reserva confirmada exitosamente.');
          setTimeout(() => this.successMessage.set(''), 4000);
        },
        error: () => { this.confirmPending.set(false); }
      });
  }

  rejectReservation() {
    const current = this.data();
    if (!current || !this.canReject() || this.rejectPending()) return;
    this.rejectPending.set(true);
    this.successMessage.set('');
    this.reservationsApi
      .rejectReservation(current.bookingId)
      .pipe(switchMap(() => this.reservationsApi.getReservationDetail(current.bookingId)), takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (detail) => {
          this.data.set(detail);
          this.rejectPending.set(false);
          this.successMessage.set('Reserva rechazada.');
          setTimeout(() => this.successMessage.set(''), 4000);
        },
        error: () => { this.rejectPending.set(false); }
      });
  }

  // ── Room Assignment ──

  openRoomModal() {
    const vm = this.data();
    if (!vm) return;
    this.showRoomModal.set(true);
    this.roomAssignmentState.set('loading');
    this.roomAssignmentMessage.set('');
    this.selectedRoomIds.set(new Set());

    this.reservationsApi.getAvailableRooms(vm.bookingId).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (result) => {
        this.availableRooms.set(result.available_rooms);
        this.assignedRoomIds.set(result.assigned_rooms || []);
        this.roomsRequired.set(result.rooms_required);
        // Pre-select already assigned rooms
        if (result.assigned_rooms && result.assigned_rooms.length > 0) {
          this.selectedRoomIds.set(new Set(result.assigned_rooms));
        }
        this.roomAssignmentState.set('success');
      },
      error: () => {
        this.roomAssignmentState.set('error');
      }
    });
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
    const vm = this.data();
    if (!vm) return;
    const selected = [...this.selectedRoomIds()];
    if (selected.length === 0) return;

    this.roomAssignmentSaving.set(true);
    this.roomAssignmentMessage.set('');

    this.reservationsApi.assignRooms(vm.bookingId, selected).pipe(
      switchMap(() => this.reservationsApi.getReservationDetail(vm.bookingId)),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (detail) => {
        this.data.set(detail);
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

  private loadDetail() {
    this.activatedRoute.paramMap
      .pipe(
        map((params) => params.get('bookingId') ?? ''),
        distinctUntilChanged(),
        tap(() => this.viewState.set('loading')),
        switchMap((bookingId) => this.reservationsApi.getReservationDetail(bookingId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (detail) => {
          this.data.set(detail);
          this.viewState.set('success');
          this.loadProducts();
        },
        error: (error: ApiError) => { this.viewState.set(error.status === 404 ? 'empty' : 'error'); }
      });
  }

}
