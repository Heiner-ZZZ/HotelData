import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { distinctUntilChanged, map, switchMap, tap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { CheckInsApiService, type CheckInDetailDto } from '../../services/check-ins-api.service';

@Component({
  selector: 'app-check-in-detail-page',
  imports: [CurrencyPipe, FormsModule, RouterLink, LoadingStateComponent, ErrorStateComponent, EmptyStateComponent],
  templateUrl: './check-in-detail-page.html',
  styleUrl: './check-in-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckInDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly api = inject(CheckInsApiService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<CheckInDetailDto | null>(null);
  readonly successMessage = signal('');
  readonly errorMessage = signal('');

  // ── Check-in fields ──
  readonly arrivalTime = signal('');
  readonly hasCompanions = signal(false);
  readonly companionsCount = signal(0);
  readonly documentVerified = signal(false);
  readonly keysDelivered = signal(false);
  readonly paymentPending = signal(false);
  readonly depositReceived = signal(false);
  readonly privacySigned = signal(false);
  readonly observations = signal('');

  // ── Completion ──
  readonly completing = signal(false);
  readonly completeError = signal('');

  readonly Math = Math;
  readonly canComplete = signal(false);

  constructor() {
    this.activatedRoute.paramMap
      .pipe(
        map(params => params.get('bookingId') ?? ''),
        distinctUntilChanged(),
        tap(() => this.viewState.set('loading')),
        switchMap(bookingId => this.api.getCheckInDetail(bookingId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (detail) => {
          this.data.set(detail);
          this.arrivalTime.set(detail.check_in_arrival_time || '');
          this.hasCompanions.set(detail.check_in_has_companions || false);
          this.companionsCount.set(detail.check_in_companions_count || 0);
          this.documentVerified.set(detail.check_in_document_verified || false);
          this.keysDelivered.set(detail.check_in_keys_delivered || false);
          this.paymentPending.set(detail.check_in_payment_pending || false);
          this.depositReceived.set(detail.check_in_deposit_received || false);
          this.privacySigned.set(detail.check_in_privacy_signed || false);
          this.observations.set(detail.check_in_observations || '');
          this.canComplete.set(detail.assigned_rooms.length > 0 && detail.stay_status !== 'checked_in');
          this.viewState.set('success');
        },
        error: (err: ApiError) => {
          this.viewState.set(err.status === 404 ? 'empty' : 'error');
        }
      });
  }

  completeCheckIn(): void {
    const d = this.data();
    if (!d || this.completing()) return;
    this.completing.set(true);
    this.completeError.set('');

    this.api.completeCheckInWithDetail(d.booking_id, {
      check_in_arrival_time: this.arrivalTime(),
      check_in_has_companions: this.hasCompanions(),
      check_in_companions_count: this.companionsCount(),
      check_in_document_verified: this.documentVerified(),
      check_in_keys_delivered: this.keysDelivered(),
      check_in_payment_pending: this.paymentPending(),
      check_in_deposit_received: this.depositReceived(),
      check_in_privacy_signed: this.privacySigned(),
      check_in_observations: this.observations(),
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        this.completing.set(false);
        this.successMessage.set(`✅ Check-in completado — Folio: ${result.folio || 'N/A'}`);
        this.canComplete.set(false);
        // Reload
        this.api.getCheckInDetail(d.booking_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: (updated) => this.data.set(updated),
        });
      },
      error: (err: ApiError) => {
        this.completing.set(false);
        this.completeError.set(err.message || 'Error al completar check-in.');
      },
    });
  }

  roomLabel(r: CheckInDetailDto['assigned_rooms'][number]): string {
    return r.room_label || r.room_number || r.hotel_room_id;
  }
}
