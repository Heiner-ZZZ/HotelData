import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal, effect } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { DatePipe } from '@angular/common';
import { switchMap, timer, map } from 'rxjs';

import { HrApiService } from '../../services/hr-api.service';
import { HrAuthService } from '../../services/hr-auth.service';
import type { EmployeePortal, PortalTasksData, PortalTask } from '../../models/hr.model';
import { toast } from '../../../../core/toast/toast.service';

@Component({
  selector: 'app-employee-dashboard-page',
  standalone: true,
  imports: [DatePipe],
  templateUrl: './employee-dashboard-page.html',
  styleUrl: './employee-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EmployeeDashboardPageComponent {
  private readonly api = inject(HrApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  readonly hrAuth = inject(HrAuthService);

  /**
   * Bump signal that triggers a re-fetch of the portal stream when its value
   * changes. Replaces the legacy ``BehaviorSubject<void>`` refresh pattern;
   * week navigation + check-in/out flows increment it.
   */
  private readonly refreshTrigger = signal(0);
  private autoCheckinDone = false;
  private autoCheckoutTimer: ReturnType<typeof setTimeout> | null = null;

  /** Week navigation offset: 0 = current week, -1 = last week, 1 = next week, etc. */
  readonly weekOffset = signal(0);

  readonly currentTime = toSignal(
    timer(0, 1000).pipe(map(() => {
      const now = new Date();
      return now.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', hour12: true });
    })), { initialValue: '' }
  );

  readonly currentDate = toSignal(
    timer(0, 60000).pipe(map(() => {
      return new Date().toLocaleDateString('es-MX', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    })), { initialValue: '' }
  );

  /** Compute the week_start string (Monday of the week at current offset) */
  readonly weekStart = computed(() => {
    const now = new Date();
    const day = now.getDay(); // 0=Sun, 1=Mon, ...
    // Offset to Monday (0=Mon)
    const diffToMonday = day === 0 ? -6 : 1 - day;
    const monday = new Date(now);
    monday.setDate(now.getDate() + diffToMonday + (this.weekOffset() * 7));
    return monday.toISOString().substring(0, 10);
  });

  /** Human-readable week label: "Semana del 13 jul 2026" */
  readonly weekLabel = computed(() => {
    const ws = this.weekStart();
    if (!ws) return '';
    const d = new Date(ws + 'T00:00:00');
    const day = d.getDate();
    const months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    return `Semana del ${day} ${months[d.getMonth()]} ${d.getFullYear()}`;
  });

  readonly portal = toSignal(
    toObservable(this.refreshTrigger).pipe(
      switchMap(() => this.route.paramMap),
      switchMap(params => {
        const employeeId = params.get('employeeId') || '';
        return this.api.getPortal(employeeId, this.weekStart());
      })
    )
  );

  readonly shiftLoading = signal(false);

  /** Portal tasks & operations data (loaded once on init) */
  readonly portalTasks = signal<PortalTasksData | null>(null);
  readonly tasksLoading = signal(false);

  /** Quick action: mark a task as in_progress */
  startPortalTask(task: PortalTask): void {
    this.tasksLoading.set(true);
    const payload = {
      prop_id: 0,
      room_label: task.roomLabel,
      status: 'in_progress',
      task_type: task.taskType || '',
      priority: task.priority,
      note: task.note || '',
      scheduled_date: task.scheduledDate || '',
      room_number: '',
      room_type_id: '',
    };
    this.api.startTask(task.id, payload).subscribe({
      next: () => { this.tasksLoading.set(false); this._loadPortalTasks(); toast('Tarea iniciada', 'success', 3000); },
      error: () => { this.tasksLoading.set(false); toast('Error al iniciar tarea', 'error', 4000); },
    });
  }

  /** Quick action: mark a cleaning task as completed */
  completePortalTask(task: PortalTask): void {
    this.tasksLoading.set(true);
    this.api.completeTask(task.id).subscribe({
      next: () => { this.tasksLoading.set(false); this._loadPortalTasks(); toast('Tarea completada', 'success', 3000); },
      error: () => { this.tasksLoading.set(false); toast('Error al completar tarea', 'error', 4000); },
    });
  }

  /** Load portal tasks from the backend */
  private _loadPortalTasks(): void {
    const data = this.portal();
    if (!data) return;
    this.api.getPortalTasks(data.employee.id).subscribe({
      next: (pt) => this.portalTasks.set(pt),
      error: () => { /* non-critical – tasks panel simply stays empty */ },
    });
  }

  constructor() {
    // Auto check-out timer cleanup is registered inline with ``DestroyRef``,
    // replacing the legacy ``ngOnDestroy`` hook. Angular 22 fires ``onDestroy``
    // callbacks during the same destruction phase as the lifecycle hook.
    this.destroyRef.onDestroy(() => this._clearAutoCheckoutTimer());

    // ── Auto register attendance on first load if shift is pending ──
    effect(() => {
      const data = this.portal();
      if (!data) return;

      this._tryAutoCheckin(data);
      this._scheduleAutoCheckout(data);
      this._loadPortalTasks();
    });
  }

  /** Auto register check-in when shift is pending */
  private _tryAutoCheckin(data: EmployeePortal): void {
    if (this.autoCheckinDone) return;
    const shift = data.currentShift;
    if (!shift || shift.status !== 'pending') return;

    this.autoCheckinDone = true;
    const now = new Date();
    const timeStr = now.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const dateStr = now.toLocaleDateString('es-MX', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    this.shiftLoading.set(true);
    this.api.shiftCheckIn(shift.id, data.employee.id).subscribe({
      next: () => {
        this.shiftLoading.set(false);
        this.refreshTrigger.update(v => v + 1);
        toast(
          `Asistencia registrada automáticamente el ${dateStr} a las ${timeStr}`,
          'success',
          6000
        );
      },
      error: () => {
        this.shiftLoading.set(false);
        toast('No se pudo registrar la asistencia automática. Intenta manualmente.', 'warning', 5000);
      },
    });
  }

  /** Schedule automatic check-out at the shift's scheduled end time */
  private _scheduleAutoCheckout(data: EmployeePortal): void {
    const shift = data.currentShift;
    if (!shift || shift.status !== 'active' || !shift.scheduledEnd) return;

    // If already has check-out, skip
    if (shift.actualCheckOut) return;

    // Parse scheduled end time (HH:MM)
    const parts = shift.scheduledEnd.split(':').map(Number);
    if (parts.length < 2 || isNaN(parts[0]) || isNaN(parts[1])) return;

    const now = new Date();
    const endTime = new Date(
      now.getFullYear(), now.getMonth(), now.getDate(),
      parts[0], parts[1], 0, 0
    );

    // If end time is already past, don't schedule (user should check out manually)
    const msUntilEnd = endTime.getTime() - now.getTime();
    if (msUntilEnd <= 0) return;

    // Clear any existing timer
    this._clearAutoCheckoutTimer();

    this.autoCheckoutTimer = setTimeout(() => {
      this.autoCheckoutTimer = null;
      const now2 = new Date();
      const timeStr = now2.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      this.shiftLoading.set(true);
      this.api.shiftCheckOut(shift.id, data.employee.id).subscribe({
        next: () => {
          this.shiftLoading.set(false);
          this.refreshTrigger.update(v => v + 1);
          toast(
            `Check-out automático registrado a las ${timeStr}`,
            'success',
            6000
          );
        },
        error: () => {
          this.shiftLoading.set(false);
          toast('No se pudo registrar el check-out automático. Intenta manualmente.', 'warning', 5000);
        },
      });
    }, msUntilEnd);
  }

  private _clearAutoCheckoutTimer(): void {
    if (this.autoCheckoutTimer !== null) {
      clearTimeout(this.autoCheckoutTimer);
      this.autoCheckoutTimer = null;
    }
  }


  /** Sections that are currently collapsed (by name). */
  readonly collapsedSections = signal<Set<string>>(new Set());

  toggleCollapse(section: string): void {
    this.collapsedSections.update(s => {
      const next = new Set(s);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  }

  isCollapsed(section: string): boolean {
    return this.collapsedSections().has(section);
  }

  doCheckIn() {
    const data = this.portal();
    if (!data?.currentShift) return;

    this.shiftLoading.set(true);
    const employeeId = data.employee.id;
    const shift = data.currentShift;
    const action = shift.status === 'active'
      ? this.api.shiftCheckOut(shift.id, employeeId)
      : this.api.shiftCheckIn(shift.id, employeeId);      action.subscribe({
      next: () => {
        // Cancel auto check-out timer if user manually checked out
        if (shift.status === 'active') {
          this._clearAutoCheckoutTimer();
        }
        this.shiftLoading.set(false);
        this.refreshTrigger.update(v => v + 1);
        const msg = shift.status === 'active'
          ? 'Check-out registrado correctamente.'
          : 'Asistencia registrada correctamente.';
        toast(msg, 'success', 4000);
      },
      error: () => {
        this.shiftLoading.set(false);
        toast('Error al registrar. Intenta de nuevo.', 'error', 5000);
      },
    });
  }

  /** Navegar a la semana anterior */
  goPrevWeek() {
    this.weekOffset.update(v => v - 1);
    this.refreshTrigger.update(v => v + 1);
  }

  /** Navegar a la semana siguiente */
  goNextWeek() {
    this.weekOffset.update(v => v + 1);
    this.refreshTrigger.update(v => v + 1);
  }

  /** Volver a la semana actual */
  goCurrentWeek() {
    this.weekOffset.set(0);
    this.refreshTrigger.update(v => v + 1);
  }

  /** Navegar al historial de asistencias */
  viewAttendanceHistory() {
    const data = this.portal();
    const id = data?.employee.id;
    if (id) {
      this.router.navigate(['/management/hr/portal', id, 'attendance']);
    }
  }

  /** Navegar al calendario mensual de housekeeping */
  viewFullMonth() {
    const data = this.portal();
    const propId = data?.employee.propId;
    if (propId) {
      this.router.navigate(['/management/housekeeping/calendar'], {
        queryParams: { prop_id: propId },
      });
    } else {
      toast('No hay propiedad asignada para ver el calendario completo.', 'info', 4000);
    }
  }

  /** Ver recibos / reportes de nómina anteriores */
  viewPreviousPayroll() {
    const data = this.portal();
    if (!data || data.payroll.workedHours === 0) {
      toast('No hay recibos de nómina anteriores disponibles para este período.', 'info', 5000);
    } else {
      toast('Funcionalidad de recibos anteriores próximamente.', 'info', 4000);
    }
  }

  /** Extrae HH:mm de un ISO string */
  formatTime(iso: string | null): string {
    if (!iso) return '—';
    try {
      return iso.substring(11, 16);
    } catch {
      return '—';
    }
  }

}
