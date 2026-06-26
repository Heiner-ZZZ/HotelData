import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';

export interface CalendarDayRate {
  date: string;
  rateAmount: number;
  ratePlanName: string;
  ratePlanId: string;
  isClosed: boolean;
  minStay: number;
  /** Color category for visual grouping */
  tier: 'low' | 'medium' | 'high' | 'premium';
}

export interface RoomTypeCalendarRow {
  roomTypeId: string;
  roomTypeName: string;
  roomTypeNumber: string;
  days: CalendarDayRate[];
}

@Component({
  selector: 'app-rate-monthly-calendar',
  imports: [CurrencyPipe, DatePipe],
  templateUrl: './rate-monthly-calendar.html',
  styleUrl: './rate-monthly-calendar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RateMonthlyCalendarComponent {
  /** Room type rows with their daily rates */
  readonly rows = input<RoomTypeCalendarRow[]>([]);
  /** Currently viewed month (0-11) */
  readonly month = input(0);
  /** Currently viewed year */
  readonly year = input(0);
  /** Display mode: 'month' (full month) or 'week' (7 days) */
  readonly displayMode = input<'month' | 'week'>('week');
  /** Events per date — shown as colored indicators on cells */
  readonly events = input<Array<{ date: string; type: string; label: string; color: string }>>([]);

  /** Emit when month changes */
  readonly monthChange = output<{ month: number; year: number }>();
  /** Emit when display mode changes */
  readonly displayModeChange = output<'month' | 'week'>();

  readonly monthNames = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
  ];

  readonly monthLabel = computed(() => {
    const m = this.month();
    const y = this.year();
    return `${this.monthNames[m]} ${y}`;
  });

  readonly daysInMonth = computed(() => {
    const m = this.month();
    const y = this.year();
    return new Date(y, m + 1, 0).getDate();
  });

  readonly firstDayOfWeek = computed(() => {
    const m = this.month();
    const y = this.year();
    return new Date(y, m, 1).getDay(); // 0=Sun
  });

  readonly dayLabels = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

  readonly dayNumbers = computed(() => {
    const days = this.daysInMonth();
    return Array.from({ length: days }, (_, i) => i + 1);
  });

  readonly weekRows = computed(() => {
    const days = this.daysInMonth();
    const firstDow = this.firstDayOfWeek();
    const totalCells = firstDow + days;
    const rowsCount = Math.ceil(totalCells / 7);
    const result: number[][] = [];
    let day = 1;
    for (let r = 0; r < rowsCount; r++) {
      const week: number[] = [];
      for (let d = 0; d < 7; d++) {
        const cellIdx = r * 7 + d;
        if (cellIdx < firstDow || day > days) {
          week.push(0);
        } else {
          week.push(day);
          day++;
        }
      }
      result.push(week);
    }
    return result;
  });

  prevMonth(): void {
    const m = this.month();
    const y = this.year();
    if (m === 0) {
      this.monthChange.emit({ month: 11, year: y - 1 });
    } else {
      this.monthChange.emit({ month: m - 1, year: y });
    }
  }

  nextMonth(): void {
    const m = this.month();
    const y = this.year();
    if (m === 11) {
      this.monthChange.emit({ month: 0, year: y + 1 });
    } else {
      this.monthChange.emit({ month: m + 1, year: y });
    }
  }

  readonly showEvents = computed(() => this.events().length > 0);

  getRateForDay(row: RoomTypeCalendarRow, day: number): CalendarDayRate | undefined {
    const dateStr = `${this.year()}-${String(this.month() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return row.days.find((d) => d.date === dateStr);
  }

  getEventsForDate(dateStr: string): Array<{ type: string; label: string; color: string }> {
    return this.events().filter((e) => e.date === dateStr);
  }

  /** Build a full date string from year + month (0-11) + day. */
  dateStrFromDay(day: number): string {
    return `${this.year()}-${String(this.month() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  isToday(day: number): boolean {
    const today = new Date();
    return (
      today.getDate() === day &&
      today.getMonth() === this.month() &&
      today.getFullYear() === this.year()
    );
  }

  onToggleDisplayMode(): void {
    this.displayModeChange.emit(this.displayMode() === 'month' ? 'week' : 'month');
  }
}
