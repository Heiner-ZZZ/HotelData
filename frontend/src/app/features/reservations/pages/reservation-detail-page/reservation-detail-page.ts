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

  goToInvoice(invoiceId: string) {
    this.router.navigate(['/account/billing', invoiceId]);
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
        next: (detail) => { this.data.set(detail); this.viewState.set('success'); },
        error: (error: ApiError) => { this.viewState.set(error.status === 404 ? 'empty' : 'error'); }
      });
  }

}
