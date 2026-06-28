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
  readonly weekStart = input<string>('');

  readonly prevWeek = output<void>();
  readonly nextWeek = output<void>();

  readonly dayLabels = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sab'];

  readonly monthLabel = computed(() => {
    const d = this.data();
    if (!d) return '';
    const names = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    return `${names[d.month - 1]} ${d.year}`;
  });

  readonly weekDays = computed(() => {
    const d = this.data();
    const ws = this.weekStart();
    if (!d || !ws) return [];
    const start = new Date(ws);
    const today = new Date();
    const days: Array<{ day: number; date: string; isToday: boolean; data: OperationalDay | undefined }> = [];
    for (let i = 0; i < 7; i++) {
      const dt = new Date(start);
      dt.setDate(start.getDate() + i);
      const dateStr = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
      days.push({
        day: dt.getDate(),
        date: dateStr,
        isToday: today.getDate() === dt.getDate() && today.getMonth() === dt.getMonth() && today.getFullYear() === dt.getFullYear(),
        data: d.days.find(day => day.date === dateStr),
      });
    }
    return days;
  });

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
