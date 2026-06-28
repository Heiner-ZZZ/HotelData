import type { AvailabilityInventoryItem, CalendarMonth, CalendarRoomTypeCell } from '../../models/availability.model';

export type ViewMode = 'month' | 'week';

export const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

export const MONTH_NAMES_SHORT = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];

export const DAY_NAMES = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

/** Return the Monday of the week containing the given date. */
export function mondayOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay(); // 0=Sun .. 6=Sat
  const diff = day === 0 ? -6 : 1 - day; // Monday = 1
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Return the timestamp of the Monday anchoring the week containing this date. */
function _weekMonday(date: Date): number {
  return mondayOfWeek(date).getTime();
}

/** Group inventory items by date */
function _groupByDate(items: AvailabilityInventoryItem[]): Map<string, AvailabilityInventoryItem[]> {
  const byDate = new Map<string, AvailabilityInventoryItem[]>();
  for (const item of items) {
    const dateStr = item.date;
    if (!byDate.has(dateStr)) byDate.set(dateStr, []);
    byDate.get(dateStr)!.push(item);
  }
  return byDate;
}

/** Build CalendarRoomTypeCell[] for a given date */
function _roomTypesForDate(byDate: Map<string, AvailabilityInventoryItem[]>, dateStr: string): CalendarRoomTypeCell[] {
  return (byDate.get(dateStr) ?? []).map((inv) => ({
    roomTypeId: inv.roomTypeName,
    roomTypeName: inv.roomTypeName,
    totalRooms: inv.totalRooms,
    availableRooms: inv.availableRooms,
    blockedRooms: inv.blockedRooms,
    occupancyPct: inv.occupancyPct,
  }));
}

/** Build a full month view */
export function buildCalendarMonth(year: number, month: number, items: AvailabilityInventoryItem[]): CalendarMonth {
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);
  const byDate = _groupByDate(items);
  const currentWeekMonday = _weekMonday(today);

  const days: CalendarMonth['days'] = [];
  for (let d = 1; d <= daysInMonth; d++) {
    const dateObj = new Date(year, month, d);
    const dateStr = dateObj.toISOString().slice(0, 10);
    const dayOfWeek = dateObj.getDay();

    days.push({
      date: dateStr,
      day: d,
      dayName: DAY_NAMES[dayOfWeek],
      isToday: dateStr === todayStr,
      isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
      isPast: dateStr < todayStr,
      isCurrentWeek: _weekMonday(dateObj) === currentWeekMonday,
      roomTypes: _roomTypesForDate(byDate, dateStr),
    });
  }

  return { year, month, monthName: MONTH_NAMES[month], days };
}

/** Build a single-week (7-day) view starting from a Monday anchor date.
 *  The anchor is a Monday at 00:00:00 UTC; we build 7 consecutive days. */
export function buildCalendarWeek(anchorMonday: Date, items: AvailabilityInventoryItem[]): CalendarMonth {
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);
  const byDate = _groupByDate(items);

  const days: CalendarMonth['days'] = [];
  for (let i = 0; i < 7; i++) {
    const dateObj = new Date(anchorMonday);
    dateObj.setDate(anchorMonday.getDate() + i);
    const dateStr = dateObj.toISOString().slice(0, 10);
    const dayOfWeek = dateObj.getDay();

    days.push({
      date: dateStr,
      day: dateObj.getDate(),
      dayName: DAY_NAMES[dayOfWeek],
      isToday: dateStr === todayStr,
      isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
      isPast: dateStr < todayStr,
      isCurrentWeek: true,
      roomTypes: _roomTypesForDate(byDate, dateStr),
    });
  }

  const month = anchorMonday.getMonth();
  return { year: anchorMonday.getFullYear(), month, monthName: MONTH_NAMES[month], days };
}

/** CSS class for a calendar cell based on occupancy */
export function cellClass(roomType: CalendarRoomTypeCell): string {
  if (roomType.totalRooms === 0) return 'cell-na';
  const pct = roomType.occupancyPct;
  if (pct >= 90) return 'cell-danger';
  if (pct >= 60) return 'cell-warning';
  if (pct >= 30) return 'cell-caution';
  return 'cell-good';
}

/** Occupancy label for a cell */
export function cellLabel(roomType: CalendarRoomTypeCell): string {
  if (roomType.totalRooms === 0) return '—';
  return `${roomType.availableRooms}/${roomType.totalRooms}`;
}

/** Tooltip text for a cell */
export function cellTooltip(roomType: CalendarRoomTypeCell, date: string): string {
  return `${date} · ${roomType.roomTypeName}: ${roomType.availableRooms}/${roomType.totalRooms} disponibles (${roomType.occupancyPct}% ocupado)`;
}

/** Active cell info label */
export function activeCellLabel(date: string, roomTypeName: string): string {
  return `${date} — ${roomTypeName}`;
}
