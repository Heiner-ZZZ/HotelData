import { ChangeDetectionStrategy, Component, input, computed, signal, output, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';

import type { AvailabilityInventoryItem, AvailabilityBlackoutItem } from '../../models/availability.model';
import { DAY_NAMES, MONTH_NAMES_SHORT } from '../../availability.helpers';

@Component({
  selector: 'app-availability-data-tables',
  imports: [EmptyStateComponent, FormsModule],
  templateUrl: './availability-data-tables.html',
  styleUrl: '../../pages/availability-page/availability-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class AvailabilityDataTablesComponent {
  readonly inventoryItems = input<AvailabilityInventoryItem[]>([]);
  readonly availabilityBlocks = input<AvailabilityBlackoutItem[]>([]);
  readonly blackoutItems = input<AvailabilityBlackoutItem[]>([]);
  readonly roomNumbersByType = input<Map<string, string[]>>(new Map());

  /** Emitted when the user wants to delete a blackout block. */
  readonly deleteBlackout = output<string>();

  /** Emitted when the user wants to edit a blackout block. */
  readonly editBlackout = output<string>();

  /** Emitted when the user wants to edit an inventory entry. */
  readonly editInventory = output<{ date: string; roomTypeName: string; roomTypeId: string; totalRooms: number; availableRooms: number; blockedRooms: number }>();

  /** Emitted when the user wants to delete an inventory entry. */
  readonly deleteInventory = output<{ date: string; roomTypeName: string }>();

  readonly DAY_NAMES = DAY_NAMES;

  readonly viewMode = signal<'table' | 'calendar'>('table');
  readonly pageSize = 10;
  readonly currentPage = signal(1);
  readonly filterRoomType = signal('');
  readonly filterDateFrom = signal('');
  readonly filterDateTo = signal('');
  readonly hidePastDates = signal(true);
  readonly todayStr = new Date().toISOString().slice(0, 10);
  readonly calendarMonth = signal(new Date().getMonth());
  readonly calendarYear = signal(new Date().getFullYear());

  readonly roomTypeOptions = computed(() => {
    const seen = new Set<string>();
    const opts: string[] = [];
    for (const item of this.inventoryItems()) {
      if (!seen.has(item.roomTypeName)) {
        seen.add(item.roomTypeName);
        opts.push(item.roomTypeName);
      }
    }
    return opts.sort();
  });

  readonly filteredItems = computed(() => {
    let items = [...this.inventoryItems()];
    const rt = this.filterRoomType();
    const from = this.filterDateFrom();
    const to = this.filterDateTo();
    if (rt) items = items.filter(i => i.roomTypeName === rt);
    if (from) items = items.filter(i => i.date >= from);
    if (to) items = items.filter(i => i.date <= to);
    // By default hide past dates
    if (this.hidePastDates()) {
      items = items.filter(i => i.date >= this.todayStr);
    }
    items.sort((a, b) => a.date.localeCompare(b.date) || a.roomTypeName.localeCompare(b.roomTypeName));
    return items;
  });

  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.filteredItems().length / this.pageSize)));

  readonly paginatedItems = computed(() => {
    const page = Math.min(this.currentPage(), this.totalPages());
    const start = (page - 1) * this.pageSize;
    return this.filteredItems().slice(start, start + this.pageSize);
  });

  roomNumbersFor(roomTypeId: string, roomTypeName: string): string[] {
    const map = this.roomNumbersByType();
    // Primary lookup by roomTypeId (more reliable)
    let result = map.get(roomTypeId) ?? [];
    // Fallback: try by name if ID didn't match
    if (result.length === 0 && roomTypeName) {
      result = map.get(roomTypeName) ?? [];
    }
    // Only log if hotel rooms have loaded but BOTH lookups failed
    if (result.length === 0 && map.size > 0) {
      console.log('[roomNumbersFor] NOT FOUND — id:', roomTypeId, 'name:', roomTypeName, 'available keys:', [...map.keys()]);
    }
    return result;
  }

  readonly totalCount = computed(() => this.inventoryItems().length);
  readonly filteredCount = computed(() => this.filteredItems().length);

  /** Build calendar grid for the selected month */
  readonly calendarGrid = computed(() => {
    const year = this.calendarYear();
    const month = this.calendarMonth();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const firstDay = new Date(year, month, 1).getDay();
    const today = new Date();
    const todayStr = today.toISOString().slice(0, 10);

    const items = this.inventoryItems();
    const byDate = new Map<string, AvailabilityInventoryItem[]>();
    for (const item of items) {
      if (!byDate.has(item.date)) byDate.set(item.date, []);
      byDate.get(item.date)!.push(item);
    }

    const weeks: { date: string; day: number; isToday: boolean; isOtherMonth: boolean; roomTypes: AvailabilityInventoryItem[] }[][] = [];
    let week: typeof weeks[0] = [];

    // Pad empty days before first day
    for (let i = 0; i < firstDay; i++) {
      week.push({ date: '', day: 0, isToday: false, isOtherMonth: true, roomTypes: [] });
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const dateObj = new Date(year, month, d);
      const dateStr = dateObj.toISOString().slice(0, 10);
      week.push({
        date: dateStr,
        day: d,
        isToday: dateStr === todayStr,
        isOtherMonth: false,
        roomTypes: byDate.get(dateStr) ?? [],
      });
      if (week.length === 7) {
        weeks.push(week);
        week = [];
      }
    }
    // Pad last week
    if (week.length > 0) {
      while (week.length < 7) {
        week.push({ date: '', day: 0, isToday: false, isOtherMonth: true, roomTypes: [] });
      }
      weeks.push(week);
    }

    return { year, month, monthName: MONTH_NAMES_SHORT[month], weeks };
  });

  readonly calendarSummary = computed(() => {
    const grid = this.calendarGrid();
    let total = 0, occupied = 0, days = 0;
    for (const week of grid.weeks) {
      for (const day of week) {
        for (const rt of day.roomTypes) {
          total += rt.totalRooms;
          occupied += rt.totalRooms - rt.availableRooms;
          days++;
        }
      }
    }
    return { totalRooms: total, occupiedRooms: occupied, avgOccupancy: days > 0 ? Math.round((occupied / total) * 100) : 0 };
  });

  occupancyBadgeClass(pct: number): string {
    if (pct < 0) return 'badge';
    if (pct < 30) return 'badge badge-success';
    if (pct < 60) return 'badge badge-warning';
    return 'badge badge-danger';
  }

  occupancyColor(pct: number): string {
    if (pct <= 0) return 'occ-0';
    if (pct < 30) return 'occ-low';
    if (pct < 60) return 'occ-mid';
    if (pct < 90) return 'occ-high';
    return 'occ-full';
  }

  nextMonth() {
    const m = this.calendarMonth();
    const y = this.calendarYear();
    if (m === 11) { this.calendarMonth.set(0); this.calendarYear.set(y + 1); }
    else { this.calendarMonth.set(m + 1); }
  }

  prevMonth() {
    const m = this.calendarMonth();
    const y = this.calendarYear();
    if (m === 0) { this.calendarMonth.set(11); this.calendarYear.set(y - 1); }
    else { this.calendarMonth.set(m - 1); }
  }

  nextPage() {
    if (this.currentPage() < this.totalPages()) this.currentPage.update(p => p + 1);
  }

  prevPage() {
    if (this.currentPage() > 1) this.currentPage.update(p => p - 1);
  }

  goToPage(page: number) {
    this.currentPage.set(Math.max(1, Math.min(page, this.totalPages())));
  }

  pageNumbers(): number[] {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: number[] = [];
    const start = Math.max(1, current - 2);
    const end = Math.min(total, current + 2);
    for (let i = start; i <= end; i++) pages.push(i);
    return pages;
  }
}
