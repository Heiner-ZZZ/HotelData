import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { CheckInsApiService, type CheckInDetailDto } from '../../services/check-ins-api.service';

interface StepConfig {
  num: number;
  label: string;
  icon: string;
}

const STEPS: StepConfig[] = [
  { num: 1, label: 'Huésped', icon: 'person' },
  { num: 2, label: 'Llegada', icon: 'login' },
  { num: 3, label: 'Verificación', icon: 'fact_check' },
  { num: 4, label: 'Notas', icon: 'edit_note' },
  { num: 5, label: 'Completar', icon: 'check_circle' },
];

@Component({
  selector: 'app-check-in-detail-page',
  imports: [RouterLink, LoadingStateComponent, ErrorStateComponent, EmptyStateComponent],
  templateUrl: './check-in-detail-page.html',
  styleUrl: './check-in-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckInDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly api = inject(CheckInsApiService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<CheckInDetailDto | null>(null);
  readonly successMessage = signal('');
  readonly errorMessage = signal('');

  // ── Wizard state ──
  readonly currentStep = signal(1);
  protected readonly Math = Math;
  readonly steps = STEPS;

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
  readonly checkinDone = computed(() => this.data()?.stay_status === 'checked_in');

  // ── Financial computed ──
  readonly totalPrice = computed(() => this.data()?.total_price ?? 0);
  readonly totalNights = computed(() => this.data()?.total_nights ?? 0);
  readonly pricePerNight = computed(() => {
    const total = this.totalPrice();
    const nights = this.totalNights();
    return nights > 0 ? Math.round((total / nights) * 100) / 100 : 0;
  });
  readonly currency = computed(() => this.data()?.currency ?? 'USD');

  // ── Room statuses ──
  readonly assignedRoomsStatuses = computed(() => {
    const d = this.data();
    return d?.assigned_rooms?.map((r) => ({
      label: r.room_label || r.room_number || r.hotel_room_id,
      status: r.room_status || 'unknown',
      ok: (r.room_status || 'unknown') === 'available',
    })) ?? [];
  });

  readonly allRoomsAvailable = computed(() =>
    this.assignedRoomsStatuses().length > 0 && this.assignedRoomsStatuses().every((r) => r.ok)
  );

  // ── Navigation ──
  readonly canGoNext = computed(() => {
    const step = this.currentStep();
    if (step === 5) return true;
    return true; // all steps navigable
  });

  constructor() {
    this.activatedRoute.paramMap
      .pipe(
        map((params) => params.get('bookingId') ?? ''),
        distinctUntilChanged(),
        map((bookingId) => {
          this.viewState.set('loading');
          return bookingId;
        }),
        switchMap((bookingId) => this.api.getCheckInDetail(bookingId)),
        takeUntilDestroyed(this.destroyRef),
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
          if (detail.stay_status === 'checked_in') this.currentStep.set(5);
          this.viewState.set('success');
        },
        error: (err: ApiError) => {
          this.viewState.set(err.status === 404 ? 'empty' : 'error');
        },
      });
  }

  goToStep(n: number): void {
    if (n >= 1 && n <= 5) this.currentStep.set(n);
  }

  nextStep(): void {
    if (this.currentStep() < 5) this.currentStep.update((s) => s + 1);
  }

  prevStep(): void {
    if (this.currentStep() > 1) this.currentStep.update((s) => s - 1);
  }

  completeCheckIn(): void {
    const d = this.data();
    if (!d || this.completing()) return;
    this.completing.set(true);
    this.completeError.set('');

    this.api
      .completeCheckInWithDetail(d.booking_id, {
        check_in_arrival_time: this.arrivalTime(),
        check_in_has_companions: this.hasCompanions(),
        check_in_companions_count: this.companionsCount(),
        check_in_document_verified: this.documentVerified(),
        check_in_keys_delivered: this.keysDelivered(),
        check_in_payment_pending: this.paymentPending(),
        check_in_deposit_received: this.depositReceived(),
        check_in_privacy_signed: this.privacySigned(),
        check_in_observations: this.observations(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.completing.set(false);
          this.successMessage.set(`Check-in completado — Folio: ${result.folio || 'N/A'}`);
          this.currentStep.set(5);
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

  roomStatusColor(status: string): string {
    const map: Record<string, string> = {
      available: '#16a34a', occupied: '#006076', cleaning: '#d97706',
      clean: '#059669', inspected: '#4338ca', dirty: '#92400e',
      maintenance: '#ba1a1a', out_of_order: '#ba1a1a', out_of_service: '#6f797d',
    };
    return map[status] ?? '#6f797d';
  }

  roomStatusLabel(status: string): string {
    const map: Record<string, string> = {
      available: 'Disponible', occupied: 'Ocupada', cleaning: 'Limpieza',
      clean: 'Limpia', inspected: 'Inspeccionada', dirty: 'Sucia',
      maintenance: 'Mantenimiento', out_of_order: 'Fuera Servicio',
      out_of_service: 'Fuera Servicio',
    };
    return map[status] ?? status;
  }
}
