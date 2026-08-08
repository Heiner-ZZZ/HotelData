import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { switchMap } from 'rxjs';

import { HrApiService } from '../../services/hr-api.service';
import { HrAuthService } from '../../services/hr-auth.service';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ConfirmDialogComponent } from '../../../../shared/ui/confirm-dialog/confirm-dialog.component';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { toast } from '../../../../core/toast/toast.service';
import type { EmployeeListItem, ShiftItem, ShiftCreatePayload } from '../../models/hr.model';

@Component({
  selector: 'app-shift-schedule-page',
  standalone: true,
  imports: [ConfirmDialogComponent],
  templateUrl: './shift-schedule-page.html',
  styleUrl: './shift-schedule-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShiftSchedulePageComponent {
  private readonly api = inject(HrApiService);
  private readonly router = inject(Router);
  private readonly propCtx = inject(PropertyContextService);
  readonly hrAuth = inject(HrAuthService);
  private readonly opMode = inject(OperationModeService);
  private readonly confirmDialog = inject(ConfirmDialogService);

  /**
   * Bump signal that triggers a re-fetch when its value changes. Replaces the
   * legacy ``BehaviorSubject<void>`` refresh pattern: any user action that
   * causes the shifts list to be stale increments this counter, and the
   * ``toObservable(refreshTrigger)`` stream re-subscribes the API call.
   */
  private readonly refreshTrigger = signal(0);

  readonly todayStr = new Date().toISOString().substring(0, 10);

  // ── State ──
  readonly employees = signal<EmployeeListItem[]>([]);
  readonly selectedEmployeeId = signal<string>('');

  // Week navigation
  readonly weekOffset = signal(0);

  readonly weekStart = computed(() => this._getWeekStart(this.weekOffset()));
  readonly weekEnd = computed(() => {
    const d = new Date(this.weekStart());
    d.setDate(d.getDate() + 6);
    return d.toISOString().substring(0, 10);
  });

  readonly weekDays = computed(() => {
    const start = new Date(this.weekStart());
    const days: { date: string; dayName: string; dayNum: number; isToday: boolean }[] = [];
    const names = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
    for (let i = 0; i < 7; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      const dateStr = d.toISOString().substring(0, 10);
      days.push({
        date: dateStr,
        dayName: names[d.getDay()],
        dayNum: d.getDate(),
        isToday: dateStr === this.todayStr,
      });
    }
    return days;
  });

  // Shifts for selected employee in current week range
  readonly shifts = toSignal(
    toObservable(this.refreshTrigger).pipe(
      switchMap(() => {
        const empId = this.selectedEmployeeId();
        if (!empId) return [null];
        return this.api.getShifts(empId, undefined, this.weekStart(), this.weekEnd());
      })
    )
  );

  // Build a lookup by date for quick access
  readonly shiftsByDate = computed(() => {
    const data = this.shifts();
    if (!data) return new Map<string, ShiftItem>();
    const map = new Map<string, ShiftItem>();
    for (const s of data.items) {
      map.set(s.date, s);
    }
    return map;
  });

  // ── Form state ──
  readonly formDate = signal(this.todayStr);
  readonly formStart = signal('09:00');
  readonly formEnd = signal('17:00');
  readonly formArea = signal('');
  readonly formNotes = signal('');
  readonly editingShiftId = signal<string | null>(null);
  readonly saving = signal(false);

  constructor() {
    this._loadEmployees();
  }

  private _loadEmployees() {
    const propId = this.propCtx.currentPropId() || undefined;
    this.api.getEmployees(undefined, undefined, true, 1, propId).subscribe({
      next: (res) => this.employees.set(res.items),
    });
  }

  selectEmployee(id: string) {
    this.selectedEmployeeId.set(id);
    this.refreshTrigger.update(v => v + 1);
  }

  selectWeek(offset: number) {
    this.weekOffset.set(offset);
    this.refreshTrigger.update(v => v + 1);
  }

  /** Open form to create/edit a shift */
  editShift(shift?: ShiftItem, date?: string) {
    if (shift) {
      // Editar turno existente → modo update.
      this.opMode.setMode('update', `Turno ${shift.date}`);
      this.editingShiftId.set(shift.id);
      this.formDate.set(shift.date);
      this.formStart.set(shift.scheduledStart);
      this.formEnd.set(shift.scheduledEnd);
      this.formArea.set(shift.area);
      this.formNotes.set(shift.notes);
    } else {
      // Click en celda vacía → crear turno → modo insert.
      this.opMode.setMode('insert', `Turno ${date || this.todayStr}`);
      this.editingShiftId.set(null);
      this.formDate.set(date || this.todayStr);
      this.formStart.set('09:00');
      this.formEnd.set('17:00');
      this.formArea.set('');
      this.formNotes.set('');
    }
  }

  cancelEdit() {
    this.opMode.reset();
    this.editingShiftId.set(null);
  }

  saveShift() {
    const empId = this.selectedEmployeeId();
    if (!empId) {
      toast('Selecciona un empleado.', 'warning', 4000);
      return;
    }
    const date = this.formDate();
    const start = this.formStart();
    const end = this.formEnd();
    if (!date || !start || !end) {
      toast('Completa fecha, inicio y fin del turno.', 'warning', 4000);
      return;
    }

    this.saving.set(true);
    const payload: ShiftCreatePayload = {
      employeeId: empId,
      date,
      scheduledStart: start,
      scheduledEnd: end,
      area: this.formArea(),
      notes: this.formNotes(),
    };

    // Convert to snake_case for API
    const apiPayload = {
      employee_id: payload.employeeId,
      date: payload.date,
      scheduled_start: payload.scheduledStart,
      scheduled_end: payload.scheduledEnd,
      area: payload.area || '',
      notes: payload.notes || '',
    };

    const editId = this.editingShiftId();
    const request = editId
      ? this.api.updateShift(editId, apiPayload as any)
      : this.api.createShift(apiPayload as any);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.editingShiftId.set(null);
        this.opMode.reset();
        this.refreshTrigger.update(v => v + 1);
        toast(editId ? 'Turno actualizado.' : 'Turno creado.', 'success', 4000);
      },
      error: () => {
        this.saving.set(false);
        toast('Error al guardar el turno.', 'error', 5000);
      },
    });
  }

  async deleteShift(shift: ShiftItem): Promise<void> {
    // Confirm compartido (mode-aware): muestra el modo delete en el nav mientras
    // el diálogo está abierto y restaura el modo previo al cerrar.
    const ok = await this.confirmDialog.open({
      title: 'Eliminar turno',
      message: `¿Eliminar el turno del ${shift.date} (${shift.scheduledStart}-${shift.scheduledEnd})?`,
      confirmLabel: 'Eliminar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: `Turno ${shift.date}`,
    });
    if (!ok) return;
    this.api.deleteShift(shift.id).subscribe({
      next: () => {
        this.refreshTrigger.update(v => v + 1);
        toast('Turno eliminado.', 'info', 4000);
      },
      error: () => toast('Error al eliminar el turno.', 'error', 5000),
    });
  }

  goBack() {
    this.router.navigate(['/management/hr/directory']);
  }

  private _getWeekStart(offset: number): string {
    const now = new Date();
    const day = now.getDay(); // 0=Sun
    const diff = now.getDate() - day + (offset * 7); // Start on Sunday
    const d = new Date(now);
    d.setDate(diff);
    return d.toISOString().substring(0, 10);
  }
}
