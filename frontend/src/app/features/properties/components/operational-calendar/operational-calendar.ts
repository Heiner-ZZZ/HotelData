import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

export interface OperationalDay {
  date: string;
  hasRate: boolean;
  rateCount: number;
  bestRate: number | null;
  bestRatePlan: string | null;
  hasPromotion: boolean;
  hasInventory: boolean;
  totalRooms: number;
  availableRooms: number;
  blockedRooms: number;
  roomNumbers: string[];
  rooms: Array<{
    roomTypeId: string;
    roomTypeName: string;
    roomNumbers: string[];
    available: number;
    availableStatus: string;
    blocked: boolean;
    total: number;
  }>;
}

export interface DayHeader {
  date: string;
  dayOfWeek: number;
  isToday: boolean;
}

export interface OperationalFlags {
  policies_configured: boolean;
  rooms_configured: boolean;
  rates_configured: boolean;
  inventory_configured: boolean;
  promotions_active: boolean;
}

export interface OperationalCalendarData {
  year: number;
  month: number;
  operational: OperationalFlags;
  dayHeaders: DayHeader[];
  days: OperationalDay[];
  roomCount: number;
  roomNumbers: string[];
}

@Component({
  selector: 'app-operational-calendar',
  imports: [],
  templateUrl: './operational-calendar.html',
  styleUrl: './operational-calendar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OperationalCalendarComponent {
  readonly data = input<OperationalCalendarData | null>(null);
  readonly loading = input(false);

  readonly prevMonth = output<void>();
  readonly nextMonth = output<void>();

  readonly monthNames = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
  ];

  readonly dayLabels = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sab'];

  readonly monthLabel = computed(() => {
    const d = this.data();
    if (!d) return '';
    return `${this.monthNames[d.month - 1]} ${d.year}`;
  });

  readonly daysInMonth = computed(() => {
    const d = this.data();
    if (!d) return 0;
    return new Date(d.year, d.month, 0).getDate();
  });

  readonly firstDayOfWeek = computed(() => {
    const d = this.data();
    if (!d) return 0;
    return new Date(d.year, d.month - 1, 1).getDay();
  });

  readonly weekRows = computed(() => {
    const d = this.data();
    if (!d) return [];
    const days = this.daysInMonth();
    const firstDow = this.firstDayOfWeek();
    const totalCells = firstDow + days;
    const rowsCount = Math.ceil(totalCells / 7);
    const result: Array<Array<{ day: number; date: string; isToday: boolean }>> = [];
    let day = 1;
    for (let r = 0; r < rowsCount; r++) {
      const week: Array<{ day: number; date: string; isToday: boolean }> = [];
      for (let col = 0; col < 7; col++) {
        const cellIdx = r * 7 + col;
        if (cellIdx < firstDow || day > days) {
          week.push({ day: 0, date: '', isToday: false });
        } else {
          const dateStr = `${d.year}-${String(d.month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
          const today = new Date();
          week.push({
            day,
            date: dateStr,
            isToday: today.getDate() === day && today.getMonth() === d.month - 1 && today.getFullYear() === d.year,
          });
          day++;
        }
      }
      result.push(week);
    }
    return result;
  });

  getDay(dateStr: string): OperationalDay | undefined {
    return this.data()?.days.find(d => d.date === dateStr);
  }

  roomTooltip(d: OperationalDay): string {
    if (!d.hasInventory) return 'Sin datos de inventario';
    const parts: string[] = [];
    for (const r of d.rooms) {
      for (const num of r.roomNumbers) {
        parts.push(`Hab ${num} (${r.roomTypeName}): ${r.availableStatus}`);
      }
    }
    return parts.join(' · ');
  }
}
