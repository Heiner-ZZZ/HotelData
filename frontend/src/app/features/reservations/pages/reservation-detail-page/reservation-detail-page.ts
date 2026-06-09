import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap, tap } from 'rxjs';

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
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, RouterLink],
  templateUrl: './reservation-detail-page.html',
  styleUrl: './reservation-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReservationDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reservationsApi = inject(ReservationsApiService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<ReservationDetailViewModel | null>(null);
  readonly cancelPending = signal(false);

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
