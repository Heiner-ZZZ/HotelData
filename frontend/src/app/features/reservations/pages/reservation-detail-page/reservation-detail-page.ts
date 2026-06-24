import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap, tap } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReservationDetailViewModel } from '../../models/reservations.model';
import { ReservationsApiService } from '../../services/reservations-api.service';

@Component({
  selector: 'app-reservation-detail-page',
  imports: [CurrencyPipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, RouterLink],
  templateUrl: './reservation-detail-page.html',
  styleUrl: './reservation-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReservationDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reservationsApi = inject(ReservationsApiService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<ReservationDetailViewModel | null>(null);
  readonly cancelPending = signal(false);
  readonly confirmPending = signal(false);
  readonly rejectPending = signal(false);
  readonly successMessage = signal('');

  readonly isStaff = computed(() => {
    const role = this.authService.currentUser()?.primaryRole;
    return role ? ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'].includes(role) : false;
  });

  readonly canConfirm = computed(() => {
    const vm = this.data();
    return vm && vm.status === 'pending' && this.isStaff();
  });

  readonly canReject = computed(() => this.canConfirm());

  constructor() {
    this.loadDetail();
  }

  cancelReservation() {
    const current = this.data();
    if (!current || !current.canCancel || this.cancelPending()) {
      return;
    }

    this.cancelPending.set(true);
    this.reservationsApi
      .cancelReservation(current.bookingId)
      .pipe(
        switchMap(() => this.reservationsApi.getReservationDetail(current.bookingId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (detail) => {
          this.data.set(detail);
          this.cancelPending.set(false);
        },
        error: () => {
          this.viewState.set('error');
          this.cancelPending.set(false);
        }
      });
  }

  confirmReservation() {
    const current = this.data();
    if (!current || !this.canConfirm() || this.confirmPending()) return;
    this.confirmPending.set(true);
    this.successMessage.set('');
    this.reservationsApi
      .confirmReservation(current.bookingId)
      .pipe(
        switchMap(() => this.reservationsApi.getReservationDetail(current.bookingId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (detail) => {
          this.data.set(detail);
          this.confirmPending.set(false);
          this.successMessage.set('Reserva confirmada exitosamente.');
          setTimeout(() => this.successMessage.set(''), 4000);
        },
        error: () => {
          this.confirmPending.set(false);
        }
      });
  }

  rejectReservation() {
    const current = this.data();
    if (!current || !this.canReject() || this.rejectPending()) return;
    this.rejectPending.set(true);
    this.successMessage.set('');
    this.reservationsApi
      .rejectReservation(current.bookingId)
      .pipe(
        switchMap(() => this.reservationsApi.getReservationDetail(current.bookingId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (detail) => {
          this.data.set(detail);
          this.rejectPending.set(false);
          this.successMessage.set('Reserva rechazada.');
          setTimeout(() => this.successMessage.set(''), 4000);
        },
        error: () => {
          this.rejectPending.set(false);
        }
      });
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
        },
        error: (error: ApiError) => {
          this.viewState.set(error.status === 404 ? 'empty' : 'error');
        }
      });
  }
}
