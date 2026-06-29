import { computed } from '@angular/core';

import type { AvailabilityInventoryItem, CalendarMonth } from '../../../models/availability.model';
import { buildCalendarMonth, buildCalendarWeek, mondayOfWeek } from '../../../availability.helpers';
import { AvailabilityState } from '../../../services/availability-state';

export class CalendarService {
  constructor(private readonly state: AvailabilityState) {
    state.weekAnchor.set(mondayOfWeek(new Date()));
  }

  readonly displayCalendar = computed(() =>
    this.state.viewMode() === 'month'
      ? this.state.calendarMonth()
      : this.state.calendarWeek(),
  );

  readonly skeletonCols = computed(() => {
    const count =
      this.state.viewMode() === 'month'
        ? new Date(this.state.calendarYear(), this.state.calendarMonthIdx() + 1, 0).getDate()
        : 7;
    return Array.from({ length: count }, (_, i) => i + 1);
  });

  readonly avgOccupancy = computed(() => {
    const cal = this.displayCalendar();
    if (!cal) return 0;
    const daysWithData = cal.days.filter((d) => d.roomTypes.length > 0).length;
    if (daysWithData === 0) return 0;
    return (
      cal.days.reduce((sum, d) => {
        const pcts = d.roomTypes.map((r) => r.occupancyPct);
        return sum + (pcts.length > 0 ? pcts.reduce((a, b) => a + b, 0) / pcts.length : 0);
      }, 0) / daysWithData
    );
  });

  setView(mode: 'month' | 'week') {
    this.state.viewMode.set(mode);
    this.rebuildCalendar();
  }

  prevPeriod() {
    if (this.state.viewMode() === 'month') {
      const y = this.state.calendarYear();
      const m = this.state.calendarMonthIdx();
      if (m === 0) {
        this.state.calendarYear.set(y - 1);
        this.state.calendarMonthIdx.set(11);
      } else {
        this.state.calendarMonthIdx.set(m - 1);
      }
    } else {
      const anchor = new Date(this.state.weekAnchor());
      anchor.setDate(anchor.getDate() - 7);
      this.state.weekAnchor.set(anchor);
    }
    this.state.activeCell.set(null);
    this.state.editingCell.set(null);
    this.rebuildCalendar();
  }

  nextPeriod() {
    if (this.state.viewMode() === 'month') {
      const y = this.state.calendarYear();
      const m = this.state.calendarMonthIdx();
      if (m === 11) {
        this.state.calendarYear.set(y + 1);
        this.state.calendarMonthIdx.set(0);
      } else {
        this.state.calendarMonthIdx.set(m + 1);
      }
    } else {
      const anchor = new Date(this.state.weekAnchor());
      anchor.setDate(anchor.getDate() + 7);
      this.state.weekAnchor.set(anchor);
    }
    this.state.activeCell.set(null);
    this.state.editingCell.set(null);
    this.rebuildCalendar();
  }

  goToday() {
    this.state.calendarYear.set(this.state.today.getFullYear());
    this.state.calendarMonthIdx.set(this.state.today.getMonth());
    this.state.weekAnchor.set(mondayOfWeek(new Date()));
    this.state.activeCell.set(null);
    this.state.editingCell.set(null);
    this.rebuildCalendar();
  }

  rebuildCalendar() {
    const vm = this.state.pageData();
    if (!vm) return;
    if (this.state.viewMode() === 'month') {
      this.state.calendarMonth.set(
        buildCalendarMonth(this.state.calendarYear(), this.state.calendarMonthIdx(), vm.inventoryItems),
      );
    } else {
      this.state.calendarWeek.set(
        buildCalendarWeek(this.state.weekAnchor(), vm.inventoryItems),
      );
    }
  }
}
