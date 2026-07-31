import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { switchMap, map } from 'rxjs';

import { HrApiService } from '../../services/hr-api.service';
import { toast } from '../../../../core/toast/toast.service';
import { catchAndToastWarning } from '../../../../shared/utils/catch-and-toast';

type TabType = 'all' | 'present' | 'absent' | 'late';

@Component({
  selector: 'app-attendance-history-page',
  standalone: true,
  imports: [],
  templateUrl: './attendance-history-page.html',
  styleUrl: './attendance-history-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AttendanceHistoryPageComponent {
  private readonly api = inject(HrApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  /**
   * Bump signal that triggers a re-fetch when its value changes. Replaces the
   * legacy ``BehaviorSubject<void>`` refresh pattern; ``prevMonth`` /
   * ``nextMonth`` increment it to invalidate the attendance stream.
   */
  private readonly refreshTrigger = signal(0);

  /** Current month in YYYY-MM format */
  readonly currentMonth = signal(this._getDefaultMonth());

  /** Today's date in YYYY-MM-DD for highlighting */
  readonly todayStr = new Date().toISOString().substring(0, 10);

  /** Whether the selected month is the current (or future) month — disables next button */
  readonly isAtOrPastCurrentMonth = computed(() => {
    const sel = this.currentMonth();
    const now = this._getDefaultMonth();
    return sel >= now;
  });

  readonly employeeId = toSignal(
    this.route.paramMap.pipe(map(params => params.get('employeeId') || ''))
  );

  readonly attendance = toSignal(
    toObservable(this.refreshTrigger).pipe(
      switchMap(() => this.route.paramMap),
      switchMap(params => {
        const id = params.get('employeeId') || '';
        const month = this.currentMonth();
        return this.api.getAttendance(id, month);
      })
    )
  );

  readonly activeTab = signal<TabType>('all');

  readonly filteredRecords = computed(() => {
    const data = this.attendance();
    if (!data) return [];
    const tab = this.activeTab();

    return data.records.filter(r => {
      if (tab === 'all') return true;
      if (tab === 'present') return r.checkIn !== null;
      if (tab === 'absent') return r.status !== 'rest' && r.checkIn === null;
      if (tab === 'late') return false;
      return true;
    });
  });

  readonly monthNames = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
  ];

  readonly monthLabel = computed(() => {
    const [y, m] = this.currentMonth().split('-').map(Number);
    return `${this.monthNames[m - 1]} ${y}`;
  });

  prevMonth() {
    const [y, m] = this.currentMonth().split('-').map(Number);
    const d = new Date(y, m - 2, 1);
    this.currentMonth.set(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
    this.refreshTrigger.update(v => v + 1);
  }

  nextMonth() {
    if (this.isAtOrPastCurrentMonth()) return;
    const [y, m] = this.currentMonth().split('-').map(Number);
    const d = new Date(y, m, 1);
    this.currentMonth.set(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
    this.refreshTrigger.update(v => v + 1);
  }

  goBack() {
    const id = this.employeeId();
    if (id) {
      this.router.navigate(['/management/hr/portal', id]);
    } else {
      this.router.navigate(['/management/hr/directory']);
    }
  }

  formatTime(iso: string | null): string {
    if (!iso) return '—';
    try {
      return iso.substring(11, 16);
    } catch (err) {
      // Was silent — now visible in dev console + amber toast so devs see
      // when an unexpected ISO shape arrives (the previous fallback to '—'
      // hid any bad-data issues on the page).
      catchAndToastWarning('attendance.formatTime', '—')(err);
      return '—';
    }
  }

  formatHours(hours: number | null): string {
    if (hours === null || hours === undefined) return '—';
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h}h ${m}m`;
  }

  setTab(tab: TabType) {
    this.activeTab.set(tab);
  }

  isToday(dateStr: string): boolean {
    return dateStr === this.todayStr;
  }

  /** Genera y descarga un archivo CSV con los datos actuales */
  exportCSV() {
    const data = this.attendance();
    if (!data || data.records.length === 0) {
      toast('No hay datos para exportar en el mes seleccionado.', 'warning', 4000);
      return;
    }

    const rows: string[] = [];
    // Header
    rows.push('Fecha,Dia,Turno,Check-in,Check-out,Horas,Estado,Area');

    for (const r of data.records) {
      const date = r.date;
      const day = r.dayName;
      const shift = r.shiftStart ? `${r.shiftStart}-${r.shiftEnd}` : '';
      const checkIn = r.checkIn ? this.formatTime(r.checkIn) : '';
      const checkOut = r.checkOut ? this.formatTime(r.checkOut) : '';
      const hours = r.hoursWorked !== null ? this.formatHours(r.hoursWorked) : '';
      const status = this._statusLabel(r);
      const area = r.area;

      // Escape commas by wrapping in quotes
      const row = [date, day, shift, checkIn, checkOut, hours, status, area]
        .map(cell => `"${cell}"`).join(',');
      rows.push(row);
    }

    // BOM (\uFEFF) para que Excel reconozca UTF-8 correctamente
    const csv = '\uFEFF' + rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `asistencias_${data.employeeName}_${this.currentMonth()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast(`CSV exportado: ${data.records.length} registros.`, 'success', 4000);
  }

  /** Etiqueta legible para el estado */
  private _statusLabel(r: { status: string; checkIn: string | null; checkOut: string | null }): string {
    if (r.status === 'rest') return 'Descanso';
    if (r.checkIn && r.checkOut) return 'Completo';
    if (r.checkIn && !r.checkOut) return 'En curso';
    if (r.status === 'completed' && !r.checkIn) return 'Falta';
    return 'Pendiente';
  }

  private _getDefaultMonth(): string {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }
}
