import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { getErrorStatus, getErrorMessage } from '../../../../shared/utils/http-error.util';
import { catchAndToastWarning } from '../../../../shared/utils/catch-and-toast';

import { AuthService } from '../../../../core/auth/auth.service';
import { OperationModeService, type OperationMode } from '../../../../core/services/operation-mode.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { NoShowService } from '../../../../shared/services/no-show.service';
import { CheckInsApiService, type CheckInDetailDto } from '../../services/check-ins-api.service';
import { STAY_CHECKED_IN, STAY_NO_SHOW } from '../../../reservations/utils/reservation-status.util';

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
  private readonly opMode = inject(OperationModeService);
  private readonly auth = inject(AuthService);
  private readonly noShowService = inject(NoShowService);

  readonly viewState = signal<ViewState>('loading');
  /**
   * Degradación elegante: httpResource.value() LANZA cuando el request falló
   * (ej. 403 check-ins.read) y todos los computeds derivados (_opMode,
   * totalPrice, assignedRoomsStatuses…) lo re-leerían → spam de consola en
   * cada recomputación. Con error presente devolvemos null y la vista pasa a
   * 'forbidden'/'error' sin lanzar.
   */
  readonly data = computed(() => {
    if (this.detailResource.error()) return null;
    return this.detailResource.value() ?? null;
  });
  readonly successMessage = signal('');
  readonly errorMessage = signal('');

  // ── Reactive route param → httpResource (re-fires on bookingId change) ──
  private readonly paramMap = toSignal(this.activatedRoute.paramMap, {
    initialValue: this.activatedRoute.snapshot.paramMap,
  });
  readonly bookingId = computed(() => this.paramMap().get('bookingId') ?? '');

  readonly detailResource = httpResource<CheckInDetailDto>(() => {
    const id = this.bookingId();
    return id ? `/management/check-ins/${id}/detail` : undefined;
  });

  /**
   * Id-gate for the wizard init effect: pre-fills the 8 backend-derived fields,
   * the localStorage overlay, and the currentStep exactly once per fetched
   * booking_id. Reloads after completeCheckIn() don't reset user edits.
   */
  private lastInitializedId: string | null = null;

  // ── Wizard state ──
  readonly currentStep = signal(1);
  protected readonly Math = Math;
  protected readonly Number = Number;
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

  /**
   * Modo CRUD reactivo: si algún campo del wizard difiere del estado guardado
   * en backend, el usuario está editando el check-in → UPDATE en el nav.
   */
  private readonly _opMode = computed<{ mode: OperationMode; detail: string }>(() => {
    const d = this.data();
    if (!d) return { mode: 'read', detail: '' };
    const edited =
      this.arrivalTime() !== (d.check_in_arrival_time || '') ||
      this.hasCompanions() !== (d.check_in_has_companions || false) ||
      this.companionsCount() !== (d.check_in_companions_count || 0) ||
      this.documentVerified() !== (d.check_in_document_verified || false) ||
      this.keysDelivered() !== (d.check_in_keys_delivered || false) ||
      this.paymentPending() !== (d.check_in_payment_pending || false) ||
      this.depositReceived() !== (d.check_in_deposit_received || false) ||
      this.privacySigned() !== (d.check_in_privacy_signed || false) ||
      this.observations() !== (d.check_in_observations || '');
    return edited
      ? { mode: 'update', detail: `Check-in ${d.booking_id}` }
      : { mode: 'read', detail: '' };
  });

  // ── Past-date validation ──
  readonly isPastDate = computed(() => {
    const d = this.data();
    if (!d?.check_in_date) return false;
    const checkIn = new Date(d.check_in_date + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return checkIn < today;
  });

  // ── No-show: guest never arrived and stay already ended ──
  // Una reserva marcada como no_show (estado terminal) o cuya fecha de
  // check-out ya pasó sin que el huésped llegara no admite check-in.
  readonly noShow = computed(() => {
    const d = this.data();
    if (!d || this.checkinDone()) return false;
    if (d.stay_status === STAY_NO_SHOW) return true;
    if (!d.check_out_date) return false;
    const checkOut = new Date(d.check_out_date + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return checkOut < today;
  });

  // ── Completion ──
  readonly completing = signal(false);
  readonly completeError = signal('');
  readonly checkinDone = computed(() => this.data()?.stay_status === STAY_CHECKED_IN);

  // ── No-show manual (cierre desde recepción) ──
  readonly noShowPending = signal(false);
  /**
   * Folio de la penalización generado al marcar no-show (respuesta del API).
   * Se muestra en el panel para enlazar a Facturación; se limpia al cambiar
   * de reserva (no al recargar el detalle, para que persista tras el reload).
   */
  readonly noShowResult = signal<{ folio_number: string | null; penalty_amount: number } | null>(null);

  /**
   * El botón solo aplica a reservas que VENCIERON como no-show pero aún no
   * fueron marcadas (stay_status ausente/pending). Las ya `no_show` y las
   * con estancia activa/terminal quedan excluidas. Gate por permiso
   * `reservations.update` — el mismo que exige el backend en el endpoint.
   */
  readonly canMarkNoShow = computed(() => {
    const d = this.data();
    if (!d || this.checkinDone() || !this.noShow()) return false;
    if (d.stay_status === STAY_NO_SHOW) return false;
    return this.auth.hasPermission('reservations.update');
  });

  async markNoShow() {
    const d = this.data();
    if (!d || !this.canMarkNoShow() || this.noShowPending()) return;

    this.noShowPending.set(true);
    this.successMessage.set('');
    this.errorMessage.set('');
    try {
      // Flujo compartido: diálogo de confirmación → POST no-show → folio.
      const result = await this.noShowService.markNoShowWithConfirm(d.booking_id, d.guest_name);
      if (!result) return; // cancelado — el finally libera el pending
      this.successMessage.set(this.noShowService.successMessage(result));
      this.noShowResult.set({
        folio_number: result.folio_number ?? null,
        penalty_amount: result.penalty_amount,
      });
      this.detailResource.reload();
    } catch (err) {
      this.errorMessage.set(getErrorMessage(err) || 'No fue posible marcar el no-show.');
    } finally {
      this.noShowPending.set(false);
    }
  }

  // ── Completion guard (button disabled while processing) ──
  // `completing()` is used directly in the template

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
      ok: (r.room_status || 'unknown') === 'available' || (r.room_status || 'unknown') === 'vacant_clean',
    })) ?? [];
  });

  readonly allRoomsAvailable = computed(() =>
    this.assignedRoomsStatuses().length > 0 && this.assignedRoomsStatuses().every((r) => r.ok)
  );

  // ── Navigation ──
  readonly canGoNext = computed(() => {
    const step = this.currentStep();
    if (step === 5) return true;
    // Block going to completion if it's a past date
    if (step === 4 && this.isPastDate()) return false;
    return true;
  });

  // ── Persistence key ──
  private storageKey = '';
  private readonly STORAGE_PREFIX = 'ciw_draft_';

  constructor() {
    // Single effect handles: error → viewState('error'|'empty'),
    // first fetch → bind storage key + pre-fill backend fields + overlay
    // localStorage draft + set currentStep if stay_status indicates completed.
    //
    // Id-gate ensures reload() after completeCheckIn() does NOT overwrite
    // user-edited wizard fields. The backend already received those edits via
    // completeCheckInWithDetail() call below.
    effect(() => {
      // Leer error() ANTES de value(): value() lanza cuando el request falló
      // (ej. 403) y este efecto se re-ejecuta durante el change detection →
      // el throw rompería la vista y spamearía la consola.
      const err = this.detailResource.error();
      if (err) {
        // getErrorStatus cubre HttpErrorResponse (tests) y ApiError del
        // interceptor (app en vivo) — ver shared/utils/http-error.util.ts.
        const status = getErrorStatus(err);
        // 403 check-ins.read → el rol no tiene permiso; no es un error del server.
        this.viewState.set(status === 403 ? 'forbidden' : (status === 404 ? 'empty' : 'error'));
        return;
      }

      const detail = this.detailResource.value();
      if (!detail) {
        this.viewState.set('loading');
        return;
      }
      if (this.lastInitializedId === detail.booking_id) return;
      this.lastInitializedId = detail.booking_id;

      this.storageKey = this.STORAGE_PREFIX + detail.booking_id;
      // Always restore backend-saved fields first
      this.arrivalTime.set(detail.check_in_arrival_time || '');
      this.hasCompanions.set(detail.check_in_has_companions || false);
      this.companionsCount.set(detail.check_in_companions_count || 0);
      this.documentVerified.set(detail.check_in_document_verified || false);
      this.keysDelivered.set(detail.check_in_keys_delivered || false);
      this.paymentPending.set(detail.check_in_payment_pending || false);
      this.depositReceived.set(detail.check_in_deposit_received || false);
      this.privacySigned.set(detail.check_in_privacy_signed || false);
      this.observations.set(detail.check_in_observations || '');
      // Nueva reserva → limpiar el folio de un no-show anterior
      this.noShowResult.set(null);
      // Then overlay localStorage draft (if newer)
      this._restoreDraft();
      if (detail.stay_status === STAY_CHECKED_IN) this.currentStep.set(5);
      this.viewState.set('success');
    }, { allowSignalWrites: true });

    // Modo CRUD reactivo: editar campos del wizard → UPDATE en el nav.
    // El cleanup es importante: el efecto se re-ejecuta con cada cambio de
    // campo y también debe liberar el overlay cuando la página se destruye.
    effect((onCleanup) => {
      const m = this._opMode();
      if (m.mode === 'read') return;
      onCleanup(this.opMode.setTransientMode(m.mode, m.detail));
    }, { allowSignalWrites: true });

    // Persist wizard fields to localStorage on every change
    effect(() => {
      // Read all signals to trigger tracking
      const draft = {
        step: this.currentStep(),
        arrivalTime: this.arrivalTime(),
        hasCompanions: this.hasCompanions(),
        companionsCount: this.companionsCount(),
        documentVerified: this.documentVerified(),
        keysDelivered: this.keysDelivered(),
        paymentPending: this.paymentPending(),
        depositReceived: this.depositReceived(),
        privacySigned: this.privacySigned(),
        observations: this.observations(),
      };
      this._persistDraft(draft);
    });
  }

  private _persistDraft(draft: Record<string, unknown>): void {
    if (!this.storageKey) return;
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(draft));
    } catch (err) {
      // Was silent — now logs dev + warning toast so dev sees when localStorage
      // is full/unavailable (was previously invisible, hiding hard-to-debug
      // "my draft didn't save" complaints).
      catchAndToastWarning('check-in.localStorage.persist', undefined)(err);
    }
  }

  private _restoreDraft(): void {
    if (!this.storageKey) return;
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) return;
      const saved = JSON.parse(raw) as Record<string, unknown>;
      if (saved['arrivalTime']) this.arrivalTime.set(String(saved['arrivalTime']));
      if (typeof saved['hasCompanions'] === 'boolean') this.hasCompanions.set(saved['hasCompanions']);
      if (typeof saved['companionsCount'] === 'number') this.companionsCount.set(saved['companionsCount']);
      if (typeof saved['documentVerified'] === 'boolean') this.documentVerified.set(saved['documentVerified']);
      if (typeof saved['keysDelivered'] === 'boolean') this.keysDelivered.set(saved['keysDelivered']);
      if (typeof saved['paymentPending'] === 'boolean') this.paymentPending.set(saved['paymentPending']);
      if (typeof saved['depositReceived'] === 'boolean') this.depositReceived.set(saved['depositReceived']);
      if (typeof saved['privacySigned'] === 'boolean') this.privacySigned.set(saved['privacySigned']);
      if (saved['observations']) this.observations.set(String(saved['observations']));
      if (typeof saved['step'] === 'number' && saved['step'] >= 1 && saved['step'] <= 5) {
        this.currentStep.set(saved['step']);
      }
    } catch (err) {
      // Corrupt JSON or storage access error — was silent; now visible.
      catchAndToastWarning('check-in.localStorage.restore', undefined)(err);
    }
  }

  /** Clear the draft from localStorage after successful check-in. */
  private _clearDraft(): void {
    if (!this.storageKey) return;
    try {
      localStorage.removeItem(this.storageKey);
    } catch (err) {
      // Was silent — now visible.
      catchAndToastWarning('check-in.localStorage.clear', undefined)(err);
    }
  }

  goToStep(n: number): void {
    if (n >= 1 && n <= 5) {
      // Don't allow skipping to step 5 if it's a past date (show warning on step 4 instead)
      if (n === 5 && this.isPastDate()) {
        this.currentStep.set(4);
        return;
      }
      this.currentStep.set(n);
    }
  }

  nextStep(): void {
    if (this.currentStep() < 5) this.currentStep.update((s) => s + 1);
  }

  prevStep(): void {
    if (this.currentStep() > 1) this.currentStep.update((s) => s - 1);
  }

  completeCheckIn(): void {
    const d = this.data();
    if (!d || this.completing() || !this.keysDelivered()) return;
    if (!this.allRoomsAvailable()) {
      this.completeError.set('No se puede completar el check-in: hay habitaciones asignadas que no están disponibles (ocupadas, en mantenimiento, etc.). Asigna otras habitaciones antes de continuar.');
      return;
    }
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
          this._clearDraft();
          this.successMessage.set(`Check-in completado — Folio: ${result.folio || 'N/A'}`);
          this.currentStep.set(5);
          // Refresh detail; the init effect's id-gate preserves user-edited
          // wizard fields across this refetch.
          this.detailResource.reload();
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
      available: '#16a34a', vacant_clean: '#16a34a', occupied: '#006076', cleaning: '#d97706',
      clean: '#059669', inspected: '#4338ca', dirty: '#92400e',
      maintenance: '#ba1a1a', out_of_order: '#ba1a1a', out_of_service: '#6f797d',
    };
    return map[status] ?? '#6f797d';
  }

  roomStatusLabel(status: string): string {
    const map: Record<string, string> = {
      available: 'Disponible', vacant_clean: 'Disponible', occupied_clean: 'Ocupada Limpia',
      occupied: 'Ocupada', cleaning: 'Limpieza', clean: 'Limpia',
      inspected: 'Inspeccionada', dirty: 'Sucia', occupied_dirty: 'Ocupada Sucia',
      vacant_dirty: 'Vacante Sucia', cleaning_in_progress: 'Limpieza en Progreso',
      cleaning_completed: 'Limpieza Completada', maintenance_requested: 'Mantenimiento Solicitado',
      maintenance: 'Mantenimiento', out_of_order: 'Fuera Servicio',
      out_of_service: 'Fuera Servicio',
    };
    return map[status] ?? status;
  }
}
