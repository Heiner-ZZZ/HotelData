import {
  ChangeDetectionStrategy,
  Component,
  computed,
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

  close(): void {
    this.isOpen.set(false);
  }

  selectDay(day: CalendarDay): void {
    if (day.isDisabled) return;

    const dateStr = this._formatDate(day.date);

    if (!this.selectingEnd() || !this.startDate()) {
      this.startChange.emit(dateStr);
      this.endChange.emit('');
      this.selectingEnd.set(true);
    } else {
      const startD = new Date(this.startDate() + 'T00:00:00');
      if (day.date < startD) {
        this.startChange.emit(dateStr);
        this.endChange.emit('');
        this.selectingEnd.set(true);
      } else {
        this.endChange.emit(dateStr);
        this.selectingEnd.set(false);
        this.close();
      }
    }
  }

  private _formatDate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}
