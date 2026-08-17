import { HttpErrorResponse, httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, HostListener, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { getErrorStatus, getErrorMessage } from '../../../../shared/utils/http-error.util';
import { catchAndToastWarning } from '../../../../shared/utils/catch-and-toast';

import { AuthService } from '../../../../core/auth/auth.service';
import { CHECK_INS_EARLY_APPROVE, CHECK_INS_NO_SHOW_REOPEN } from '../../../../core/auth/permission.constants';
import { OperationModeService, type OperationMode } from '../../../../core/services/operation-mode.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { NoShowService } from '../../../../shared/services/no-show.service';
import {
  CheckInsApiService,
  type CheckInDetailDto,
  type EarlyCheckInDto,
  type LateArrivalDto,
} from '../../services/check-ins-api.service';
import { STAY_CHECKED_IN, STAY_NO_SHOW } from '../../../reservations/utils/reservation-status.util';

interface StepConfig {
  num: number;
  label: string;
  icon: string;
}

/** Bloqueo del gate de depósito: montos estructurados del detail 409. */
interface DepositGateInfo {
  percent: number;
  minDeposit: number;
  paid: number;
  missing: number;
  message: string;
}

/** Forma del ``detail`` estructurado que devuelve el backend en el 409. */
interface DepositGateDetail {
  code?: unknown;
  message?: unknown;
  deposit_percent?: unknown;
  min_deposit?: unknown;
  paid_total?: unknown;
  missing?: unknown;
}

const STEPS: StepConfig[] = [
  { num: 1, label: 'Huésped', icon: 'person' },
  { num: 2, label: 'Llegada', icon: 'login' },
  { num: 3, label: 'Verificación', icon: 'fact_check' },
  { num: 4, label: 'Notas', icon: 'edit_note' },
  { num: 5, label: 'Completar', icon: 'check_circle' },
];

const EMPTY_EARLY_CHECK_IN: EarlyCheckInDto = {
  enabled: true,
  is_early: false,
  minutes_before: 0,
  courtesy_minutes: 60,
  requires_approval: false,
  check_in_time: '',
  default_fee: 0,
};

/** Clave de fecha local YYYY-MM-DD desplazada `offsetDays` desde hoy. */
function localDateKey(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

const EMPTY_LATE_ARRIVAL: LateArrivalDto = {
  guaranteed_reservation: false,
  late_arrival_cutoff: '23:59',
  no_show_execution: 'next_day',
  declared_late_arrival: false,
  protected_from_auto_no_show: false,
  is_late_arrival_window: false,
  check_in_days_ago: null,
  blocked_reason: null,
};

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
  /** Gate de depósito (409 deposit_not_met): banner accionable con el faltante. */
  readonly depositGate = signal<DepositGateInfo | null>(null);

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

  // ── Late arrival (post-midnight window) ──
  /** Contexto servidor-autoritativo de llegada tardía / no-show. */
  readonly lateArrival = computed<LateArrivalDto>(() => this.data()?.late_arrival ?? EMPTY_LATE_ARRIVAL);
  /** Ventana abierta: el check-in era AYER y la reserva sigue checkeable como llegada tardía. */
  readonly isLateArrivalWindow = computed(() => this.lateArrival().is_late_arrival_window);
  /** Motivo de bloqueo del backend (no_show | stay_ended | too_late | null). */
  readonly lateArrivalBlockedReason = computed(() => this.lateArrival().blocked_reason);
  /** La llegada fue declarada (o el huésped marcó late_checkin) → protegida del auto no-show. */
  readonly declaredLateArrival = computed(() => this.lateArrival().declared_late_arrival);

  /**
   * Past-date validation refinada por la política de llegada tardía:
   * - AYER (ventana abierta) → se permite el check-in como ``late_arrival``,
   *   fechas intactas, sin recargos.
   * - 2+ días → no es check-in normal: no-show/gerente (bloqueado con motivo).
   */
  readonly isPastDate = computed(() => {
    const d = this.data();
    if (!d?.check_in_date) return false;
    const checkIn = new Date(d.check_in_date + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (checkIn >= today) return false;
    // Ayer = ventana de llegada tardía post-medianoche (permitido).
    if (this.isLateArrivalWindow()) return false;
    return true;
  });

  // ── Declarar llegada tardía (recepción) ──
  readonly lateArrivalDeclareOpen = signal(false);
  readonly lateArrivalDeclareValue = signal(false);
  readonly lateArrivalEta = signal('');
  readonly lateArrivalPending = signal(false);
  readonly lateArrivalError = signal('');
  /** Recepción puede declarar/retirar la llegada tardía con permiso de reservas. */
  readonly canDeclareLateArrival = computed(() => {
    const d = this.data();
    if (!d || this.checkinDone() || this.noShow()) return false;
    if (d.stay_status === STAY_NO_SHOW) return false;
    return this.auth.hasPermission('reservations.update');
  });

  /** Sprint 1: a future calendar date cannot be checked in yet.
   * Time-window and early-check-in authorization belong to the next sprint;
   * this gate intentionally compares only the hotel's current local day.
   */
  readonly isFutureDate = computed(() => {
    const d = this.data();
    if (!d?.check_in_date) return false;
    const checkIn = new Date(d.check_in_date + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return checkIn > today;
  });

  // ── Same-day early check-in ──
  /** Server-authoritative context; the frontend never decides the policy. */
  readonly earlyCheckIn = computed(() => this.data()?.early_check_in ?? EMPTY_EARLY_CHECK_IN);
  readonly canApproveEarlyCheckIn = computed(() => this.auth.hasPermission(CHECK_INS_EARLY_APPROVE));
  readonly earlyApprovalBlocked = computed(() =>
    this.earlyCheckIn().is_early && this.earlyCheckIn().requires_approval && !this.canApproveEarlyCheckIn()
  );
  readonly earlyDialogOpen = signal(false);
  readonly earlyDialogMode = signal<'early_courtesy' | 'early_approved'>('early_courtesy');
  readonly earlyCheckInReason = signal('');
  readonly earlyCheckInFee = signal(0);
  readonly earlyDialogError = signal('');
  private earlyDialogTrigger: HTMLElement | null = null;

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

  // ── Marca de reapertura: el huésped llegó tras el no-show ──
  /**
   * Aviso para recepción cuando el gerente reabrió la reserva: el huésped NO
   * llegó a tiempo, se marcó no-show y luego llegó — por eso el gerente la
   * reabrió. Se muestra mientras la ventana de reapertura siga abierta
   * (check-in de hoy o ayer + estadía vigente, misma regla que el botón de
   * reapertura): fuera de la ventana el panel de llegada tardía ya explica el
   * bloqueo y un aviso de "reabierta" sería engañoso.
   */
  readonly reopenedNotice = computed<{
    date: string;
    by: string;
    reason: string;
    penaltyRemoved: boolean;
  } | null>(() => {
    const d = this.data();
    if (!d?.no_show_reopened_at) return null;
    if (d.stay_status === STAY_NO_SHOW) return null;
    const today = localDateKey();
    if (d.check_in_date && d.check_in_date < today && d.check_in_date !== localDateKey(-1)) {
      return null;
    }
    if (d.check_out_date && d.check_out_date < today) {
      return null;
    }
    return {
      date: d.no_show_reopened_at,
      by: d.no_show_reopened_by || '',
      reason: d.no_show_reopen_reason || '',
      penaltyRemoved: !!d.no_show_penalty_removed,
    };
  });

  /** Fecha legible (es-MX) de la reapertura; passthrough si el valor no parsea. */
  formatReopenDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat('es-MX', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }

  // ── No-show manual (cierre desde recepción) ──
  readonly noShowPending = signal(false);
  /**
   * Folio de la penalización generado al marcar no-show (respuesta del API).
   * Se muestra en el panel para enlazar a Facturación; se limpia al cambiar
   * de reserva (no al recargar el detalle, para que persista tras el reload).
   */
  readonly noShowResult = signal<{ folio_number: string | null; penalty_amount: number } | null>(null);
  /** Server-backed fallback so the folio link survives a page reload or navigation.
   * The transient result is still preferred immediately after marking no-show.
   */
  readonly noShowFolio = computed(() => {
    const result = this.noShowResult();
    if (result) return result;
    const d = this.data();
    if (!d || d.stay_status !== STAY_NO_SHOW) return null;
    return {
      folio_number: d.folio,
      penalty_amount: d.no_show_penalty_amount ?? 0,
    };
  });

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

  openLateArrivalDeclare(): void {
    this.lateArrivalDeclareValue.set(this.declaredLateArrival());
    this.lateArrivalEta.set(this.data()?.estimated_arrival_time || '');
    this.lateArrivalError.set('');
    this.lateArrivalDeclareOpen.set(true);
  }

  saveLateArrivalDeclaration(): void {
    const d = this.data();
    if (!d || this.lateArrivalPending() || !this.canDeclareLateArrival()) return;
    const declared = this.lateArrivalDeclareValue();
    const eta = this.lateArrivalEta().trim();
    this.lateArrivalPending.set(true);
    this.lateArrivalError.set('');
    this.api
      .declareLateArrival(d.booking_id, {
        declared_late_arrival: declared,
        estimated_arrival_time: eta || undefined,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.lateArrivalPending.set(false);
          this.lateArrivalDeclareOpen.set(false);
          this.successMessage.set(
            declared
              ? 'Llegada tardía declarada — la reserva queda protegida del auto no-show.'
              : 'Llegada tardía retirada.',
          );
          this.detailResource.reload();
        },
        error: (err: ApiError) => {
          this.lateArrivalPending.set(false);
          this.lateArrivalError.set(err.message || 'No fue posible guardar la declaración de llegada tardía.');
        },
      });
  }

  // ── No-show reopen (gerente): el huésped llegó tras el cierre del no-show ──
  /**
   * Reapertura = gerente + reserva no_show + DENTRO de la ventana (check-in de
   * hoy o ayer con estadía vigente). Reabrir un no-show antiguo colapsaría la
   * estancia con las de otras fechas (inventario, folios, facturación).
   */
  readonly canReopenNoShow = computed(() => {
    const d = this.data();
    if (!d || d.stay_status !== STAY_NO_SHOW) return false;
    if (!this.auth.hasPermission(CHECK_INS_NO_SHOW_REOPEN)) return false;
    return this.reopenWindowBlockedReason() === null;
  });
  /** `too_late` | `stay_ended` cuando el no-show está FUERA de la ventana de
   *  reapertura (con permiso gerencial); null si reabrir está disponible. */
  readonly reopenWindowBlockedReason = computed<string | null>(() => {
    const d = this.data();
    if (!d || d.stay_status !== STAY_NO_SHOW) return null;
    if (!this.auth.hasPermission(CHECK_INS_NO_SHOW_REOPEN)) return null;
    const today = localDateKey();
    if (d.check_in_date && d.check_in_date < today && d.check_in_date !== localDateKey(-1)) {
      return 'too_late';
    }
    if (d.check_out_date && d.check_out_date < today) {
      return 'stay_ended';
    }
    return null;
  });
  readonly reopenDialogOpen = signal(false);
  readonly reopenReason = signal('');
  readonly reopenPending = signal(false);
  readonly reopenError = signal('');
  private reopenDialogTrigger: HTMLElement | null = null;

  openReopenDialog(): void {
    if (!this.canReopenNoShow()) return;
    this.reopenDialogTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    this.reopenReason.set('');
    this.reopenError.set('');
    this.reopenDialogOpen.set(true);
    setTimeout(() => {
      if (this.reopenDialogOpen()) document.getElementById('ciw-reopen-reason')?.focus();
    }, 0);
  }

  cancelReopenDialog(): void {
    this.reopenDialogOpen.set(false);
    this.reopenError.set('');
    queueMicrotask(() => this.reopenDialogTrigger?.focus());
    this.reopenDialogTrigger = null;
  }

  confirmReopenNoShow(): void {
    const d = this.data();
    if (!d || this.reopenPending() || !this.canReopenNoShow()) return;
    const reason = this.reopenReason().trim();
    if (!reason) {
      this.reopenError.set('Escribe el motivo de la reapertura antes de continuar.');
      return;
    }
    this.reopenPending.set(true);
    this.reopenError.set('');
    this.api
      .reopenNoShow(d.booking_id, reason)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.reopenPending.set(false);
          this.reopenDialogOpen.set(false);
          const penaltyNote = result.penalty_removed
            ? result.folio_deleted
              ? 'La penalización fue retirada: el folio de penalización se eliminó.'
              : result.reversal_amount && result.reversal_amount > 0
                ? `La penalización de $${Number(result.reversal_amount).toFixed(2)} fue revertida en el folio${result.folio_number ? ` (${result.folio_number})` : ''}: quedó un crédito a favor del huésped para gestionar en Facturación.`
                : 'La penalización fue retirada del folio.'
            : result.penalty_amount > 0
              ? `La penalización de $${Number(result.penalty_amount).toFixed(2)} quedó registrada en Facturación para su gestión.`
              : '';
          this.successMessage.set('Reserva reabierta — el huésped puede hacer check-in. ' + penaltyNote);
          this.detailResource.reload();
        },
        error: (err: ApiError) => {
          this.reopenPending.set(false);
          this.reopenError.set(err.message || 'No fue posible reabrir la reserva.');
        },
      });
  }

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
      this.reopenDialogOpen.set(false);
      this.reopenError.set('');
      this.depositGate.set(null);
      // Then overlay localStorage draft (if newer)
      this._restoreDraft();
      if (detail.stay_status === STAY_CHECKED_IN) this.currentStep.set(5);
      this.viewState.set('success');
    });

    // Modo CRUD reactivo: editar campos del wizard → UPDATE en el nav.
    // El cleanup es importante: el efecto se re-ejecuta con cada cambio de
    // campo y también debe liberar el overlay cuando la página se destruye.
    effect((onCleanup) => {
      const m = this._opMode();
      if (m.mode === 'read') return;
      onCleanup(this.opMode.setTransientMode(m.mode, m.detail));
    });

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
    if (!d || this.completing() || !this.keysDelivered() || this.isFutureDate()) return;
    if (!this.allRoomsAvailable()) {
      this.completeError.set('No se puede completar el check-in: hay habitaciones asignadas que no están disponibles (ocupadas, en mantenimiento, etc.). Asigna otras habitaciones antes de continuar.');
      return;
    }
    if (this.earlyCheckIn().is_early) {
      this.openEarlyCheckInDialog();
      return;
    }
    this.submitCheckIn();
  }

  openEarlyCheckInDialog(): void {
    const policy = this.earlyCheckIn();
    if (!policy.enabled) {
      this.completeError.set('El early check-in está deshabilitado para este hotel.');
      return;
    }
    if (policy.requires_approval && !this.canApproveEarlyCheckIn()) {
      this.completeError.set('Solo un gerente de hotel o super_admin puede aprobar este early check-in.');
      return;
    }
    this.earlyDialogTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    this.earlyDialogMode.set(policy.requires_approval ? 'early_approved' : 'early_courtesy');
    this.earlyCheckInReason.set('');
    this.earlyCheckInFee.set(policy.default_fee || 0);
    this.earlyDialogError.set('');
    this.earlyDialogOpen.set(true);
    // Angular renders the dialog after the signal update. A macrotask keeps
    // focus handoff after that render (a microtask could run while the node
    // is still absent, leaving keyboard users on the trigger).
    setTimeout(() => {
      if (this.earlyDialogOpen()) document.getElementById('ciw-early-dialog')?.focus();
    }, 0);
  }

  cancelEarlyCheckIn(): void {
    this.earlyDialogOpen.set(false);
    this.earlyDialogError.set('');
    queueMicrotask(() => this.earlyDialogTrigger?.focus());
    this.earlyDialogTrigger = null;
  }

  confirmEarlyCheckIn(): void {
    const mode = this.earlyDialogMode();
    const reason = this.earlyCheckInReason().trim();
    if (mode === 'early_approved' && !this.canApproveEarlyCheckIn()) {
      this.earlyDialogError.set('Solo un gerente de hotel o super_admin puede aprobar este early check-in.');
      return;
    }
    if (mode === 'early_approved' && !reason) {
      this.earlyDialogError.set('Escribe el motivo de la aprobación antes de continuar.');
      return;
    }
    this.earlyDialogOpen.set(false);
    this.earlyDialogError.set('');
    this.submitCheckIn({
      mode,
      reason,
      fee: Math.max(0, Number(this.earlyCheckInFee()) || 0),
    });
  }

  @HostListener('document:keydown.escape')
  onEscapeEarlyDialog(): void {
    if (this.earlyDialogOpen()) this.cancelEarlyCheckIn();
    if (this.reopenDialogOpen()) this.cancelReopenDialog();
  }

  private submitCheckIn(early?: {
    mode: 'early_courtesy' | 'early_approved';
    reason: string;
    fee: number;
  }): void {
    const d = this.data();
    if (!d || this.completing() || !this.keysDelivered() || this.isFutureDate()) return;

    this.completing.set(true);
    this.completeError.set('');
    this.depositGate.set(null);
    const earlyPayload = early
      ? {
          early_check_in_mode: early.mode,
          early_check_in_approved: true,
          early_check_in_reason: early.reason,
          early_check_in_fee: early.fee,
        }
      : {};

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
        ...earlyPayload,
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
          const gate = this.parseDepositGate(err);
          if (gate) {
            // 409 del gate de depósito → banner accionable con el monto
            // faltante, en lugar del toast genérico.
            this.depositGate.set(gate);
          } else {
            this.completeError.set(err.message || 'Error al completar check-in.');
          }
        },
      });
  }

  /**
   * Detecta el 409 ``deposit_not_met`` y extrae los montos estructurados.
   * Cubre el ``ApiError`` del interceptor (``details`` = body crudo) y el
   * ``HttpErrorResponse`` directo (specs).
   */
  private parseDepositGate(err: unknown): DepositGateInfo | null {
    if (err instanceof HttpErrorResponse) {
      if (err.status !== 409) return null;
      const body = err.error as { detail?: unknown } | null;
      return this.mapDepositDetail(body?.detail, err.message);
    }
    if (err && typeof err === 'object') {
      const anyErr = err as { status?: unknown; message?: unknown; details?: unknown };
      if (anyErr.status !== 409) return null;
      const body = anyErr.details as { detail?: unknown } | null;
      return this.mapDepositDetail(body?.detail, typeof anyErr.message === 'string' ? anyErr.message : undefined);
    }
    return null;
  }

  private mapDepositDetail(detail: unknown, fallbackMessage?: string): DepositGateInfo | null {
    if (!detail || typeof detail !== 'object') return null;
    const d = detail as DepositGateDetail;
    if (d.code !== 'deposit_not_met') return null;
    return {
      percent: Number(d.deposit_percent) || 0,
      minDeposit: Number(d.min_deposit) || 0,
      paid: Number(d.paid_total) || 0,
      missing: Number(d.missing) || 0,
      message: typeof d.message === 'string' && d.message ? d.message : fallbackMessage ?? '',
    };
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
