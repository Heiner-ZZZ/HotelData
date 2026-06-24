import { CurrencyPipe, DatePipe, PercentPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { distinctUntilChanged, map, switchMap, tap, forkJoin } from 'rxjs';
import { AuthService } from '../../../../core/auth/auth.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReservationDetailViewModel } from '../../models/reservations.model';
import { ReservationsApiService } from '../../services/reservations-api.service';

interface RoomGuestEntry {
  roomIndex: number;
  guests: { guestName: string; guestEmail: string; guestPhone: string; age: number | null; isChild: boolean; isPrimaryForRoom: boolean }[];
}

interface EditForm {
  checkInDate: string;
  checkOutDate: string;
  rooms: number;
  comment: string;
}

@Component({
  selector: 'app-reservation-detail-page',
  imports: [CurrencyPipe, DatePipe, PercentPipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, RouterLink, StatusBadgeComponent, FormsModule],
  templateUrl: './reservation-detail-page.html',
  styleUrl: './reservation-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReservationDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<ReservationDetailViewModel | null>(null);
  readonly cancelPending = signal(false);
  readonly confirmPending = signal(false);
  readonly rejectPending = signal(false);
  readonly successMessage = signal('');

  // Room guests
  readonly roomGuests = signal<RoomGuestEntry[]>([]);
  readonly guestsLoading = signal(false);
  readonly guestsSaving = signal(false);
  readonly guestsEditMode = signal(false);

  // Edit booking
  readonly editMode = signal(false);
  readonly editForm = signal<EditForm>({ checkInDate: '', checkOutDate: '', rooms: 1, comment: '' });
  readonly editSaving = signal(false);
  readonly editError = signal('');

  // Review form
  readonly reviewSuccess = signal(false);
  readonly showReviewForm = computed(() => {
    const vm = this.data();
    return vm && vm.status === 'checked_out' && !this.reviewSuccess();
  });
  readonly reviewForm = signal({ rating: 0, title: '', comment: '' });
  readonly reviewSubmitting = signal(false);

  readonly isStaff = computed(() => {
    const role = this.authService.currentUser()?.primaryRole;
    return role ? ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'].includes(role) : false;
  });

  readonly canConfirm = computed(() => {
    const vm = this.data();
    return vm && vm.status === 'pending' && this.isStaff();
  });

  readonly canReject = computed(() => this.canConfirm());

  readonly canEdit = computed(() => {
    const vm = this.data();
    return vm && !['cancelled', 'rejected', 'checked_in', 'checked_out'].includes(vm.status);
  });

  readonly canManageGuests = computed(() => {
    const vm = this.data();
    return vm && vm.status === 'confirmed' && vm.rooms > 0;
  });

  readonly totalRooms = computed(() => this.data()?.rooms || 1);

  constructor() {
    this.loadDetail();
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

  loadRoomGuests() {
    const vm = this.data();
    if (!vm) return;
    this.guestsLoading.set(true);
    this.reservationsApi.getRoomGuests(vm.bookingId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (items: any[]) => {
          const entries: RoomGuestEntry[] = items.map((item: any) => ({
            roomIndex: item.room_index,
            guests: (item.guests || []).map((g: any) => ({
              guestName: g.guest_name || '',
              guestEmail: g.guest_email || '',
              guestPhone: g.guest_phone || '',
              age: g.age ?? null,
              isChild: !!g.is_child,
              isPrimaryForRoom: !!g.is_primary_for_room,
            })),
          }));
          this.roomGuests.set(entries);
          this.guestsLoading.set(false);
        },
        error: () => this.guestsLoading.set(false),
      });
  }

  enterGuestsMode() {
    this.guestsEditMode.set(true);
    this.loadRoomGuests();
  }

  cancelGuestEdit() {
    this.guestsEditMode.set(false);
    this.roomGuests.set([]);
  }

  getRoomGuestsForIndex(idx: number): RoomGuestEntry {
    const existing = this.roomGuests().find(r => r.roomIndex === idx);
    if (existing) return existing;
    return { roomIndex: idx, guests: [] };
  }

  addGuestToRoom(roomIndex: number) {
    this.roomGuests.update(list => {
      const copy = [...list];
      const idx = copy.findIndex(r => r.roomIndex === roomIndex);
      if (idx >= 0) {
        copy[idx] = { ...copy[idx], guests: [...copy[idx].guests, { guestName: '', guestEmail: '', guestPhone: '', age: null, isChild: false, isPrimaryForRoom: copy[idx].guests.length === 0 }] };
      } else {
        copy.push({ roomIndex, guests: [{ guestName: '', guestEmail: '', guestPhone: '', age: null, isChild: false, isPrimaryForRoom: true }] });
      }
      return copy;
    });
  }

  removeGuestFromRoom(roomIndex: number, guestIdx: number) {
    this.roomGuests.update(list => {
      const copy = [...list];
      const idx = copy.findIndex(r => r.roomIndex === roomIndex);
      if (idx >= 0) {
        const guests = [...copy[idx].guests];
        guests.splice(guestIdx, 1);
        copy[idx] = { ...copy[idx], guests };
      }
      return copy;
    });
  }

  updateGuestField(roomIndex: number, guestIdx: number, field: string, value: any) {
    this.roomGuests.update(list => {
      const copy = [...list];
      const idx = copy.findIndex(r => r.roomIndex === roomIndex);
      if (idx >= 0) {
        const guests = [...copy[idx].guests];
        guests[guestIdx] = { ...guests[guestIdx], [field]: value };
        copy[idx] = { ...copy[idx], guests };
      }
      return copy;
    });
  }

  saveRoomGuests() {
    const vm = this.data();
    if (!vm || this.guestsSaving()) return;
    this.guestsSaving.set(true);
    const payload = this.roomGuests().map(entry => ({
      room_index: entry.roomIndex,
      guests: entry.guests.map(g => ({
        guest_name: g.guestName,
        guest_email: g.guestEmail,
        guest_phone: g.guestPhone,
        age: g.age,
        is_child: g.isChild,
        is_primary_for_room: g.isPrimaryForRoom,
      })),
    }));
    this.reservationsApi.saveRoomGuests(vm.bookingId, payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.guestsSaving.set(false);
          this.guestsEditMode.set(false);
          this.roomGuests.set([]);
          this.successMessage.set('Datos de huéspedes guardados correctamente.');
          setTimeout(() => this.successMessage.set(''), 4000);
        },
        error: () => {
          this.guestsSaving.set(false);
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

  parseAge(value: string): number | null {
    const n = parseInt(value, 10);
    return isNaN(n) ? null : n;
  }

  goToInvoice(invoiceId: string) {
    this.router.navigate(['/account/billing', invoiceId]);
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
        next: (detail) => { this.data.set(detail); this.viewState.set('success'); },
        error: (error: ApiError) => { this.viewState.set(error.status === 404 ? 'empty' : 'error'); }
      });
  }

  setReviewRating(rating: number) {
    this.reviewForm.update(f => ({ ...f, rating }));
  }

  submitReview() {
    const vm = this.data();
    if (!vm || this.reviewSubmitting()) return;
    const f = this.reviewForm();
    if (f.rating === 0) return;

    this.reviewSubmitting.set(true);
    this.reservationsApi.createGuestReview(vm.bookingId, vm.propId, f.rating, f.title, f.comment)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.reviewSubmitting.set(false);
          this.reviewSuccess.set(true);
          this.successMessage.set('¡Gracias por tu reseña!');
          setTimeout(() => this.successMessage.set(''), 4000);
        },
        error: () => {
          this.reviewSubmitting.set(false);
        }
      });
  }
}
