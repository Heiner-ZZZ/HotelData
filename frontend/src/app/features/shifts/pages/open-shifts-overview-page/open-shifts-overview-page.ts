import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { DatePipe, CurrencyPipe } from '@angular/common';
import { Router } from '@angular/router';

import { ToastService } from '../../../../shared/services/toast.service';
import { getErrorMessage } from '../../../../shared/utils/http-error.util';
import { formatCurrency } from '../../../../shared/utils/currency-format.util';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { type PermissionCode } from '../../../../core/auth/permission.constants';
import { OpenShiftOverview, ShiftsApiService } from '../../services/shifts-api.service';

/** A shift is "near expiry" (warning tone) once it reaches this fraction of its limit. */
const NEAR_LIMIT_RATIO = 0.75;

/** The overview re-fetches the open-shift list on this cadence (30 min). */
const AUTO_REFRESH_MS = 30 * 60 * 1000;

/** Live countdown tick (30 s) — keeps the "vence en" column fresh without churn. */
const COUNTDOWN_TICK_MS = 30_000;

@Component({
  selector: 'app-open-shifts-overview-page',
  imports: [DatePipe, CurrencyPipe],
  templateUrl: './open-shifts-overview-page.html',
  styleUrl: './open-shifts-overview-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OpenShiftsOverviewPageComponent {
  private readonly api = inject(ShiftsApiService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly auth = inject(AuthService);

  readonly loading = signal(true);
  readonly items = signal<OpenShiftOverview[]>([]);
  readonly lastUpdated = signal<Date | null>(null);

  /** Client-side clock driving the live countdown column. */
  readonly now = signal(Date.now());
  private readonly destroyRef = inject(DestroyRef);

  readonly totalOpen = computed(() => this.items().length);

  readonly expiredCount = computed(() => this.items().filter(i => i.is_expired).length);

  readonly oldestAgeHours = computed(() => {
    const ages = this.items().map(i => i.hours_open);
    return ages.length ? Math.max(...ages) : 0;
  });

  readonly totalCollected = computed(() =>
    this.items().reduce((sum, i) => sum + (i.total_collected || 0), 0),
  );

  /** Cash locked in EXPIRED drawers: fondo inicial + cobrado de cada vencido. */
  readonly retainedExpired = computed(() =>
    this.items()
      .filter(i => i.is_expired)
      .reduce((sum, i) => sum + (i.cash_initial || 0) + (i.total_collected || 0), 0),
  );

  /** Sort direction: asc = menos tiempo restante primero (más urgente). */
  readonly sortOrder = signal<'asc' | 'desc'>('asc');

  /** Remaining ms until expiry; null when the shift has no expiry estimate. */
  private remainingMs(row: OpenShiftOverview): number | null {
    if (!row.expires_at) return null;
    const ms = new Date(row.expires_at).getTime() - this.now();
    return Number.isFinite(ms) ? ms : null;
  }

  /**
   * Rows ordered by remaining time. Default (asc): the shift closest to — or
   * past — its expiry limit first (forgotten shifts surface at the top).
   * Rows without an expiry estimate always stay at the end.
   */
  readonly sortedItems = computed(() => {
    const order = this.sortOrder();
    const list = [...this.items()];
    list.sort((a, b) => {
      const ra = this.remainingMs(a);
      const rb = this.remainingMs(b);
      if (ra === null && rb === null) return 0;
      if (ra === null) return 1;
      if (rb === null) return -1;
      return order === 'asc' ? ra - rb : rb - ra;
    });
    return list;
  });

  /** Toggle between "menos tiempo primero" and "más tiempo primero". */
  toggleSortOrder(): void {
    this.sortOrder.update(o => (o === 'asc' ? 'desc' : 'asc'));
  }

  /** Forced close is a manager power (shifts.manage, same as the dashboard). */
  readonly canForceClose = computed(() => this.auth.hasPermission('shifts.manage' as PermissionCode));

  /** Shift being force-closed (in-flight state for the row button). */
  readonly closingId = signal<string | null>(null);

  constructor() {
    this.load();

    // Live countdown: re-evaluate remaining time on a modest tick.
    const countdownTimer = setInterval(() => this.now.set(Date.now()), COUNTDOWN_TICK_MS);
    // Auto-refresh: keep the forgotten-shift view honest every 30 minutes.
    const refreshTimer = setInterval(() => this.load(true), AUTO_REFRESH_MS);
    this.destroyRef.onDestroy(() => {
      clearInterval(countdownTimer);
      clearInterval(refreshTimer);
    });
  }

  load(silent = false): void {
    if (!silent || this.items().length === 0) {
      this.loading.set(true);
    }
    this.api.getOpenShiftsOverview().subscribe({
      next: (res) => {
        this.items.set(res.items);
        this.lastUpdated.set(new Date());
        this.loading.set(false);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.toast.error(getErrorMessage(err) ?? 'Error al cargar los turnos abiertos');
      },
    });
  }

  /**
   * Expected-arqueo summary for the forced-close 2nd dialog: fondo inicial
   * + cobrado por método (omitiendo métodos en $0) + total esperado en caja.
   * Falls back to fondo + total cobrado when the row lacks the breakdown.
   */
  private arqueoSummary(row: OpenShiftOverview): string[] {
    // en-US para el separador de decimales con punto — consistente con el
    // CurrencyPipe que ya usa esta página para los KPIs ($150.00).
    const money = (n: number) => formatCurrency(n, 'USD', 'en-US');
    const lines: string[] = [];
    lines.push(`Fondo inicial: ${money(row.cash_initial || 0)}`);

    const bd = row.payment_breakdown;
    if (bd) {
      const byLabel: Array<[number, string]> = [
        [bd.cash || 0, 'Efectivo'],
        [bd.card || 0, 'Tarjeta'],
        [bd.transfer || 0, 'Transferencias'],
        [bd.other || 0, 'Otros'],
      ];
      for (const [amount, label] of byLabel) {
        if (amount > 0) lines.push(`${label}: ${money(amount)}`);
      }
      lines.push(`Total esperado en caja: ${money((row.cash_initial || 0) + bd.total)}`);
    } else {
      lines.push(`Total cobrado: ${money(row.total_collected || 0)}`);
      lines.push(`Total esperado en caja: ${money((row.cash_initial || 0) + (row.total_collected || 0))}`);
    }
    return lines;
  }

  /** "46.2" → "46h 12m"; sub-hour → "0m". */
  formatAge(hours: number): string {
    const safe = Number.isFinite(hours) && hours > 0 ? hours : 0;
    const h = Math.floor(safe);
    const m = Math.round((safe - h) * 60);
    if (h === 0) return `${m}m`;
    return `${h}h ${m}m`;
  }

  /**
   * Live remaining time until expiry. "8h 59m restantes" for a live shift,
   * "hace 34h 0m" for an expired one (drives the countdown column).
   */
  countdownText(row: OpenShiftOverview): string {
    if (!row.expires_at) return '—';
    const diffMs = new Date(row.expires_at).getTime() - this.now();
    if (diffMs <= 0) {
      return `hace ${this.formatAge(Math.abs(diffMs) / 3_600_000)}`;
    }
    return `${this.formatAge(diffMs / 3_600_000)} restantes`;
  }

  /** Countdown tone mirrors the age tone (expired → danger, near → warning). */
  countdownClass(row: OpenShiftOverview): string {
    if (row.is_expired) return 'expired';
    if (row.max_open_hours > 0 && row.hours_open >= row.max_open_hours * NEAR_LIMIT_RATIO) {
      return 'warning';
    }
    return 'ok';
  }

  /** Row tone: expired → danger; near the per-hotel limit → warning; else normal. */
  ageClass(row: OpenShiftOverview): 'expired' | 'warning' | 'normal' {
    if (row.is_expired) return 'expired';
    if (row.max_open_hours > 0 && row.hours_open >= row.max_open_hours * NEAR_LIMIT_RATIO) {
      return 'warning';
    }
    return 'normal';
  }

  goToShift(row: OpenShiftOverview): void {
    void this.router.navigate(['/management/shifts/dashboard'], {
      queryParams: { prop_id: row.prop_id, prop_label: row.hotel_name },
    });
  }

  /**
   * Force-close an EXPIRED shift with double confirmation.
   *
   * 1st dialog: warning of the block + consequence (danger, delete mode).
   * 2nd dialog: confirms with an optional reason (stamped in the audit log as
   * the emergency reason; defaults to ``vencimiento``). The counted cash is
   * the expected drawer content (fondo + cobrado) — simplified arqueo.
   */
  async forceClose(row: OpenShiftOverview): Promise<void> {
    const detail = `${row.hotel_name} · ${row.shift_label} · ${row.employee}`;
    const first = await this.confirmDialog.open({
      title: 'Cerrar forzosamente el turno',
      message:
        `El turno de ${row.hotel_name} lleva más de ${row.max_open_hours}h sin cerrarse. ` +
        'Las operaciones de caja de este hotel están bloqueadas y la caja retiene ' +
        'efectivo hasta que se cierre. Continúa solo si eres gerencia.',
      confirmLabel: 'Continuar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: detail,
    });
    if (!first) return;

    // Resumen del arqueo esperado (fondo + cobrado por método) antes de
    // confirmar: lo que la caja debería contener físicamente al cerrarla.
    const arqueoDetails = this.arqueoSummary(row);
    const reason = await this.confirmDialog.openPrompt({
      title: 'Confirmar cierre forzado',
      message:
        'El turno está VENCIDO y el cierre es irreversible. Se hará un arqueo ' +
        'simplificado con el efectivo esperado en caja; el motivo quedará en el audit log.',
      confirmLabel: 'Cerrar forzosamente',
      variant: 'danger',
      mode: 'delete',
      modeDetail: detail,
      details: arqueoDetails,
      input: {
        label: 'Motivo del cierre (opcional)',
        placeholder: 'Ej. Turno olvidado, gerencia cierra la caja…',
        maxLength: 200,
      },
    });
    if (reason === null) return;

    this.closingId.set(row.id);
    this.api.closeShift(
      row.id,
      (row.cash_initial || 0) + (row.total_collected || 0),
      undefined,
      undefined,
      undefined,
      undefined,
      true,
      reason.trim() || 'vencimiento',
    ).subscribe({
      next: () => {
        this.closingId.set(null);
        this.toast.success('Turno cerrado forzosamente — caja liberada.');
        this.load(true);
      },
      error: (err: unknown) => {
        this.closingId.set(null);
        this.toast.error(getErrorMessage(err) ?? 'Error al cerrar el turno forzosamente');
      },
    });
  }
}
