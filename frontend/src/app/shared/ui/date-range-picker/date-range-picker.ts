import {
  ChangeDetectionStrategy,
  Component,
  computed,
  HostListener,
  input,
  output,
  signal,
} from '@angular/core';

interface CalendarDay {
  date: Date;
  day: number;
  month: number;
  year: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  isDisabled: boolean;
  isStart: boolean;
  isEnd: boolean;
  isInRange: boolean;
  isSameStartEnd: boolean;
}

@Component({
  selector: 'app-date-range-picker',
  imports: [],
  templateUrl: './date-range-picker.html',
  styleUrl: './date-range-picker.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DateRangePickerComponent {
  readonly minDate = input<string>('');
  readonly startDate = input<string>('');
  readonly endDate = input<string>('');
  readonly startChange = output<string>();
  readonly endChange = output<string>();

  readonly isOpen = signal(false);

  readonly currentMonth = signal(new Date().getMonth());
  readonly currentYear = signal(new Date().getFullYear());
  readonly selectingEnd = signal(false);

  readonly monthNames = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  readonly dayNames = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

  /** Escape cierra el popover (WCAG 2.1.1 — sin trampa de teclado). */
  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.isOpen()) this.close();
  }

  /** Nombre accesible completo de un día: "Vie 15 de Agosto de 2026" en vez
   *  de solo el número (WCAG 4.1.2 — los botones de día deben autodescribirse). */
  dayLabel(day: CalendarDay): string {
    const weekday = this.dayNames[(day.date.getDay() + 6) % 7];
    return `${weekday} ${day.day} de ${this.monthNames[day.month]} de ${day.year}`;
  }

  readonly dateLabel = computed(() => {
    const s = this.startDate();
    const e = this.endDate();
    if (!s && !e) return 'Seleccionar fechas';
    if (s && !e) return this._formatDisplay(s) + ' — ?';
    if (s && e) {
      if (s === e) return this._formatDisplay(s) + ' (misma fecha)';
      return this._formatDisplay(s) + ' — ' + this._formatDisplay(e);
    }
    return 'Seleccionar fechas';
  });

  private _formatDisplay(dateStr: string): string {
    if (!dateStr) return '';
    const [y, m, d] = dateStr.split('-');
    return `${d}/${m}/${y}`;
  }

  readonly calendarDays = computed(() => {
    const month = this.currentMonth();
    const year = this.currentYear();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startOffset = (firstDay.getDay() + 6) % 7;
    const totalDays = lastDay.getDate();

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const minD = this.minDate() ? new Date(this.minDate() + 'T00:00:00') : null;
    const startD = this.startDate() ? new Date(this.startDate() + 'T00:00:00') : null;
    const endD = this.endDate() ? new Date(this.endDate() + 'T00:00:00') : null;

    const days: CalendarDay[] = [];

    const prevMonth = new Date(year, month, 0);
    for (let i = startOffset - 1; i >= 0; i--) {
      const d = prevMonth.getDate() - i;
      const date = new Date(year, month - 1, d);
      days.push(this._makeDay(date, false, today, minD, startD, endD));
    }

    for (let d = 1; d <= totalDays; d++) {
      const date = new Date(year, month, d);
      days.push(this._makeDay(date, true, today, minD, startD, endD));
    }

    const remaining = 42 - days.length;
    for (let d = 1; d <= remaining; d++) {
      const date = new Date(year, month + 1, d);
      days.push(this._makeDay(date, false, today, minD, startD, endD));
    }

    return days;
  });

  private _makeDay(
    date: Date,
    isCurrentMonth: boolean,
    today: Date,
    minD: Date | null,
    startD: Date | null,
    endD: Date | null,
  ): CalendarDay {
    const isToday = date.getTime() === today.getTime();
    const isDisabled = minD ? date < minD : false;
    const isStart = startD ? date.getTime() === startD.getTime() : false;
    const isEnd = endD ? date.getTime() === endD.getTime() : false;
    const isSameStartEnd = isStart && isEnd;
    const isInRange = startD && endD && !isSameStartEnd ? date > startD && date < endD : false;

    return {
      date,
      day: date.getDate(),
      month: date.getMonth(),
      year: date.getFullYear(),
      isCurrentMonth,
      isToday,
      isDisabled,
      isStart,
      isEnd,
      isInRange,
      isSameStartEnd,
    };
  }

  prevMonth(): void {
    const m = this.currentMonth();
    if (m === 0) {
      this.currentMonth.set(11);
      this.currentYear.update(y => y - 1);
    } else {
      this.currentMonth.set(m - 1);
    }
  }

  nextMonth(): void {
    const m = this.currentMonth();
    if (m === 11) {
      this.currentMonth.set(0);
      this.currentYear.update(y => y + 1);
    } else {
      this.currentMonth.set(m + 1);
    }
  }

  toggleOpen(): void {
    this.isOpen.update(v => !v);
  }

  /** Abre el calendario programáticamente (p. ej. "Elegir fechas" de una card). */
  open(): void {
    this.isOpen.set(true);
  }

  close(): void {
    this.isOpen.set(false);
  }

  // ─── Drag/click-select state ───
  readonly isDragging = signal(false);
  readonly dragStartDate = signal('');
  readonly dragHoverDate = signal('');

  /** Entrada vigente ANTES del mousedown. El preview del arrastre emite una
   *  entrada provisional en mousedown, así que para reconstruir la selección
   *  clic-clic hay que recordar el valor previo (el input del padre ya lo
   *  pisó para cuando llega el mouseup). */
  private clickStartBefore = '';
  /** Estado de selección ANTES del mousedown (¿se estaba eligiendo la salida?). */
  private clickSelectingEndBefore = false;

  onDayMouseDown(day: CalendarDay, event: MouseEvent): void {
    if (day.isDisabled) return;
    event.preventDefault();
    this.clickStartBefore = this.startDate();
    this.clickSelectingEndBefore = this.selectingEnd();
    const dateStr = this._formatDate(day.date);
    this.isDragging.set(true);
    this.dragStartDate.set(dateStr);
    this.dragHoverDate.set(dateStr);
    this.startChange.emit(dateStr);
    this.endChange.emit('');
    this.selectingEnd.set(true);
  }

  onDayMouseEnter(day: CalendarDay): void {
    if (!this.isDragging()) return;
    const dateStr = this._formatDate(day.date);
    this.dragHoverDate.set(dateStr);
    // Preview the range end
    const startD = new Date(this.dragStartDate() + 'T00:00:00');
    const hoverD = new Date(dateStr + 'T00:00:00');
    if (hoverD >= startD) {
      this.endChange.emit(dateStr);
    } else {
      this.startChange.emit(dateStr);
      this.endChange.emit(this.dragStartDate());
    }
  }

  onDayMouseUp(day: CalendarDay): void {
    if (!this.isDragging()) return;
    this.isDragging.set(false);
    const dateStr = this._formatDate(day.date);

    // Clic (mousedown+mouseup en la MISMA celda) → selección clic-clic.
    // El mousedown ya emitió una entrada provisional; aquí se corrige para que
    // el clic signifique: 1er clic = entrada, 2º clic = salida. Si el 2º cae
    // ANTES de la entrada, se intercambian (misma validación de orden que el
    // arrastre): el más temprano pasa a ser la entrada y el tardío la salida.
    if (dateStr === this.dragStartDate()) {
      const priorStart = this.clickStartBefore;
      if (priorStart && this.clickSelectingEndBefore) {
        if (dateStr > priorStart) {
          this.startChange.emit(priorStart); // restaura la entrada provisional
          this.endChange.emit(dateStr);
        } else if (dateStr < priorStart) {
          this.endChange.emit(priorStart); // swap: el más temprano = entrada
        } else {
          this.endChange.emit(dateStr); // mismo día dos veces → misma fecha
        }
        this.selectingEnd.set(false);
      } else {
        // Primer clic (sin entrada previa) o reinicio tras un rango completo:
        // el mousedown ya dejó entrada + sin salida; queda a la espera de la
        // salida (el hint "Arrastra o haz clic…" lo acompaña).
        this.selectingEnd.set(true);
      }
      return;
    }

    // Arrastre real entre celdas → rango completo (ambas direcciones).
    const startD = new Date(this.dragStartDate() + 'T00:00:00');
    const endD = new Date(dateStr + 'T00:00:00');
    if (endD >= startD) {
      this.startChange.emit(this.dragStartDate());
      this.endChange.emit(dateStr);
    } else {
      this.startChange.emit(dateStr);
      this.endChange.emit(this.dragStartDate());
    }
    this.selectingEnd.set(false);
  }

  onMouseUpGlobal(): void {
    if (this.isDragging()) {
      this.isDragging.set(false);
      this.selectingEnd.set(false);
    }
  }

  /** Selección clic-clic: el primer clic fija la entrada; el segundo fija la
   *  salida, intercambiando si cae antes de la entrada (misma regla de orden
   *  que el arrastre). Comparte máquina de estados con el clic de ratón. */
  selectDay(day: CalendarDay): void {
    if (day.isDisabled) return;

    const dateStr = this._formatDate(day.date);

    if (!this.selectingEnd() || !this.startDate()) {
      this.startChange.emit(dateStr);
      this.endChange.emit('');
      this.selectingEnd.set(true);
      return;
    }

    const startStr = this.startDate();
    if (dateStr > startStr) {
      this.endChange.emit(dateStr);
      this.selectingEnd.set(false);
    } else if (dateStr < startStr) {
      this.startChange.emit(dateStr); // el más temprano pasa a ser la entrada
      this.endChange.emit(startStr); // la entrada previa pasa a ser la salida
      this.selectingEnd.set(false);
    } else {
      this.endChange.emit(dateStr); // mismo día dos veces → misma fecha
      this.selectingEnd.set(false);
    }
  }

  /** El clic de RATÓN ya lo resuelve el flujo mousedown/mouseup (arrastre o
   *  clic); este handler atiende SOLO la activación por teclado (Enter/Espacio,
   *  cuyo evento `click` llega con detail === 0). Sin esto el calendario sería
   *  inutilizable por teclado, porque el arrastre es exclusivo de ratón. */
  onDayClick(day: CalendarDay, event: MouseEvent): void {
    if (event.detail !== 0) return;
    this.selectDay(day);
  }

  /** Check if a day is within the drag preview range. */
  isDragInRange(day: CalendarDay): boolean {
    if (!this.isDragging()) return false;
    const hoverStr = this.dragHoverDate();
    if (!hoverStr) return false;
    const d = day.date;
    const start = this.startDate() ? new Date(this.startDate() + 'T00:00:00') : null;
    const hover = new Date(hoverStr + 'T00:00:00');
    if (!start) return false;
    const lo = start < hover ? start : hover;
    const hi = start < hover ? hover : start;
    return d > lo && d < hi;
  }

  private _formatDate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}
