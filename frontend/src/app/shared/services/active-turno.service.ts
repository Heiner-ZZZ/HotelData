import { DestroyRef, Injectable, computed, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { interval } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { HR_PORTAL_READ, SHIFTS_READ } from '../../core/auth/permission.constants';
import { PropertyContextService } from './property-context.service';

/** Which turno the top-nav chip is showing: the cash shift or the employee's own HR shift. */
export type TurnoKind = 'caja' | 'personal';

export type TurnoStatusTone = 'neutral' | 'ok' | 'warn' | 'danger';

export interface TurnoCajaShift {
  id: string;
  prop_id: number;
  shift_number?: number;
  shift_type: 'morning' | 'afternoon' | 'evening';
  employee: string;
  opened_by: string | null;
  start_time: string;
  end_time: string | null;
  status: 'open' | 'closed';
  is_expired?: boolean;
  expires_at?: string | null;
}

export interface TurnoCajaResponse {
  shift: TurnoCajaShift | null;
  shift_type_labels?: Record<string, string>;
  /** true cuando hay un turno activo pero pertenece a OTRO empleado. */
  occupied?: boolean;
  opener_username?: string | null;
  opener_employee?: string | null;
  /** Cuándo el turno ajeno alcanza su límite de apertura (ISO). */
  expires_at?: string | null;
  max_open_hours?: number;
}

export interface TurnoPersonalShift {
  id: string;
  employee_id: string;
  date: string;
  scheduled_start: string;
  scheduled_end: string;
  area: string;
  status: string;
  actual_check_in: string | null;
  actual_check_out: string | null;
}

export interface TurnoPersonalResponse {
  shift: TurnoPersonalShift | null;
  employee_name: string;
}

/** Ready-to-render state for the TurnoChipComponent. */
export interface TurnoChipViewModel {
  kind: TurnoKind;
  /** Material Symbols icon name. */
  icon: string;
  /** Popover heading: "Turno actual" / "Mi turno". */
  title: string;
  /** Compact chip text, e.g. "T01 · 08:00–16:00". */
  chipLabel: string;
  /** "Turno Matutino" / area name. */
  typeLabel: string;
  dateLabel: string;
  windowLabel: string;
  startLabel: string;
  endLabel: string;
  statusLabel: string;
  statusTone: TurnoStatusTone;
  operatorLabel: string;
  hasShift: boolean;
  /** Texto extra para el popover cuando no hay shift propio (ej. turno ajeno). */
  note?: string;
  cta: { label: string; href: string } | null;
}

/** Parse "Matutino (08:00-16:00)" → type + start + end. */
function parseShiftLabel(label: string | undefined): { typeLabel: string; start: string; end: string } | null {
  if (!label) return null;
  const match = label.match(/^(.+?)\s*\(([^)]+)\)$/);
  if (!match) return null;
  const typeLabel = match[1].trim();
  const window = match[2].trim();
  const parts = window.split('-');
  if (parts.length === 2) {
    return { typeLabel, start: parts[0].trim(), end: parts[1].trim() };
  }
  return { typeLabel, start: window, end: '' };
}

/** "15 Ago" — noon anchor avoids UTC-day boundary drift for date-only values. */
function formatDate(value: string): string {
  if (!value) return '';
  const d = new Date(value.length === 10 ? `${value}T12:00:00` : value);
  if (Number.isNaN(d.getTime())) return '';
  const text = new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short' }).format(d);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Horas restantes hasta que el turno ajeno alcanza su límite de apertura.
 *  Sin exponer datos del compañero (solo el límite absoluto). */
export function shiftLimitHint(expiresAt: string | null | undefined): string {
  if (!expiresAt) return '';
  const at = new Date(expiresAt).getTime();
  if (Number.isNaN(at)) return '';
  const diffMs = at - Date.now();
  if (diffMs <= 0) return 'Turno vencido: requiere cierre de gerencia';
  const hours = diffMs / 3_600_000;
  if (hours < 1) return 'Alcanza su límite en menos de 1 h';
  return `Alcanza su límite en ~${Math.round(hours)} h`;
}

@Injectable({ providedIn: 'root' })
export class ActiveTurnoService {
  private readonly auth = inject(AuthService);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly destroyRef = inject(DestroyRef);

  /** Bumped every 30s so the httpResources refetch, mirroring the notifications poll. */
  private readonly tick = signal(0);

  /** Which turno is currently shown in the chip. */
  readonly activeKind = signal<TurnoKind>('caja');

  readonly canCaja = computed(() => this.auth.hasPermission(SHIFTS_READ));
  readonly canPersonal = computed(() => this.auth.hasPermission(HR_PORTAL_READ));

  /** Available kinds, permission-gated: caja first (operative), then personal. */
  readonly kinds = computed<TurnoKind[]>(() => {
    const list: TurnoKind[] = [];
    if (this.canCaja()) list.push('caja');
    if (this.canPersonal()) list.push('personal');
    return list;
  });

  readonly hasMultiple = computed(() => this.kinds().length > 1);

  private readonly cajaResource = httpResource<TurnoCajaResponse | undefined>(() => {
    this.tick(); // periodic refetch dependency
    const propId = this.propertyCtx.currentPropId();
    if (!this.canCaja() || !propId) return undefined;
    return `/reception/shifts/active?prop_id=${propId}`;
  });

  private readonly personalResource = httpResource<TurnoPersonalResponse | undefined>(() => {
    this.tick(); // periodic refetch dependency
    if (!this.canPersonal()) return undefined;
    return '/hr/my-shift/today';
  });

  readonly isLoading = computed(() =>
    this.activeKind() === 'caja' ? this.cajaResource.isLoading() : this.personalResource.isLoading(),
  );

  readonly hasError = computed(() =>
    this.activeKind() === 'caja' ? !!this.cajaResource.error() : !!this.personalResource.error(),
  );

  readonly viewModel = computed<TurnoChipViewModel | null>(() => {
    const kind = this.activeKind();
    if (kind === 'caja') return this.cajaViewModel(this.cajaResource.value());
    return this.personalViewModel(this.personalResource.value());
  });

  constructor() {
    // Keep the active kind valid when the permission set changes (login/role/logout).
    effect(() => {
      const kinds = this.kinds();
      if (kinds.length > 0 && !kinds.includes(this.activeKind())) {
        this.activeKind.set(kinds[0]);
      }
    });
    interval(30_000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.tick.update((t) => t + 1));
  }

  /** Cycle caja ↔ personal ("tipo bucle") when the user has both permissions. */
  cycleKind(): void {
    const kinds = this.kinds();
    if (kinds.length < 2) return;
    const index = kinds.indexOf(this.activeKind());
    this.activeKind.set(kinds[(index + 1) % kinds.length]);
  }

  private cajaViewModel(res: TurnoCajaResponse | undefined): TurnoChipViewModel {
    const shift = res?.shift ?? null;
    const labels = res?.shift_type_labels ?? {};
    if (res?.occupied && !shift) {
      // Hay un turno activo, pero es de OTRO empleado: no se muestran sus
      // datos ni se ofrece abrir otro (el backend lo rechazaría con 409).
      const opener = res.opener_employee || res.opener_username || 'otro empleado';
      return {
        kind: 'caja',
        icon: 'point_of_sale',
        title: 'Turno actual',
        chipLabel: 'Turno ocupado',
        typeLabel: 'Caja',
        dateLabel: '',
        windowLabel: '',
        startLabel: '—',
        endLabel: '—',
        statusLabel: 'Turno de otro empleado',
        statusTone: 'warn',
        operatorLabel: opener,
        hasShift: false,
        note: `Turno de ${opener}. ${shiftLimitHint(res.expires_at)}`,
        cta: null,
      };
    }
    if (!shift) {
      return {
        kind: 'caja',
        icon: 'point_of_sale',
        title: 'Turno actual',
        chipLabel: 'Sin turno',
        typeLabel: 'Caja',
        dateLabel: '',
        windowLabel: '',
        startLabel: '—',
        endLabel: '—',
        statusLabel: 'Sin turno',
        statusTone: 'neutral',
        operatorLabel: '—',
        hasShift: false,
        cta: { label: 'Abrir turno', href: '/management/shifts' },
      };
    }
    const parsed = parseShiftLabel(labels[shift.shift_type]);
    const typeLabel = parsed?.typeLabel ?? shift.shift_type;
    const window = parsed ? `${parsed.start}–${parsed.end}` : (labels[shift.shift_type] ?? '');
    const number = shift.shift_number ?? 0;
    const chipLabel = number > 0 ? `T${String(number).padStart(2, '0')} · ${window}` : window;
    const expired = !!shift.is_expired;
    return {
      kind: 'caja',
      icon: 'point_of_sale',
      title: 'Turno actual',
      chipLabel,
      typeLabel: `Turno ${typeLabel}`,
      dateLabel: formatDate(shift.start_time),
      windowLabel: window,
      startLabel: parsed?.start ?? '—',
      endLabel: parsed?.end ?? '—',
      statusLabel: expired ? 'Vencido' : 'Abierto',
      statusTone: expired ? 'danger' : 'ok',
      operatorLabel: shift.employee || shift.opened_by || '—',
      hasShift: true,
      cta: null,
    };
  }

  private personalViewModel(res: TurnoPersonalResponse | undefined): TurnoChipViewModel {
    const shift = res?.shift ?? null;
    const name = res?.employee_name ?? '';
    if (!shift) {
      return {
        kind: 'personal',
        icon: 'schedule',
        title: 'Mi turno',
        chipLabel: 'Descanso',
        typeLabel: 'Asistencia',
        dateLabel: '',
        windowLabel: '',
        startLabel: '—',
        endLabel: '—',
        statusLabel: 'Sin turno hoy',
        statusTone: 'neutral',
        operatorLabel: name || '—',
        hasShift: false,
        cta: null,
      };
    }
    const window = `${shift.scheduled_start || '—'}–${shift.scheduled_end || '—'}`;
    const statusMap: Record<string, { label: string; tone: TurnoStatusTone }> = {
      pending: { label: 'Pendiente', tone: 'warn' },
      active: { label: 'Activo', tone: 'ok' },
      completed: { label: 'Completado', tone: 'neutral' },
    };
    const status = statusMap[shift.status] ?? { label: shift.status, tone: 'neutral' as const };
    return {
      kind: 'personal',
      icon: 'schedule',
      title: 'Mi turno',
      chipLabel: window,
      typeLabel: shift.area || 'Turno',
      dateLabel: formatDate(shift.date),
      windowLabel: window,
      startLabel: shift.scheduled_start || '—',
      endLabel: shift.scheduled_end || '—',
      statusLabel: status.label,
      statusTone: status.tone,
      operatorLabel: name || '—',
      hasShift: true,
      cta: null,
    };
  }
}
